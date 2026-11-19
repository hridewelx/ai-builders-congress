"""Single-lot cockpit: overview, sampling plan, non-visual check."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...core import db
from ...services import review as service
from ..deps import Denied, assert_csrf, can_write_lot, lot_required, require_role, require_user
from ..pages import lang_of, page

router = APIRouter(tags=["lots"])


def evidence_summary(lot_id: int) -> dict:
    ev = service.build_evidence(lot_id)
    counts = {"critical": 0, "major": 0, "minor": 0}
    for d in ev["defects"]:
        sev = d.get("severity")
        if sev in counts:
            counts[sev] += 1
    return {
        "units_present": ev["units_present"],
        "required_units": ev["required_units"],
        "counts": counts,
        "has_defects": len(ev["defects"]) > 0,
        "nonvisual_status": ev["lot"].get("critical_nonvisual_status", "pending"),
    }


@router.get("/lots/{lot_id}", response_class=HTMLResponse)
def lot_page(request: Request, lot_id: int):
    s = require_user(request)
    L = lot_required(s, lot_id)
    plan = service.active_plan(lot_id)
    p = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC", (lot_id,))
    audit = service.timeline(lot_id)
    is_admin = s["user"]["role"] == "admin"
    return page(request, "lot.html", active="lots", lot=L, plan=plan, plan_d=service.plan_dict(plan),
                progress=p, units=units, decision=d, override=ov,
                final=service.final_disposition(d, ov) if d else None, history=hist, audit=audit,
                is_admin=is_admin, can_write=(not is_admin and can_write_lot(s, L) and L["status"] != "decided"))


@router.get("/lots/{lot_id}/plan", response_class=HTMLResponse)
def plan_page(request: Request, lot_id: int):
    s = require_user(request)
    L = lot_required(s, lot_id)
    plan = service.active_plan(lot_id)
    p = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ev_summary = evidence_summary(lot_id)
    return page(request, "plan.html", active="lots", lot=L, plan=plan, plan_d=service.plan_dict(plan),
                progress=p, units=units, decision=d, evidence_summary=ev_summary,
                is_supervisor=s["user"]["role"] == "supervisor",
                locked=L["status"] == "decided")


@router.post("/lots/{lot_id}/plan")
def plan_save(request: Request, lot_id: int, csrf: str = Form(""), n: int = Form(0),
              counting_mode: str = Form(""), critical_ac: int = Form(-1), critical_re: int = Form(-1),
              major_ac: int = Form(-1), major_re: int = Form(-1), minor_ac: int = Form(-1),
              minor_re: int = Form(-1), critical_aql: str = Form(""), major_aql: str = Form(""),
              minor_aql: str = Form(""), source_edition: str = Form(""), source_reference: str = Form(""),
              confirmed: str = Form(""), is_demo: int = Form(0)):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    L = lot_required(s, lot_id)
    if L["status"] == "decided":
        raise Denied(403, "locked")

    lang = lang_of(request)
    errors: dict[str, str] = {}

    is_demo_val = 1 if str(is_demo) in ("1", "true", "True") else 0
    source_edition_str = "" if not isinstance(source_edition, str) else source_edition.strip()
    source_ref_str = "" if not isinstance(source_reference, str) else source_reference.strip()
    confirmed_str = "" if not isinstance(confirmed, str) else confirmed.strip()

    if not confirmed_str:
        errors["confirmed"] = (
            "উৎস থেকে মান মিলিয়ে যাচাইয়ের স্বীকৃতি আবশ্যক।"
            if lang == "bn" else
            "Confirmation that values were verified against the source standard / specification is required."
        )

    if n < 1:
        errors["n"] = (
            "নমুনার আকার (n) অন্তত ১ হতে হবে।"
            if lang == "bn" else
            "Sample size n must be an integer >= 1."
        )
    elif n > L["lot_size"]:
        errors["n"] = (
            f"নমুনার আকার (n) লট সাইজ ({L['lot_size']})-এর চেয়ে বড় হতে পারে না।"
            if lang == "bn" else
            f"Sample size n cannot exceed lot size ({L['lot_size']})."
        )

    if counting_mode not in ("highest_class_only", "every_class"):
        errors["counting_mode"] = (
            "গণনার পদ্ধতি নির্বাচন করুন।"
            if lang == "bn" else
            "Counting mode is required."
        )

    classes_info = [
        ("critical", "ক্রিটিক্যাল", "Critical", critical_ac, critical_re),
        ("major", "মেজর", "Major", major_ac, major_re),
        ("minor", "মাইনর", "Minor", minor_ac, minor_re),
    ]

    for c_key, c_name_bn, c_name_en, ac, re_ in classes_info:
        if ac < 0:
            errors[f"{c_key}_ac"] = (
                f"{c_name_bn} গ্রহণ সংখ্যা (Ac) ০ বা তার বেশি হতে হবে।"
                if lang == "bn" else
                f"{c_name_en} acceptance number (Ac) must be >= 0."
            )
        if re_ < 1:
            errors[f"{c_key}_re"] = (
                f"{c_name_bn} প্রত্যাখ্যান সংখ্যা (Re) অন্তত ১ হতে হবে।"
                if lang == "bn" else
                f"{c_name_en} rejection number (Re) must be >= 1."
            )
        elif ac >= 0 and re_ != ac + 1:
            errors[f"{c_key}_re"] = (
                f"সিঙ্গেল স্যাম্পলিংয়ে Re অবশ্যই Ac + 1 হতে হবে (প্রত্যাশিত Re={ac + 1})।"
                if lang == "bn" else
                f"Single sampling requires Re = Ac + 1 (expected Re={ac + 1})."
            )

    form_data = {
        "n": n if n > 0 else "",
        "counting_mode": counting_mode,
        "critical_ac": critical_ac if critical_ac >= 0 else "",
        "critical_re": critical_re if critical_re >= 0 else "",
        "major_ac": major_ac if major_ac >= 0 else "",
        "major_re": major_re if major_re >= 0 else "",
        "minor_ac": minor_ac if minor_ac >= 0 else "",
        "minor_re": minor_re if minor_re >= 0 else "",
        "critical_aql": critical_aql,
        "major_aql": major_aql,
        "minor_aql": minor_aql,
        "source_edition": source_edition,
        "source_reference": source_reference,
        "is_demo": is_demo,
        "confirmed": confirmed,
    }

    if errors:
        plan = service.active_plan(lot_id)
        p = service.progress(lot_id)
        units = service.units_with_views(lot_id)
        d = service.latest_decision(lot_id)
        ev_summary = evidence_summary(lot_id)
        return page(request, "plan.html", status_code=422, active="lots", lot=L, plan=plan,
                    plan_d=service.plan_dict(plan), progress=p, units=units, decision=d,
                    evidence_summary=ev_summary, is_supervisor=True, locked=False,
                    errors=errors, form_data=form_data)

    final_source_edition = source_edition_str
    final_source_ref = source_ref_str
    final_is_demo = is_demo_val
    if final_is_demo:
        final_source_edition = "অননুমোদিত ডেমো অনুমান" if lang == "bn" else "Unauthorized demo assumption"
    elif not final_source_edition and not final_source_ref:
        final_source_edition = "অননুমোদিত অনুমান" if lang == "bn" else "Unauthorized assumption"

    prev = service.active_plan(lot_id)
    ver = (prev["version"] + 1) if prev else 1
    db.x("INSERT INTO plan(lot_id,version,n,counting_mode,critical_aql,critical_ac,critical_re,"
         "major_aql,major_ac,major_re,minor_aql,minor_ac,minor_re,inspection_level,sampling_type,"
         "source_edition,source_reference,is_demo,entered_by,created_at)"
         " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'II','single',?,?,?,?,?)",
         (lot_id, ver, n, counting_mode, _f(critical_aql), critical_ac, critical_re,
          _f(major_aql), major_ac, major_re, _f(minor_aql), minor_ac, minor_re,
          final_source_edition, final_source_ref, final_is_demo, s["user"]["id"], db.now()))

    # Audit trail
    db.audit(s["user"]["id"], s["user"]["display_name"], "plan.confirmed", "lot", lot_id,
             after={"version": ver, "n": n, "mode": counting_mode, "confirmed_by": s["user"]["display_name"],
                    "confirmed_at": db.now(), "source": final_source_edition, "is_demo": final_is_demo})
    db.audit(s["user"]["id"], s["user"]["display_name"], "plan.created", "lot", lot_id,
             after={"version": ver, "n": n, "mode": counting_mode, "source": final_source_edition})

    # Sample slots generation
    have = db.one("SELECT COUNT(*) c FROM sample_unit WHERE lot_id=?", (lot_id,))["c"]
    if have == 0:
        for i in range(1, n + 1):
            uid = db.x("INSERT INTO sample_unit(lot_id, garment_code, created_at) VALUES (?,?,?)",
                       (lot_id, f"G-{i:02d}", db.now()))
            for side in ("front", "back"):
                db.x("INSERT INTO unit_view(sample_unit_id, side, required) VALUES (?,?,1)", (uid, side))
        db.audit(s["user"]["id"], s["user"]["display_name"], "units.generated", "lot", lot_id,
                 after={"count": n, "views": n * 2})

    return RedirectResponse(f"/lots/{lot_id}/plan?ok=saved", status_code=303)


def _f(v: str):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


@router.post("/lots/{lot_id}/nonvisual")
def nonvisual(request: Request, lot_id: int, csrf: str = Form(""), status: str = Form(""),
              note: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    L = lot_required(s, lot_id)
    if status not in ("pending", "done", "not_required", "failed"):
        raise Denied(422, "invalid")
    if status == "failed" and len(note.strip()) < 3:
        raise Denied(422, "note_required")
    if L["status"] == "decided" and status != L["critical_nonvisual_status"]:
        raise Denied(403, "locked")
    db.x("UPDATE lot SET critical_nonvisual_status=?, nonvisual_note=? WHERE id=?",
         (status, note.strip() or None, lot_id))
    db.audit(s["user"]["id"], s["user"]["display_name"], "lot.nonvisual_changed", "lot", lot_id,
             before={"status": L["critical_nonvisual_status"]}, after={"status": status, "note": note.strip()})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)
