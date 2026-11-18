"""Deterministic AQL decision engine.

Pure function: (plan, sample evidence) -> recommendation. Imports no web,
database or ML package. Implements PRD 9.4 / SD 8.6 precedence exactly:

    plan -> REJECT -> ESCALATE -> other HOLD -> ACCEPT

The AI never appears here. Only human-confirmed defect rows enter the count.
"""
from __future__ import annotations

import hashlib
import json

ENGINE_VERSION = "lotline-engine-1.2.0"

CLASSES = ("critical", "major", "minor")
SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1}

REASONS = {
    "HOLD_PLAN_MISSING": ("HOLD", "No sampling plan is configured."),
    "HOLD_PLAN_INVALID": ("HOLD", "The entered plan is not a valid single-sampling plan."),
    "REJECT_CRITICAL_NONVISUAL_FAILED": ("REJECT", "A critical non-visual check failed."),
    "REJECT_LIMIT_REACHED": ("REJECT", "At least one class reached its rejection number."),
    "ESCALATE_CRITICAL_UNREVIEWED": ("ESCALATE", "An open proposal routes to a critical clause."),
    "ESCALATE_UNMAPPED_CLAUSE": ("ESCALATE", "A confirmed defect has no mapped buyer clause."),
    "ESCALATE_CRITICAL_REJECTION_UNCONFIRMED": ("ESCALATE", "A rejected critical proposal needs a second review."),
    "ESCALATE_SECOND_OPINION_REQUESTED": ("ESCALATE", "A reviewer requested a second opinion."),
    "HOLD_UNITS_MISSING": ("HOLD", "Fewer garments than the required sample."),
    "HOLD_VIEWS_PENDING": ("HOLD", "A required view has not been reviewed."),
    "HOLD_CRITICAL_NONVISUAL_PENDING": ("HOLD", "The critical non-visual check is not recorded."),
    "HOLD_VIEW_STATE_INCONSISTENT": ("HOLD", "A view's review state contradicts its confirmed defects."),
    "HOLD_EVIDENCE_INTEGRITY": ("HOLD", "An included image file is missing or altered."),
    "HOLD_COMPUTE_ERROR": ("HOLD", "A technical error stopped verification."),
    "ACCEPT_PLAN_MET": ("ACCEPT", "Every class is at or below its acceptance number."),
}


class PlanInvalid(Exception):
    pass


def validate_plan(plan: dict | None) -> list[str]:
    """Return a list of validation errors; empty list means the plan is usable."""
    if not plan:
        return ["no plan"]
    errs: list[str] = []
    n = plan.get("n")
    if not isinstance(n, int) or n < 1:
        errs.append("n must be an integer >= 1")
    if plan.get("counting_mode") not in ("highest_class_only", "every_class"):
        errs.append("counting_mode is required")
    for c in CLASSES:
        lim = plan.get(c) or {}
        ac, re_ = lim.get("ac"), lim.get("re")
        if not isinstance(ac, int) or ac < 0:
            errs.append(f"{c}_ac is required")
        if not isinstance(re_, int) or re_ < 0:
            errs.append(f"{c}_re is required")
        elif isinstance(ac, int) and re_ != ac + 1:
            errs.append(f"{c}: Re must equal Ac + 1 (single sampling, Version 1)")
    return errs


def count_units(defects: list[dict], unit_count: int, mode: str) -> dict[str, int]:
    """Group eligible confirmed defects by sample unit, then count per class."""
    by_unit: dict[int, set[str]] = {}
    for d in defects:
        sev = d.get("severity")
        if not sev or sev not in SEVERITY_RANK:
            continue
        by_unit.setdefault(d["unit_id"], set()).add(sev)
    counts = {c: 0 for c in CLASSES}
    for unit_id, sevs in by_unit.items():
        if mode == "every_class":
            for s in sevs:
                counts[s] += 1
        else:
            counts[max(sevs, key=lambda s: SEVERITY_RANK[s])] += 1
    return counts


def snapshot_hash(rows: list[dict]) -> str:
    canon = json.dumps(sorted(rows, key=lambda r: (r.get("unit_id", 0), r.get("defect_id", 0))),
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def decide(inp: dict) -> dict:
    """inp keys: plan, lot, units[], defects[], units_present, required_units.

    Each unit: {id, views:[{side, required, has_image, review_state, evidence_ok,
                            live_job, inference_status,
                            predictions:[{id, provisional_critical, review_state,
                                          second_review, second_opinion,
                                          confirmed_severity}]}]}
    Each defect: {defect_id, unit_id, severity, type, zone, size_band, image_id, current_image}
    """
    plan = inp.get("plan")
    lot = inp.get("lot") or {}
    units = inp.get("units") or []
    defects = inp.get("defects") or []
    present = int(inp.get("units_present") or 0)
    required = int(inp.get("required_units") or 0)
    compute_error = inp.get("compute_error")

    reasons: list[str] = []
    detail: list[dict] = []

    def add(code: str) -> None:
        if code not in reasons:
            reasons.append(code)

    # Tier 0 / 1 -- plan
    if not plan:
        add("HOLD_PLAN_MISSING")
        return _out("HOLD", reasons, {c: 0 for c in CLASSES}, None, detail,
                    {"units_present": present, "required_units": required, "complete": False}, lot)
    errs = validate_plan(plan)
    if errs:
        add("HOLD_PLAN_INVALID")
        detail.extend({"kind": "plan_error", "text": e} for e in errs)
        return _out("HOLD", reasons, {c: 0 for c in CLASSES}, plan, detail,
                    {"units_present": present, "required_units": required, "complete": False,
                     "plan_errors": errs}, lot)

    mode = plan["counting_mode"]
    n_effective = min(int(plan["n"]), int(lot.get("lot_size") or 0) or int(plan["n"]))

    # Eligibility: confirmed, not retracted, on the current image, view reviewed.
    eligible, unmapped = [], []
    for d in defects:
        if d.get("retracted"):
            continue
        if not d.get("current_image"):
            continue
        if not d.get("view_reviewed"):
            continue
        if d.get("severity") in SEVERITY_RANK:
            eligible.append(d)
        else:
            unmapped.append(d)

    counts = count_units(eligible, len(units), mode)

    # Completeness and gates
    units_missing = present < required
    views_pending = 0
    inconsistent = 0
    evidence_bad = 0
    open_critical = 0
    critical_rej_pending = 0
    second_opinion = 0
    manual_only = 0

    for u in units:
        for v in u.get("views") or []:
            if v.get("evidence_ok") is False:
                evidence_bad += 1
            if not v.get("has_image"):
                if v.get("required"):
                    views_pending += 1
                continue
            rs = v.get("review_state")
            preds = v.get("predictions") or []
            confirmed_here = [p for p in preds if p.get("review_state") == "confirmed"]
            if v.get("inference_status") == "failed" and not rs:
                manual_only += 1
            if not rs:
                if v.get("required"):
                    views_pending += 1
                if v.get("live_job"):
                    views_pending += 1
            elif rs == "needs_retake":
                views_pending += 1
            elif rs == "reviewed_clean" and confirmed_here:
                inconsistent += 1
            # An unanswered proposal is an ESCALATE condition even when the view
            # has no review yet: the engine must see it before it decides HOLD.
            for p in preds:
                if p.get("review_state") == "proposed":
                    if p.get("provisional_critical"):
                        open_critical += 1
                    if v.get("required"):
                        views_pending += 1
                if p.get("review_state") == "rejected" and p.get("provisional_critical") \
                        and p.get("second_review") == "pending":
                    critical_rej_pending += 1
                if p.get("second_opinion") and p.get("review_state") != "proposed":
                    second_opinion += 1

    complete = not (units_missing or views_pending or inconsistent or evidence_bad)
    completeness = {
        "units_present": present,
        "required_units": required,
        "n_effective": n_effective,
        "complete": complete,
        "units_missing": units_missing,
        "views_pending": views_pending,
        "inconsistent": inconsistent,
        "evidence_bad": evidence_bad,
        "open_critical": open_critical,
        "unmapped": len(unmapped),
        "critical_rejection_pending": critical_rej_pending,
        "second_opinion": second_opinion,
        "manual_only": manual_only,
    }

    # Tier 2a -- critical non-visual failed
    if lot.get("critical_nonvisual_status") == "failed":
        add("REJECT_CRITICAL_NONVISUAL_FAILED")

    # Tier 2b -- limit reached on a complete, verified sample
    limit_reached = any(counts[c] >= int(plan[c]["re"]) for c in CLASSES)
    if complete and limit_reached:
        add("REJECT_LIMIT_REACHED")

    # Tier 3..6 -- ESCALATE
    if open_critical:
        add("ESCALATE_CRITICAL_UNREVIEWED")
    if unmapped:
        add("ESCALATE_UNMAPPED_CLAUSE")
    if critical_rej_pending:
        add("ESCALATE_CRITICAL_REJECTION_UNCONFIRMED")
    if second_opinion:
        add("ESCALATE_SECOND_OPINION_REQUESTED")

    # Tier 7..12 -- HOLD
    if units_missing:
        add("HOLD_UNITS_MISSING")
    if views_pending:
        add("HOLD_VIEWS_PENDING")
    if lot.get("critical_nonvisual_status") == "pending":
        add("HOLD_CRITICAL_NONVISUAL_PENDING")
    if inconsistent:
        add("HOLD_VIEW_STATE_INCONSISTENT")
    if evidence_bad:
        add("HOLD_EVIDENCE_INTEGRITY")
    if compute_error:
        add("HOLD_COMPUTE_ERROR")

    if not reasons:
        add("ACCEPT_PLAN_MET")

    outcome = REASONS[reasons[0]][0]
    for r in reasons:
        detail.append({"kind": "reason", "code": r, "text": REASONS[r][1], "outcome": REASONS[r][0]})
    class_status = {}
    for c in CLASSES:
        ac, re_ = int(plan[c]["ac"]), int(plan[c]["re"])
        class_status[c] = {"count": counts[c], "ac": ac, "re": re_,
                           "status": "FAIL" if counts[c] >= re_ else "PASS",
                           "at_acceptance": counts[c] == ac}
    return _out(outcome, reasons, counts, plan, detail, completeness, lot, class_status)


def _out(outcome, reasons, counts, plan, detail, completeness, lot, class_status=None):
    return {
        "outcome": outcome,
        "reasons": reasons,
        "primary_reason": reasons[0] if reasons else "HOLD_COMPUTE_ERROR",
        "counts": counts,
        "class_status": class_status or {},
        "plan": plan,
        "detail": detail,
        "completeness": completeness,
        "engine_version": ENGINE_VERSION,
        "counting_mode": (plan or {}).get("counting_mode"),
    }
