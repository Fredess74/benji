"""Electrification-readiness evidence checklist.

Benji records what is KNOWN (with sources) and what an electrician must confirm. It never infers wiring
topology, available capacity (e.g. from the sum of breakers) or conductor sizing, and never states that an
installation is safe or code compliant.
"""

from __future__ import annotations

QUESTIONS = [
    "What is the service size (A) and voltage/phase, and what does a load calculation show is available?",
    "Is there panel space for new dedicated circuits, or is a panel or service upgrade needed?",
    "What circuits, conductors and disconnects will each heat pump / heat pump water heater need?",
    "Does the utility need to be notified or upgrade the service drop / transformer?",
    "Are permits and inspections required for this work?",
]


def checklist(building: dict, documents: list[dict] | None = None, annotations: list[dict] | None = None) -> dict:
    es = building.get("electrical_service") or {}
    known, missing = [], []
    for field, label in [("service_amps", "Service size (A)"), ("service_voltage", "Service voltage (V)"),
                         ("phases", "Phases"), ("main_panel_id", "Main panel identifier"),
                         ("main_breaker_amps", "Main breaker rating (A)"), ("spare_breaker_spaces", "Spare breaker spaces")]:
        if es.get(field) is not None:
            known.append({"item": label, "value": es[field], "source": es.get("source") or "user entry (source not stated)",
                          "evidence_refs": es.get("evidence_refs", []), "status": "user_reported"})
        else:
            missing.append({"item": label, "ask": "electrician or panel label"})
    equip = []
    for e in building.get("equipment") or []:
        if e.get("kind") in ("heat_pump", "electric_resistance", "water_heater", "split_ac", "chiller", "rooftop_unit") \
                or e.get("fuel") == "electricity":
            equip.append({"equipment_id": e["id"], "kind": e["kind"],
                          "electrical_input_kw": e.get("electrical_input_kw"), "circuit_ref": e.get("circuit_ref"),
                          "evidence_refs": e.get("evidence_refs", []),
                          "missing": [x for x, v in (("nameplate electrical input", e.get("electrical_input_kw")),
                                                     ("assigned circuit", e.get("circuit_ref"))) if v is None]})
    docs = [{"document_id": d["id"], "kind": d.get("kind"), "filename": d.get("filename")}
            for d in (documents or []) if d.get("kind") in ("panel_schedule", "electrical_drawing")]
    if not docs:
        missing.append({"item": "Panel schedule or electrical drawing", "ask": "upload as reference evidence"})
    return {
        "known_facts": known, "electrical_equipment": equip, "reference_documents": docs, "missing": missing,
        "questions_for_electrician": QUESTIONS,
        "status": "evidence_incomplete" if missing else "evidence_collected_needs_electrician_review",
        "disclaimer": "Evidence checklist only. Benji does not calculate available electrical capacity, infer wiring "
                      "from drawings, or determine safety or code compliance. A licensed electrician must confirm.",
    }
