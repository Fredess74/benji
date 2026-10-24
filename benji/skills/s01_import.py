"""01 Import Energy Data.

Supported inputs:
* CSV in the Benji bill template (one row per bill).
* Text-based PDF bills: a conservative label-based extractor. Every extracted value is
  stored as ``pending_confirmation`` and uncertain fields are listed.
* Scanned/image PDFs are not supported (no OCR); the user is told to enter values manually.

Imported text is treated as data only. Nothing in a document is executed or followed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date, datetime
from pathlib import Path

from ..models import Bill, BillSource, LineItem
from ..store import ROOT
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult

UPLOAD_DIR = ROOT / "data" / "uploads"

CSV_COLUMNS = [
    "fuel", "utility", "account", "period_start", "period_end", "quantity", "unit",
    "total_usd", "fixed_charges_usd", "energy_charges_usd", "delivery_variable_usd",
    "demand_charges_usd", "taxes_other_usd", "demand_kw",
]
REQUIRED_CSV = ["fuel", "period_start", "period_end", "quantity", "unit"]
FUEL_ALIASES = {"electric": "electricity", "electricity": "electricity", "elec": "electricity",
                "gas": "natural_gas", "natural gas": "natural_gas", "natural_gas": "natural_gas"}

SUPPORTED_FORMATS = {
    "csv": "Benji CSV template, columns: " + ", ".join(CSV_COLUMNS),
    "pdf": "Text-based PDF utility bills (values must be confirmed). Scanned/image PDFs need manual entry.",
    "manual": "Manual entry form / JSON",
}


class ImportError_(ValueError):
    pass


def _store_original(content: bytes, filename: str) -> tuple[str, str]:
    sha = hashlib.sha256(content).hexdigest()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{sha[:16]}{Path(filename).suffix.lower()}"
    if not path.exists():
        path.write_bytes(content)
    return sha, str(path.relative_to(ROOT))


def _parse_date(s: str) -> date:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ImportError_(f"Unrecognised date '{s}'")


def _num(s) -> float | None:
    if s is None:
        return None
    s = str(s).strip().replace("$", "").replace(",", "")
    if s == "":
        return None
    return float(s)


def parse_csv(content: bytes, filename: str = "upload.csv") -> dict:
    """Parse a Benji CSV. Returns {"bills": [...], "errors": [...]} without saving."""
    sha, stored = _store_original(content, filename)
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_CSV if c not in headers]
    if missing:
        return {"bills": [], "errors": [f"Missing required column(s): {', '.join(missing)}. "
                                          f"Expected template columns: {', '.join(CSV_COLUMNS)}"]}
    bills, errors = [], []
    for i, raw in enumerate(reader, start=2):
        row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        try:
            fuel = FUEL_ALIASES.get(row["fuel"].lower())
            if not fuel:
                raise ImportError_(f"unsupported fuel '{row['fuel']}' (supported: electricity, natural_gas)")
            items = []
            for col, cat, label in [("fixed_charges_usd", "fixed", "Fixed / customer charges"),
                                    ("energy_charges_usd", "energy", "Energy supply charges"),
                                    ("delivery_variable_usd", "delivery_variable", "Usage-based delivery charges"),
                                    ("demand_charges_usd", "demand", "Demand charges"),
                                    ("taxes_other_usd", "tax_other", "Taxes and other")]:
                v = _num(row.get(col))
                if v is not None:
                    items.append(LineItem(description=label, category=cat, amount_usd=v))
            bill = Bill(
                fuel=fuel, utility=row.get("utility") or None, account=row.get("account") or None,
                period_start=_parse_date(row["period_start"]), period_end=_parse_date(row["period_end"]),
                quantity=_num(row["quantity"]), unit=row["unit"], total_usd=_num(row.get("total_usd")),
                demand_kw=_num(row.get("demand_kw")), line_items=items,
                source=BillSource(kind="csv", filename=filename, sha256=sha, stored_path=stored,
                                  raw_excerpt=",".join(f"{k}={v}" for k, v in row.items())[:500]),
                extraction_confidence="high", status="pending_confirmation",
            )
            bills.append(bill.model_dump(mode="json"))
        except (ImportError_, ValueError, KeyError, TypeError) as exc:
            errors.append(f"Row {i}: {exc}")
    return {"bills": bills, "errors": errors}


# --- PDF ---------------------------------------------------------------------------
_MONEY = r"\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})"
_DATE = r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|[A-Z][a-z]{2,8} [0-9]{1,2}, [0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})"
PDF_PATTERNS = {
    "period": re.compile(r"(?:billing|service)\s+period[:\s]*" + _DATE + r"\s*(?:-|to|–|through)\s*" + _DATE, re.I),
    "kwh": re.compile(r"(?:total\s+)?(?:kwh|kilowatt[- ]hours?)\s*(?:used|usage)?[:\s]*([0-9][0-9,]*\.?[0-9]*)\s*(?:kwh)?", re.I),
    "kwh_after": re.compile(r"([0-9][0-9,]*\.?[0-9]*)\s*kwh", re.I),
    "therms": re.compile(r"([0-9][0-9,]*\.?[0-9]*)\s*therms", re.I),
    "ccf": re.compile(r"([0-9][0-9,]*\.?[0-9]*)\s*ccf", re.I),
    "total": re.compile(r"(?:total\s+amount\s+due|amount\s+due|total\s+charges)[:\s]*" + _MONEY, re.I),
    "customer_charge": re.compile(r"(?:customer|basic\s+service|monthly\s+service)\s+charge[:\s]*" + _MONEY, re.I),
    "demand_kw": re.compile(r"(?:billed\s+)?demand[:\s]*([0-9][0-9,]*\.?[0-9]*)\s*kw\b", re.I),
    "account": re.compile(r"account\s*(?:number|no\.?|#)?[:\s]*([0-9][0-9\- ]{4,20}[0-9])", re.I),
}
KNOWN_UTILITIES = ["Eversource", "National Grid", "Unitil", "Berkshire Gas", "Liberty", "Cape Light Compact"]


def extract_pdf_text(content: bytes) -> str:
    import pdfplumber  # local import: optional heavy dependency

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def parse_pdf_text(text: str) -> dict:
    """Extract a bill draft from PDF text. Returns {"draft": dict|None, "uncertain": [...], "notes": [...]}."""
    uncertain, notes = [], []
    draft: dict = {}
    m = PDF_PATTERNS["period"].search(text)
    if m:
        draft["period_start"], draft["period_end"] = _parse_date(m.group(1)).isoformat(), _parse_date(m.group(2)).isoformat()
    else:
        uncertain += ["period_start", "period_end"]
    therms = PDF_PATTERNS["therms"].search(text)
    ccf = PDF_PATTERNS["ccf"].search(text)
    kwh = PDF_PATTERNS["kwh"].search(text) or PDF_PATTERNS["kwh_after"].search(text)
    if therms or ccf:
        draft["fuel"] = "natural_gas"
        draft["quantity"], draft["unit"] = (_num(therms.group(1)), "therms") if therms else (_num(ccf.group(1)), "ccf")
        if kwh:
            notes.append("Document mentions both gas and electricity quantities; fuel assignment must be confirmed.")
            uncertain.append("fuel")
    elif kwh:
        draft["fuel"], draft["quantity"], draft["unit"] = "electricity", _num(kwh.group(1)), "kWh"
    else:
        uncertain += ["fuel", "quantity", "unit"]
    tot = PDF_PATTERNS["total"].search(text)
    if tot:
        draft["total_usd"] = _num(tot.group(1))
    else:
        uncertain.append("total_usd")
    items = []
    cc = PDF_PATTERNS["customer_charge"].search(text)
    if cc:
        items.append({"description": "Customer charge", "category": "fixed", "amount_usd": _num(cc.group(1))})
    else:
        notes.append("No fixed customer charge found; fixed vs. usage-based charges need manual classification.")
    draft["line_items"] = items
    dkw = PDF_PATTERNS["demand_kw"].search(text)
    if dkw:
        draft["demand_kw"] = _num(dkw.group(1))
    acct = PDF_PATTERNS["account"].search(text)
    if acct:
        draft["account"] = acct.group(1).strip()
    for u in KNOWN_UTILITIES:
        if u.lower() in text.lower():
            draft["utility"] = u
            break
    return {"draft": draft, "uncertain": uncertain, "notes": notes}


def parse_pdf(content: bytes, filename: str = "bill.pdf") -> dict:
    sha, stored = _store_original(content, filename)
    try:
        text = extract_pdf_text(content)
    except Exception as exc:  # corrupted / encrypted PDFs
        return {"bills": [], "errors": [f"Could not read PDF ({type(exc).__name__}). Use manual entry."],
                "manual_entry_required": True}
    if len(text.strip()) < 40:
        return {"bills": [], "manual_entry_required": True,
                "errors": ["This PDF has no extractable text (likely a scanned image). OCR is not available in "
                           "this version. Please enter the bill values manually; the original file is kept."]}
    parsed = parse_pdf_text(text)
    d = parsed["draft"]
    required_missing = [f for f in ("fuel", "period_start", "period_end", "quantity", "unit") if f not in d]
    source = BillSource(kind="pdf_text", filename=filename, sha256=sha, stored_path=stored, raw_excerpt=text[:800])
    preview = {
        **{k: d.get(k) for k in ("fuel", "utility", "account", "period_start", "period_end", "quantity",
                                  "unit", "total_usd", "demand_kw")},
        "line_items": d.get("line_items", []),
        "source": source.model_dump(mode="json"),
        "uncertain_fields": sorted(set(parsed["uncertain"])),
        "extraction_confidence": "low" if required_missing or parsed["uncertain"] else "medium",
        "status": "pending_confirmation",
        "notes": parsed["notes"],
    }
    if required_missing:
        # Return an editable preview but not a savable bill.
        return {"bills": [], "previews": [preview], "manual_entry_required": True,
                "errors": [f"Could not confidently extract: {', '.join(required_missing)}. "
                           "Complete these fields in the preview before saving."]}
    bill = Bill(**{k: v for k, v in preview.items() if k != "notes"})
    return {"bills": [bill.model_dump(mode="json")], "previews": [preview], "errors": []}


def import_file(content: bytes, filename: str) -> dict:
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        return parse_csv(content, filename)
    if ext == ".pdf":
        return parse_pdf(content, filename)
    return {"bills": [], "errors": [f"Unsupported file type '{ext}'. Supported: CSV template, text PDF, "
                                    "or manual entry."], "supported_formats": SUPPORTED_FORMATS}


def run(ctx: SkillContext) -> SkillResult:
    """Pipeline view of import state: what is confirmed, what still needs confirmation."""
    pending = [b for b in ctx.bills if b.get("status") != "confirmed"]
    confirmed = ctx.confirmed_bills
    res = SkillResult("01", COMPLETED if confirmed else NEEDS_DATA)
    res.outputs = {
        "confirmed_count": len(confirmed),
        "pending_count": len(pending),
        "pending_bill_ids": [b["id"] for b in pending],
        "fuels": sorted({b["fuel"] for b in confirmed}),
        "sources": sorted({(b.get("source") or {}).get("kind", "manual") for b in ctx.bills}),
        "supported_formats": SUPPORTED_FORMATS,
    }
    if pending:
        res.warnings.append(f"{len(pending)} imported bill(s) await confirmation and are excluded from analysis.")
    if not confirmed:
        res.missing_inputs.append({"field": "bills", "action": "Import or enter at least one bill, then confirm it."})
        res.message = "No confirmed bills yet."
    else:
        res.message = f"{len(confirmed)} confirmed bill(s) available for analysis."
    labels = sorted({b.get("data_label", "user_provided") for b in confirmed})
    res.evidence.append(Evidence("import.labels", f"Bill data labels: {', '.join(labels) or 'none'}",
                                 labels[0] if len(labels) == 1 else "user_provided"))
    return res
