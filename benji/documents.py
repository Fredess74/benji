"""Reference documents (floor plans, panel schedules, equipment schedules).

For machine-generated PDFs, pdfplumber words and tables are kept with page number and bounding box as
UNCONFIRMED candidates the user can check against the drawing. Benji does not recognise walls, wires,
connections or drawing scale; scanned images get no extraction (manual annotation instead).
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from .store import ROOT

DOC_DIR = ROOT / "data" / "documents"
MEDIA = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
# tokens that look like dimensions, ratings or equipment tags
CANDIDATE = re.compile(r"(\d+(\.\d+)?\s*(sq\.?\s*ft|sf|m2|ft|')|\d+\s*A\b|\d+\s*kW\b|\d+\s*(BTU|MBH)|\b(AHU|RTU|HP|B|P|LP)-?\d+\b)",
                       re.I)
MAX_CANDIDATES = 300


def ingest(content: bytes, filename: str, kind: str) -> dict:
    ext = Path(filename).suffix.lower()
    if ext not in MEDIA:
        raise ValueError(f"Unsupported document type {ext}; use PDF, PNG or JPEG")
    sha = hashlib.sha256(content).hexdigest()
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    path = DOC_DIR / f"{sha[:16]}{ext}"
    if not path.exists():
        path.write_bytes(content)
    doc = {"filename": filename, "kind": kind, "sha256": sha, "stored_path": str(path.relative_to(ROOT)),
           "media_type": MEDIA[ext], "pages": None, "candidates": [], "tables": [],
           "extraction": "none", "notice": None}
    if ext != ".pdf":
        doc["notice"] = "Image stored as reference. No automatic extraction; add annotations manually."
        return doc
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            doc["pages"] = len(pdf.pages)
            for pno, page in enumerate(pdf.pages[:20], start=1):
                words = page.extract_words() or []
                for w in words:
                    if CANDIDATE.search(w["text"]) and len(doc["candidates"]) < MAX_CANDIDATES:
                        doc["candidates"].append({"page": pno, "text": w["text"],
                                                  "bbox": [round(w["x0"], 1), round(w["top"], 1),
                                                           round(w["x1"], 1), round(w["bottom"], 1)],
                                                  "status": "unconfirmed_candidate"})
                for t in (page.extract_tables() or [])[:5]:
                    doc["tables"].append({"page": pno, "rows": t[:60], "status": "unconfirmed_candidate"})
            text_found = any((p.extract_text() or "").strip() for p in pdf.pages[:3])
    except Exception as exc:  # corrupted / encrypted
        doc["notice"] = f"Could not read PDF ({type(exc).__name__}); stored as reference only."
        return doc
    if not text_found:
        doc["notice"] = "No extractable text (likely scanned). OCR is not available; annotate manually."
    else:
        doc["extraction"] = "text_candidates"
        doc["notice"] = ("Candidates are text found on the drawing with page/position. They are NOT confirmed values "
                         "and Benji does not interpret walls, wiring or scale. Confirm by creating an annotation.")
    return doc
