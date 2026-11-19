"""Serialisation helpers shared by the JSON endpoints."""
from __future__ import annotations

import json
import sqlite3

from .. import i18n
from ..config import DEMO_LOGIN, ZONES
from ..core import db
from ..domain import engine
from ..domain.reason_catalog import REASON_CATALOG
from ..services import detector, vision
from ..services import review as service
from ..services.stats import load_model_card


def clean(value):
    """Recursively convert sqlite rows and tuples into JSON-safe values."""
    if isinstance(value, sqlite3.Row):
        return {key: clean(value[key]) for key in value.keys()}
    if isinstance(value, dict):
        return {key: clean(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return value


def public_user(user) -> dict:
    if not user:
        return {}
    data = dict(user)
    data.pop("password_hash", None)
    return clean(data)


def bootstrap() -> dict:
    return {
        "catalog": {key: {"en": pair[0], "bn": pair[1]} for key, pair in i18n.STR.items()},
        "reasons": REASON_CATALOG,
        "zones": ZONES,
        "human_classes": list(vision.HUMAN_CLASSES),
        "demo_login": DEMO_LOGIN,
    }


def model_info() -> dict:
    card = load_model_card()
    return {
        "model": detector.MODEL_NAME if detector.available() else vision.MODEL_NAME,
        "detector": detector.active_backend(),
        "model_ok": bool(card.get("self_test", {}).get("passed", False)),
        "card": card,
    }


def catalogs() -> dict:
    buyers = [clean(row) for row in db.q("SELECT * FROM buyer ORDER BY name")]
    products = [clean(row) for row in db.q("SELECT * FROM product ORDER BY name")]
    return {"buyers": buyers, "products": products}


def lot_card(row) -> dict:
    data = clean(row)
    decision = service.latest_decision(data["id"])
    override = service.override_for(decision["id"]) if decision else None
    final = service.final_disposition(decision, override) if decision else None
    data.update({
        "decision": decision_payload(decision, parsed=False),
        "override": clean(override),
        "final": final,
        "progress": service.progress(data["id"]),
    })
    return data


def lot_cards(state: str = "", outcome: str = "", q: str = "") -> list[dict]:
    rows = db.q("SELECT l.*, b.name AS buyer_name, p.name AS product_name"
                " FROM lot l JOIN buyer b ON b.id=l.buyer_id"
                " JOIN product p ON p.id=l.product_id ORDER BY l.id DESC")
    out = []
    for row in rows:
        card = lot_card(row)
        if state and card["status"] != state:
            continue
        if outcome and card["final"] != outcome:
            continue
        if q:
            hay = f"{card['lot_code']} {card['buyer_name']} {card['product_name']} {card['color']}".lower()
            if q.lower() not in hay:
                continue
        out.append(card)
    return out


def decision_payload(row, parsed: bool = True) -> dict | None:
    if not row:
        return None
    data = clean(row)
    for key, fallback in (("reasons", "[]"), ("counts", "{}"),
                          ("class_limits", "{}"), ("completeness", "{}")):
        value = data.get(key)
        if parsed and isinstance(value, str):
            data[key] = json.loads(value or fallback)
    if parsed and isinstance(data.get("plan_snapshot"), str) and data["plan_snapshot"]:
        data["plan_snapshot"] = json.loads(data["plan_snapshot"])
    return data


def timeline(lot_id: int) -> list[dict]:
    rows = service.timeline(lot_id)
    return [clean(row) for row in rows]


def parse_decision_row(row) -> dict | None:
    data = decision_payload(row)
    return data


def model_summary(lot_id: int) -> tuple[str, str]:
    rows = db.q("SELECT DISTINCT ij.model_version FROM inference_job ij"
                " JOIN image i ON i.id=ij.image_id"
                " WHERE i.lot_id=? AND ij.status='succeeded'"
                " ORDER BY ij.model_version", (lot_id,))
    names = sorted({str(row["model_version"]) for row in rows
                    if row["model_version"] and row["model_version"] != "manual"})
    if not names:
        return "manual only", "no model proposal used in this decision"
    if names == [vision.MODEL_NAME]:
        return names[0], "staged knit panels only (unsupervised baseline)"
    if names == [detector.MODEL_NAME]:
        return names[0], detector.MODEL_DOMAIN
    return ", ".join(names), "mixed model provenance; inspect the inference jobs for this lot"


def report_context(lot_id: int) -> dict:
    """The exact stored decision, shaped for the printable one-page report."""
    lot = service.lot(lot_id)
    decision = service.latest_decision(lot_id)
    if not lot or not decision:
        return None
    override = service.override_for(decision["id"])
    plan = json.loads(decision["plan_snapshot"]) if decision["plan_snapshot"] else None
    reasons = json.loads(decision["reasons"])
    completeness = json.loads(decision["completeness"])
    counts = json.loads(decision["counts"])
    limits = json.loads(decision["class_limits"] or "{}")
    class_status = {
        klass: {
            "count": counts.get(klass, 0),
            "ac": limits.get(klass, {}).get("ac"),
            "re": limits.get(klass, {}).get("re"),
            "status": ("FAIL" if limits.get(klass)
                       and counts.get(klass, 0) >= limits[klass]["re"] else "PASS"),
        }
        for klass in engine.CLASSES
    } if limits else {}
    images = db.one("SELECT COUNT(*) AS n FROM image WHERE lot_id=? AND purged=0", (lot_id,))["n"]
    units = db.one("SELECT COUNT(*) AS n FROM sample_unit WHERE lot_id=?", (lot_id,))["n"]
    model_name, model_domains = model_summary(lot_id)
    return {
        "lot_code": lot["lot_code"],
        "product": lot["product_name"],
        "buyer": lot["buyer_name"],
        "sequence": decision["sequence"],
        "created_at": decision["created_at"],
        "engine_version": decision["engine_version"],
        "outcome": decision["outcome"],
        "override": {
            "final_disposition": override["final_disposition"],
            "reason": override["reason"],
            "approved": override["effective"],
        } if override else None,
        "plan": plan,
        "n_effective": (plan or {}).get("n"),
        "counts": counts,
        "class_status": class_status,
        "reasons": [{"code": code, "text": engine.REASONS.get(code, ("", code))[1]}
                    for code in reasons],
        "units_present": completeness.get("units_present"),
        "required_units": completeness.get("required_units"),
        "views_pending": completeness.get("views_pending"),
        "evidence_bad": completeness.get("evidence_bad"),
        "nonvisual": lot["critical_nonvisual_status"],
        "images": images,
        "units": units,
        "model": model_name,
        "model_domains": model_domains,
        "manual": bool(decision["manual_inspection"]),
        "selection": lot["selection_method"],
        "snapshot_hash": decision["snapshot_hash"],
        "lot": clean(lot),
        "decision": decision_payload(decision),
        "progress": service.progress(lot_id),
        "reasons_raw": reasons,
    }
