"""Lot cockpit, sampling plan, and the non-visual critical check."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...core import db
from ...core.permissions import can_write_lot
from ...services import review as service
from ..deps import check_csrf, current_user, role_required
from ..serializers import clean, decision_payload, timeline
from .shared import _float, _lang, _lot_or_404

router = APIRouter(tags=["lots"])

@router.get("/lots/{lot_id}")
def lot_detail(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id, session)
    plan = service.active_plan(lot_id)
    progress = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    row = service.latest_decision(lot_id)
    decision = decision_payload(row)
    override = service.override_for(row["id"]) if row else None
    history = [decision_payload(item) for item in
               db.q("SELECT d.*, u.display_name AS decided_by FROM decision d"
                    " JOIN app_user u ON u.id=d.created_by WHERE d.lot_id=?"
                    " ORDER BY d.sequence DESC", (lot_id,))]
    is_admin = session["user"]["role"] == "admin"
    return {
        "lot": clean(lot),
        "plan": service.plan_dict(plan),
        "plan_row": clean(plan),
        "progress": progress,
        "units": clean(units),
        "decision": decision,
        "override": clean(override),
        "final": service.final_disposition(row, override) if row else None,
        "history": history,
        "audit": timeline(lot_id),
        "is_admin": is_admin,
        "is_supervisor": session["user"]["role"] == "supervisor",
        "can_write": (not is_admin and can_write_lot(session, lot)
                      and lot["status"] != "decided"),
        "user": clean(session["user"]),
    }


def evidence_summary(lot_id: int) -> dict:
    ev = service.build_evidence(lot_id)
    counts = {"critical": 0, "major": 0, "minor": 0}
    for defect in ev["defects"]:
        severity = defect.get("severity")
        if severity in counts:
            counts[severity] += 1
    return {
        "units_present": ev["units_present"],
        "required_units": ev["required_units"],
        "counts": counts,
        "has_defects": len(ev["defects"]) > 0,
        "nonvisual_status": ev["lot"].get("critical_nonvisual_status", "pending"),
    }



@router.get("/lots/{lot_id}/plan")
def plan_detail(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id, session)
    plan = service.active_plan(lot_id)
    row = service.latest_decision(lot_id)
    return {
        "lot": clean(lot),
        "plan": service.plan_dict(plan),
        "plan_row": clean(plan),
        "progress": service.progress(lot_id),
        "units": clean(service.units_with_views(lot_id)),
        "decision": decision_payload(row),
        "evidence_summary": evidence_summary(lot_id),
        "is_supervisor": session["user"]["role"] == "supervisor",
        "locked": lot["status"] == "decided",
        "user": clean(session["user"]),
    }



@router.post("/lots/{lot_id}/plan")
async def save_plan(request: Request, lot_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id, session)
    if lot["status"] == "decided":
        raise HTTPException(status_code=403, detail="locked")
    data = await request.json()
    lang = _lang(request)

    n = int(data.get("n") or 0)
    counting_mode = str(data.get("counting_mode") or "")
    critical_ac = int(data.get("critical_ac", -1))
    critical_re = int(data.get("critical_re", -1))
    major_ac = int(data.get("major_ac", -1))
    major_re = int(data.get("major_re", -1))
    minor_ac = int(data.get("minor_ac", -1))
    minor_re = int(data.get("minor_re", -1))
    confirmed = str(data.get("confirmed") or "").strip()
    is_demo = 1 if str(data.get("is_demo")) in ("1", "true", "True") else 0
    source_edition = str(data.get("source_edition") or "").strip()
    source_reference = str(data.get("source_reference") or "").strip()

    errors: dict[str, str] = {}
    if not confirmed:
        errors["confirmed"] = ("উৎস থেকে মান মিলিয়ে যাচাইয়ের স্বীকৃতি আবশ্যক।" if lang == "bn"
                               else "Confirmation that values were verified against the source "
                                    "standard / specification is required.")
    if n < 1:
        errors["n"] = ("নমুনার আকার (n) অন্তত ১ হতে হবে।" if lang == "bn"
                       else "Sample size n must be an integer >= 1.")
    elif n > lot["lot_size"]:
        errors["n"] = (f"নমুনার আকার (n) লট সাইজ ({lot['lot_size']})-এর চেয়ে বড় হতে পারে না।"
                       if lang == "bn" else
                       f"Sample size n cannot exceed lot size ({lot['lot_size']}).")
    if counting_mode not in ("highest_class_only", "every_class"):
        errors["counting_mode"] = ("গণনার পদ্ধতি নির্বাচন করুন।" if lang == "bn"
                                   else "Counting mode is required.")
    for key, name_bn, name_en, ac, re_ in (
        ("critical", "ক্রিটিক্যাল", "Critical", critical_ac, critical_re),
        ("major", "মেজর", "Major", major_ac, major_re),
        ("minor", "মাইনর", "Minor", minor_ac, minor_re),
    ):
        if ac < 0:
            errors[f"{key}_ac"] = (f"{name_bn} গ্রহণ সংখ্যা (Ac) ০ বা তার বেশি হতে হবে।" if lang == "bn"
                                   else f"{name_en} acceptance number (Ac) must be >= 0.")
        if re_ < 1:
            errors[f"{key}_re"] = (f"{name_bn} প্রত্যাখ্যান সংখ্যা (Re) অন্তত ১ হতে হবে।" if lang == "bn"
                                   else f"{name_en} rejection number (Re) must be >= 1.")
        elif ac >= 0 and re_ != ac + 1:
            errors[f"{key}_re"] = (
                f"সিঙ্গেল স্যাম্পলিংয়ে Re অবশ্যই Ac + 1 হতে হবে (প্রত্যাশিত Re={ac + 1})।"
                if lang == "bn" else
                f"Single sampling requires Re = Ac + 1 (expected Re={ac + 1}).")
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    final_source_edition = source_edition
    final_source_ref = source_reference
    if is_demo:
        final_source_edition = ("অননুমোদিত ডেমো অনুমান" if lang == "bn"
                                else "Unauthorized demo assumption")
    elif not final_source_edition and not final_source_ref:
        final_source_edition = ("অননুমোদিত অনুমান" if lang == "bn"
                                else "Unauthorized assumption")

    previous = service.active_plan(lot_id)
    version = (previous["version"] + 1) if previous else 1
    db.x("INSERT INTO plan(lot_id,version,n,counting_mode,critical_aql,critical_ac,critical_re,"
         "major_aql,major_ac,major_re,minor_aql,minor_ac,minor_re,inspection_level,sampling_type,"
         "source_edition,source_reference,is_demo,entered_by,created_at)"
         " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'II','single',?,?,?,?,?)",
         (lot_id, version, n, counting_mode, _float(data.get("critical_aql")), critical_ac, critical_re,
          _float(data.get("major_aql")), major_ac, major_re,
          _float(data.get("minor_aql")), minor_ac, minor_re,
          final_source_edition, final_source_ref, is_demo, session["user"]["id"], db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "plan.confirmed", "lot", lot_id,
             after={"version": version, "n": n, "mode": counting_mode,
                    "confirmed_by": session["user"]["display_name"], "confirmed_at": db.now(),
                    "source": final_source_edition, "is_demo": is_demo})
    db.audit(session["user"]["id"], session["user"]["display_name"], "plan.created", "lot", lot_id,
             after={"version": version, "n": n, "mode": counting_mode, "source": final_source_edition})

    have = db.one("SELECT COUNT(*) c FROM sample_unit WHERE lot_id=?", (lot_id,))["c"]
    if have == 0:
        for index in range(1, n + 1):
            unit_id = db.x("INSERT INTO sample_unit(lot_id, garment_code, created_at) VALUES (?,?,?)",
                           (lot_id, f"G-{index:02d}", db.now()))
            for side in ("front", "back"):
                db.x("INSERT INTO unit_view(sample_unit_id, side, required) VALUES (?,?,1)",
                     (unit_id, side))
        db.audit(session["user"]["id"], session["user"]["display_name"], "units.generated", "lot",
                 lot_id, after={"count": n, "views": n * 2})
    return {"ok": True, "plan": service.plan_dict(service.active_plan(lot_id))}


@router.post("/lots/{lot_id}/nonvisual")
async def set_nonvisual(request: Request, lot_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id, session)
    data = await request.json()
    status = str(data.get("status") or "")
    note = str(data.get("note") or "")
    if status not in ("pending", "done", "not_required", "failed"):
        raise HTTPException(status_code=422, detail="invalid")
    if status == "failed" and len(note.strip()) < 3:
        raise HTTPException(status_code=422, detail="note_required")
    if lot["status"] == "decided" and status != lot["critical_nonvisual_status"]:
        raise HTTPException(status_code=403, detail="locked")
    db.x("UPDATE lot SET critical_nonvisual_status=?, nonvisual_note=? WHERE id=?",
         (status, note.strip() or None, lot_id))
    db.audit(session["user"]["id"], session["user"]["display_name"], "lot.nonvisual_changed", "lot",
             lot_id, before={"status": lot["critical_nonvisual_status"]},
             after={"status": status, "note": note.strip()})
    return {"ok": True}
