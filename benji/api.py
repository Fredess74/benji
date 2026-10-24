"""HTTP API used by the Benji Dashboard and assistant integrations.

Run:  python -m uvicorn benji.api:app --host 127.0.0.1 --port 8000
Optional shared bearer key across data routes; bind to localhost by default.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, ValidationError

from pydantic import Field

from . import ai, assistant, demo, documents, engine, memory, readiness, thermal
from .models import Bill, Building, MeasureInputs
from .skills import registry
from .skills.s01_import import SUPPORTED_FORMATS, import_file
from .skills.s20_report import markdown_to_html, render_markdown
from .store import Store
from .validation import InputError, validate_measure_params

app = FastAPI(title="Benji API", version="0.1.0",
              description="Building Energy Intelligence - skills, analysis and action plans.")
store = Store()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.middleware("http")
async def protect_data_routes(request: Request, call_next):
    """A configured key must protect every data route, including the calculator API."""
    path = request.url.path
    protected = path == "/api" or path.startswith(("/api/", "/memory/", "/assistant/"))
    if protected and path != "/assistant/openapi.json":
        try:
            _require_key(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def _validation_error(_request: Request, exc: RequestValidationError):
    """Field-level messages; never echo the rejected input (it may be NaN/Infinity, which JSON cannot carry)."""
    detail = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


def _building_or_404(building_id: str) -> dict:
    b = store.get_building(building_id)
    if not b:
        raise HTTPException(404, "Building not found")
    return b


DASHBOARD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "index.html")


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse("/app")


@app.get("/app", include_in_schema=False)
def dashboard():
    """The management dashboard over /memory/* (single static page, no build step)."""
    return FileResponse(DASHBOARD, media_type="text/html")


@app.get("/api")
def index():
    return {"product": "Benji - Building Energy Intelligence", "docs": "/docs", "skills": "/api/skills",
            "integrations": integrations()}


@app.get("/api/integrations")
def integrations():
    return [
        {"id": "http_api", "name": "Benji HTTP API", "status": "available",
         "detail": "Local REST API over the same skill functions (see /docs). Optional BENJI_API_KEY; no user accounts."},
        {"id": "ai_explanations", "name": "AI explanations (Anthropic)",
         "status": "configured" if os.environ.get("ANTHROPIC_API_KEY") else "not_configured",
         "detail": "Optional. Rewords validated results only; deterministic summaries are used otherwise."},
        {"id": "claude_mcp", "name": "Claude (MCP server)", "status": "available",
         "detail": "python -m benji.mcp_server (stdio). Tools tested with an in-process MCP client; not yet tested "
                   "inside the Claude Desktop app. Config: integrations/claude/claude_desktop_config.json; also "
                   "bundled in the Claude Code plugin (.claude-plugin/, .mcp.json)."},
        {"id": "chatgpt_actions", "name": "ChatGPT custom GPT (Actions)", "status": "ready_to_configure",
         "detail": "OpenAPI schema at /assistant/openapi.json and integrations/chatgpt/. Needs a separately "
                   "secured HTTPS service and BENJI_API_KEY; not yet tested inside ChatGPT."},
        {"id": "openclaw", "name": "OpenClaw business agent", "status": "ready_to_configure",
         "detail": "Load the same skills/ folder (13 SKILL.md files) and give the agent the benji-memory/ folder "
                   "(or HTTP /memory/*). Tasks assigned to 'openclaw' in plan.md are its to do. Not yet tested "
                   "inside OpenClaw."},
        {"id": "monitoring", "name": "Live building monitoring", "status": "planned",
         "detail": "Not implemented; Benji works from bills, no hardware required."},
    ]


# --- skills -------------------------------------------------------------------------
@app.get("/api/skills")
def skills():
    return {"categories": registry.CATEGORIES, "skills": registry.list_skills(),
            "execution_order": registry.EXECUTION_ORDER}


# --- buildings ----------------------------------------------------------------------
@app.get("/api/buildings")
def list_buildings():
    return assistant.visible_buildings(store)


@app.get("/api/buildings/{building_id}/activity")
def activity(building_id: str):
    """What each channel did for this property (dashboard, Claude, ChatGPT, OpenClaw)."""
    _building_or_404(building_id)
    return store.list_events(building_id)


@app.get("/api/connect")
def connect_info():
    """Copy-ready settings for connecting assistants to THIS Benji instance."""
    import sys
    root = str(documents.ROOT)
    return {
        "claude_desktop": {"mcpServers": {"benji": {"command": sys.executable, "args": ["-m", "benji.mcp_server"],
                                                    "cwd": root, "env": {"BENJI_MEMORY": str(memory.root())}}}},
        "chatgpt_openapi_url": f"{assistant.PUBLIC_URL}/assistant/openapi.json",
        "openclaw_skills_path": str(documents.ROOT / "skills"),
        "memory_path": str(memory.root()),
        "api_key_required": bool(os.environ.get("BENJI_API_KEY")),
        "example_prompt": ("I want to lower my energy bills. Use Benji: create my property, then I'll give you my "
                           "last 12 months of bills. Read them back to me before confirming."),
    }


@app.post("/api/buildings", status_code=201)
def create_building(b: Building):
    data = b.model_dump(mode="json")
    data["id"] = None
    return store.save_building(data)


@app.get("/api/buildings/{building_id}")
def get_building(building_id: str):
    return _building_or_404(building_id)


@app.put("/api/buildings/{building_id}")
def update_building(building_id: str, b: Building):
    old = _building_or_404(building_id)
    data = b.model_dump(mode="json")
    data["id"] = building_id
    data["data_label"] = old.get("data_label", data["data_label"])
    return store.save_building(data)


@app.delete("/api/buildings/{building_id}", status_code=204)
def delete_building(building_id: str):
    _building_or_404(building_id)
    store.delete_building(building_id)


# --- bills --------------------------------------------------------------------------
@app.get("/api/bill-formats")
def bill_formats():
    return SUPPORTED_FORMATS


@app.get("/api/buildings/{building_id}/bills")
def list_bills(building_id: str):
    _building_or_404(building_id)
    return store.list_bills(building_id)


@app.post("/api/buildings/{building_id}/bills/import")
async def import_bills(building_id: str, file: UploadFile = File(...)):
    """Upload a CSV or PDF. Extracted bills are saved as pending_confirmation."""
    _building_or_404(building_id)
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (10 MB limit)")
    result = import_file(content, file.filename or "upload")
    saved = [store.save_bill({**bill, "building_id": building_id, "status": "pending_confirmation"})
             for bill in result.get("bills", [])]
    return {"saved_pending": saved, "previews": result.get("previews", []), "errors": result.get("errors", []),
            "manual_entry_required": result.get("manual_entry_required", False),
            "next_step": "Review each bill and confirm or correct it." if saved else
                         "Enter the bill manually using POST /api/buildings/{id}/bills."}


@app.post("/api/buildings/{building_id}/bills", status_code=201)
def add_bill(building_id: str, bill: Bill):
    """Manual entry. Saved as pending until confirmed (pass status='confirmed' to confirm at entry)."""
    b = _building_or_404(building_id)
    data = bill.model_dump(mode="json")
    data.update({"id": None, "building_id": building_id})
    if b.get("data_label") == "synthetic_demo":
        data["data_label"] = "synthetic_demo"
    return store.save_bill(data)


@app.put("/api/bills/{bill_id}")
def correct_bill(bill_id: str, bill: Bill):
    """Correct a bill. The source record is preserved; corrected fields are tracked."""
    old = store.get_bill(bill_id)
    if not old:
        raise HTTPException(404, "Bill not found")
    data = bill.model_dump(mode="json")
    changed = sorted(k for k in ("fuel", "period_start", "period_end", "quantity", "unit", "total_usd", "line_items",
                                 "demand_kw") if data.get(k) != old.get(k))
    data.update({"id": bill_id, "building_id": old["building_id"], "source": old.get("source"),
                 "data_label": old.get("data_label", data["data_label"]),
                 "corrections": (old.get("corrections") or []) + ([{"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                                     "fields": changed}] if changed else [])})
    return store.save_bill(data)


@app.post("/api/bills/{bill_id}/confirm")
def confirm_bill(bill_id: str):
    b = store.get_bill(bill_id)
    if not b:
        raise HTTPException(404, "Bill not found")
    try:
        Bill(**{k: v for k, v in b.items() if k in Bill.model_fields})
    except ValidationError as exc:
        raise HTTPException(422, f"Bill is incomplete: {exc.errors()[0]['msg']}")
    b["status"] = "confirmed"
    return store.save_bill(b)


@app.delete("/api/bills/{bill_id}", status_code=204)
def delete_bill(bill_id: str):
    if not store.get_bill(bill_id):
        raise HTTPException(404, "Bill not found")
    store.delete_bill(bill_id)


# --- measure inputs (quotes, assumptions, incentive decisions) -------------------------
@app.get("/api/buildings/{building_id}/measure-inputs")
def get_measure_inputs(building_id: str):
    _building_or_404(building_id)
    return store.list_measure_inputs(building_id)


@app.put("/api/buildings/{building_id}/measure-inputs/{measure_id}")
def put_measure_inputs(building_id: str, measure_id: str, mi: MeasureInputs):
    _building_or_404(building_id)
    from .catalog.measures import MEASURES
    if measure_id not in MEASURES:
        raise HTTPException(404, "Unknown measure")
    _, errors = validate_measure_params(measure_id, mi.params)
    if errors:
        raise HTTPException(422, errors)
    data = mi.model_dump(mode="json")
    data["measure_id"] = measure_id
    return store.save_measure_inputs(building_id, data)


# --- analysis ---------------------------------------------------------------------------
class AnalysisRequest(BaseModel):
    skills: Optional[list[str]] = None  # default: all implemented skills
    settings: dict[str, Any] = {}


@app.post("/api/buildings/{building_id}/analysis")
def run_analysis(building_id: str, req: AnalysisRequest):
    _building_or_404(building_id)
    try:
        return engine.analyze(store, building_id, req.skills, req.settings)
    except InputError as exc:
        raise HTTPException(422, exc.errors)


@app.get("/api/buildings/{building_id}/analysis")
def get_analysis(building_id: str, optional: bool = False):
    """optional=true returns null instead of 404 when nothing has been analysed yet."""
    _building_or_404(building_id)
    a = engine.with_staleness(store, store.get_analysis(building_id))
    if not a:
        if optional:
            return None
        raise HTTPException(404, "No analysis yet")
    return a


@app.get("/api/buildings/{building_id}/explain/{skill_id}")
def explain(building_id: str, skill_id: str):
    a = engine.with_staleness(store, store.get_analysis(building_id))
    if not a or skill_id not in a["results"]:
        raise HTTPException(404, "No result for this skill")
    out = ai.explain(registry.SKILLS[skill_id].name, a["results"][skill_id])
    out["stale"] = skill_id in a.get("stale_skills", [])
    if out["stale"]:
        out["notice"] = "OUT OF DATE: inputs changed after this result was calculated. " + out["notice"]
    return out


# --- plan & reports -------------------------------------------------------------------------
@app.get("/api/buildings/{building_id}/plan")
def get_plan(building_id: str, optional: bool = False):
    _building_or_404(building_id)
    p = engine.get_plan(store, building_id)
    if not p and optional:
        return None
    if not p:
        raise HTTPException(404, "No plan yet - run the analysis with skill 17 selected.")
    return p


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    next_step: Optional[str] = None


@app.patch("/api/buildings/{building_id}/plan/tasks/{task_id}")
def patch_task(building_id: str, task_id: str, upd: TaskUpdate):
    try:
        return engine.update_task(store, building_id, task_id, upd.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(404, "Task or plan not found")


@app.post("/api/buildings/{building_id}/reports", status_code=201)
def export_report(building_id: str, fmt: str = "html"):
    b = _building_or_404(building_id)
    a = engine.with_staleness(store, store.get_analysis(building_id))
    if not a or a["results"].get("20", {}).get("status") != "completed":
        raise HTTPException(409, "Run the analysis with skill 20 selected first.")
    if a["stale"]:
        raise HTTPException(409, a["stale_message"])
    # Re-render from stored results + the CURRENT plan so user task edits are included in the snapshot.
    plan = engine.get_plan(store, building_id)
    md = render_markdown(b, a["results"], plan, a["ran_at"], decision_ready=a.get("decision_ready", True),
                         not_ready_reasons=a.get("not_decision_ready_reasons"),
                         stale_message=plan.get("stale_message") if plan else None,
                         thermal=a["results"].get("08", {}).get("outputs", {}).get("scenarios"))
    content = md if fmt == "md" else markdown_to_html(md, f"Benji report - {b['name']}")
    ready = a.get("decision_ready", True) and not (plan and plan.get("stale"))
    return store.save_report(building_id, "md" if fmt == "md" else "html", content,
                             {"analysis_ran_at": a["ran_at"], "data_label": b.get("data_label"),
                              "synthetic": b.get("data_label") == "synthetic_demo",
                              "decision_ready": ready, "plan_stale": bool(plan and plan.get("stale")),
                              "versions": a.get("versions")})


# --- room heating & cooling scenarios (skill 08) ---------------------------------------------
class ThermalAlternative(BaseModel):
    name: str
    overrides: dict[str, Any] = {}


class ThermalScenarioIn(BaseModel):
    name: str
    inputs: thermal.ScenarioInputs
    alternatives: list[ThermalAlternative] = []
    add_to_plan: bool = False
    selected_alternative: Optional[str] = None


def _check_alternatives(sc: ThermalScenarioIn) -> None:
    base = sc.inputs.model_dump(mode="json")
    errors = []
    for i, alt in enumerate(sc.alternatives):
        try:
            thermal.apply_overrides(base, alt.overrides)
        except ValidationError as exc:
            errors += [{"field": f"alternatives.{i}.overrides." + ".".join(str(p) for p in e["loc"]),
                        "message": e["msg"]} for e in exc.errors()]
    if sc.selected_alternative and sc.selected_alternative not in {a.name for a in sc.alternatives}:
        errors.append({"field": "selected_alternative", "message": "must match an alternative name"})
    if errors:
        raise HTTPException(422, errors)


@app.post("/api/thermal/simulate")
def thermal_simulate(sc: ThermalScenarioIn):
    """Stateless calculation (dashboard preview, integrations). Same function as skill 08."""
    _check_alternatives(sc)
    return thermal.compare(sc.inputs.model_dump(mode="json"), [a.model_dump() for a in sc.alternatives])


@app.get("/api/buildings/{building_id}/thermal-scenarios")
def list_thermal(building_id: str):
    _building_or_404(building_id)
    return store.list_children("thermal_scenarios", building_id)


@app.post("/api/buildings/{building_id}/thermal-scenarios", status_code=201)
def create_thermal(building_id: str, sc: ThermalScenarioIn):
    _building_or_404(building_id)
    _check_alternatives(sc)
    return store.save_child("thermal_scenarios", building_id, sc.model_dump(mode="json"), "th")


@app.put("/api/buildings/{building_id}/thermal-scenarios/{scenario_id}")
def update_thermal(building_id: str, scenario_id: str, sc: ThermalScenarioIn):
    old = store.get_child("thermal_scenarios", scenario_id)
    if not old or old["building_id"] != building_id:
        raise HTTPException(404, "Scenario not found")
    _check_alternatives(sc)
    return store.save_child("thermal_scenarios", building_id, {**sc.model_dump(mode="json"), "id": scenario_id}, "th")


@app.delete("/api/buildings/{building_id}/thermal-scenarios/{scenario_id}", status_code=204)
def delete_thermal(building_id: str, scenario_id: str):
    old = store.get_child("thermal_scenarios", scenario_id)
    if not old or old["building_id"] != building_id:
        raise HTTPException(404, "Scenario not found")
    store.delete_child("thermal_scenarios", scenario_id)


# --- electrification readiness -------------------------------------------------------------------
@app.get("/api/buildings/{building_id}/electrification-readiness")
def electrification_readiness(building_id: str):
    b = _building_or_404(building_id)
    return readiness.checklist(b, store.list_children("documents", building_id),
                               store.list_children("annotations", building_id))


# --- reference documents and annotations ---------------------------------------------------------
DOC_KINDS = {"floor_plan", "panel_schedule", "electrical_drawing", "equipment_schedule", "photo", "other"}


@app.post("/api/buildings/{building_id}/documents", status_code=201)
async def upload_document(building_id: str, kind: str = "other", file: UploadFile = File(...)):
    """Store a plan / schedule as REFERENCE evidence. Extracted words are unconfirmed candidates only."""
    _building_or_404(building_id)
    if kind not in DOC_KINDS:
        raise HTTPException(422, [{"field": "kind", "message": f"must be one of {sorted(DOC_KINDS)}"}])
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (10 MB limit)")
    try:
        doc = documents.ingest(content, file.filename or "upload", kind)
    except ValueError as exc:
        raise HTTPException(422, [{"field": "file", "message": str(exc)}])
    return store.save_child("documents", building_id, doc, "doc")


@app.get("/api/buildings/{building_id}/documents")
def list_documents(building_id: str):
    _building_or_404(building_id)
    return [{k: v for k, v in d.items() if k != "candidates"} | {"candidate_count": len(d.get("candidates", []))}
            for d in store.list_children("documents", building_id)]


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    d = store.get_child("documents", doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return d


@app.get("/api/documents/{doc_id}/file")
def get_document_file(doc_id: str):
    d = store.get_child("documents", doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    path = documents.ROOT / d["stored_path"]
    return FileResponse(path, media_type=d.get("media_type") or "application/octet-stream")


class AnnotationIn(BaseModel):
    document_id: str
    page: int = Field(ge=1, le=10000)
    bbox: Optional[list[float]] = None  # [x0, top, x1, bottom] in PDF points (unrotated page space)
    label: str
    value: Optional[float] = None
    unit: Optional[str] = None
    links: dict[str, str] = {}  # e.g. {"equipment_id": "eq_boiler"} or {"thermal_scenario_id": "th_..."}
    status: str = "user_confirmed"  # an annotation is created by the user, so it is their confirmed reading
    note: Optional[str] = None
    model_config = {"allow_inf_nan": False}


@app.post("/api/buildings/{building_id}/annotations", status_code=201)
def create_annotation(building_id: str, ann: AnnotationIn):
    b = _building_or_404(building_id)
    d = store.get_child("documents", ann.document_id)
    if not d or d["building_id"] != building_id:
        raise HTTPException(404, "Document not found")
    if ann.bbox is not None and (len(ann.bbox) != 4 or ann.bbox[0] >= ann.bbox[2] or ann.bbox[1] >= ann.bbox[3]):
        raise HTTPException(422, [{"field": "bbox", "message": "must be [x0, top, x1, bottom] with x0<x1, top<bottom"}])
    eq_id = ann.links.get("equipment_id")
    if eq_id and not any(e["id"] == eq_id for e in b.get("equipment", [])):
        raise HTTPException(422, [{"field": "links.equipment_id", "message": "unknown equipment id"}])
    saved = store.save_child("annotations", building_id, ann.model_dump(mode="json"), "ann")
    if eq_id:  # keep the evidence reference on the equipment record
        for e in b["equipment"]:
            if e["id"] == eq_id and saved["id"] not in e.setdefault("evidence_refs", []):
                e["evidence_refs"].append(saved["id"])
        store.save_building(b)
    return saved


@app.get("/api/buildings/{building_id}/annotations")
def list_annotations(building_id: str):
    _building_or_404(building_id)
    return store.list_children("annotations", building_id)


@app.get("/api/buildings/{building_id}/reports")
def list_reports(building_id: str):
    return store.list_reports(building_id)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    r = store.get_report(report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    if r["format"] == "html":
        return HTMLResponse(r["content"])
    return PlainTextResponse(r["content"], media_type="text/markdown")


# --- demo mode ----------------------------------------------------------------------------------
@app.post("/api/demo/reset", include_in_schema=False)
def demo_reset():
    if not assistant.demo_mode():
        raise HTTPException(404, "Demo mode is off (set BENJI_DEMO_MODE=1 for development and tests).")
    ids = demo.reset(store)
    for bid in ids:  # analyse immediately so the demo opens on results
        engine.analyze(store, bid)
    return {"demo_buildings": ids, "notice": "Synthetic demonstration data recreated. User buildings were not changed."}


# --- assistant endpoints (ChatGPT Actions, OpenClaw, dashboard quick start) ---------------------------
# Optional shared secret. This is a single-user service, not multi-tenant authorization.
def _require_key(request: Request) -> None:
    key = os.environ.get("BENJI_API_KEY")
    supplied = request.headers.get("authorization", "")
    if key and not secrets.compare_digest(supplied.encode(), f"Bearer {key}".encode()):
        raise HTTPException(401, "Missing or invalid bearer token")


def _channel(request: Request) -> str:
    ch = (request.headers.get("x-benji-channel") or "assistant_api").strip().lower()
    return ch if ch in {"dashboard", "chatgpt", "openclaw", "claude_mcp", "assistant_api"} else "assistant_api"


def _assist(fn, *a):
    try:
        return fn(*a)
    except assistant.AssistantError as exc:
        raise HTTPException(422, exc.errors)
    except KeyError:
        raise HTTPException(404, "Unknown property_id - call GET /assistant/properties")


class BillsIn(BaseModel):
    bills: list[dict[str, Any]]
    confirmed: bool = False


class ConfirmIn(BaseModel):
    bill_ids: Optional[list[str]] = None


@app.get("/assistant/property-types", tags=["assistant"], operation_id="listPropertyTypes")
def a_types(request: Request):
    _require_key(request)
    return assistant.PROPERTY_TYPES


@app.get("/assistant/properties", tags=["assistant"], operation_id="listProperties")
def a_list(request: Request):
    _require_key(request)
    return assistant.list_properties(store)


@app.post("/assistant/properties", tags=["assistant"], operation_id="createProperty", status_code=201)
def a_create(request: Request, body: assistant.PropertyIn):
    """Create a home, small business, office or apartment building. Returns property_id and missing info."""
    _require_key(request)
    return _assist(assistant.create_property, store, body.model_dump(exclude_none=True), _channel(request))


@app.patch("/assistant/properties/{property_id}", tags=["assistant"], operation_id="updateProperty")
def a_update(request: Request, property_id: str, changes: dict[str, Any]):
    _require_key(request)
    return _assist(assistant.update_property, store, property_id, changes, _channel(request))


@app.post("/assistant/properties/{property_id}/bills", tags=["assistant"], operation_id="addBills")
def a_bills(request: Request, property_id: str, body: BillsIn):
    """Add bills: [{fuel, month 'YYYY-MM', quantity, unit, total_usd, fixed_charge_usd?}]. confirmed=true only
    after the user confirmed the values read back to them."""
    _require_key(request)
    return _assist(assistant.add_bills, store, property_id, body.bills, body.confirmed, _channel(request))


@app.post("/assistant/properties/{property_id}/bills/confirm", tags=["assistant"], operation_id="confirmPropertyBills")
def a_confirm(request: Request, property_id: str, body: ConfirmIn):
    _require_key(request)
    return _assist(assistant.confirm_bills, store, property_id, body.bill_ids, _channel(request))


@app.post("/assistant/properties/{property_id}/analyze", tags=["assistant"], operation_id="analyzeProperty")
def a_analyze(request: Request, property_id: str):
    """Run Benji and return a plain-language summary (findings, what to do first, programs, missing info)."""
    _require_key(request)
    return _assist(assistant.analyze, store, property_id, None, _channel(request))


@app.get("/assistant/properties/{property_id}/summary", tags=["assistant"], operation_id="getSummary")
def a_summary(request: Request, property_id: str):
    _require_key(request)
    return _assist(assistant.get_summary, store, property_id)


@app.get("/assistant/properties/{property_id}/plan", tags=["assistant"], operation_id="getPlan")
def a_plan(request: Request, property_id: str):
    _require_key(request)
    return _assist(assistant.get_plan, store, property_id)


@app.get("/assistant/skills", tags=["assistant"], operation_id="listSkills")
def a_skills(request: Request):
    _require_key(request)
    return assistant.list_skills()


@app.get("/assistant/openapi.json", include_in_schema=False)
def a_openapi():
    """OpenAPI 3.1 subset for ChatGPT Actions: only the /assistant tools."""
    full = app.openapi()
    paths = {p: v for p, v in full["paths"].items() if p.startswith("/memory/")}
    spec = {"openapi": full["openapi"], "info": {"title": "Benji assistant API", "version": full["info"]["version"],
            "description": "Benji memory and cross-check tools. Use with the Benji skills "
                           "(skills/benji-orchestrator) as GPT knowledge."},
            "servers": [{"url": assistant.PUBLIC_URL}], "paths": paths,
            "components": {"schemas": full.get("components", {}).get("schemas", {}),
                           "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
            "security": [{"bearer": []}]}
    return spec


# --- memory API: the dashboard and agents without file access read/manage the same files ------------
class MemCreate(BaseModel):
    slug: str
    name: str


class MemWrite(BaseModel):
    content: str
    skill: str = ""


class MemLog(BaseModel):
    skill: str = "-"
    what: str


class MemConfirm(BaseModel):
    bill_ids: Optional[list[str]] = None
    confirmed_by: str = "user"


class MemTask(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    due: Optional[str] = None


class MemAnswer(BaseModel):
    answer: str


def _mem(request: Request, fn, *a):
    _require_key(request)
    try:
        return fn(*a)
    except memory.MemoryError_ as exc:
        raise HTTPException(422, [{"field": "memory", "message": str(exc)}])
    except KeyError as exc:
        raise HTTPException(404, f"Not found: {exc}")


def _mch(request: Request) -> str:
    return (request.headers.get("x-benji-channel") or "dashboard").lower()


@app.get("/memory/info", tags=["memory"], operation_id="memoryInfo")
def m_info(request: Request):
    """Where memory lives on disk (agents with file access, e.g. OpenClaw, point here)."""
    return _mem(request, lambda: {"root": str(memory.root()), "files": list(memory.FILES)})


@app.get("/memory/places", tags=["memory"], operation_id="listPlaces")
def m_list(request: Request):
    """Places with next step, pending bills, open tasks/questions, stale flag and last activity."""
    return _mem(request, memory.list_places)


@app.post("/memory/places", tags=["memory"], operation_id="createPlace", status_code=201)
def m_create(request: Request, body: MemCreate):
    return _mem(request, memory.create_place, body.slug, body.name, _mch(request))


@app.get("/memory/places/{slug}", tags=["memory"], operation_id="readPlace")
def m_read(request: Request, slug: str):
    """Parsed profile, next step, actions, tasks, findings, bills, open questions, log, plus raw files."""
    return _mem(request, memory.read_place, slug)


@app.put("/memory/places/{slug}/files/{name:path}", tags=["memory"], operation_id="writeFile")
def m_write(request: Request, slug: str, name: str, body: MemWrite):
    return _mem(request, memory.write_file, slug, name, body.content, _mch(request), body.skill)


@app.post("/memory/places/{slug}/log", tags=["memory"], operation_id="appendLog")
def m_log(request: Request, slug: str, body: MemLog):
    return _mem(request, lambda: (memory.append_log(slug, body.skill, _mch(request), body.what), {"ok": True})[1])


@app.post("/memory/places/{slug}/bills/confirm", tags=["memory"], operation_id="confirmBills")
def m_confirm(request: Request, slug: str, body: MemConfirm):
    return _mem(request, memory.confirm_bills, slug, body.bill_ids, body.confirmed_by, _mch(request))


@app.patch("/memory/places/{slug}/tasks/{task_id}", tags=["memory"], operation_id="updateTask")
def m_task(request: Request, slug: str, task_id: str, body: MemTask):
    return _mem(request, memory.update_task, slug, task_id, body.status, body.owner, body.due, _mch(request))


@app.post("/memory/places/{slug}/questions/{qid}", tags=["memory"], operation_id="answerQuestion")
def m_answer(request: Request, slug: str, qid: str, body: MemAnswer):
    return _mem(request, memory.answer_question, slug, qid, body.answer, _mch(request))


@app.get("/memory/places/{slug}/cross-check", tags=["memory"], operation_id="crossCheck")
def m_cross(request: Request, slug: str):
    """Deterministic recomputation of costs, options and program leads from profile + confirmed bills."""
    return _mem(request, memory.cross_check, slug)
