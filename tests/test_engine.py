"""Deterministic engine tests.

Every failure path must end in HOLD, ESCALATE or REJECT -- never ACCEPT.
These tests are the contract the demo relies on: they call the engine as a pure
function, with no database, web layer or model in the loop.
"""
from __future__ import annotations

import copy
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import engine  # noqa: E402

PLAN = {
    "n": 8,
    "counting_mode": "highest_class_only",
    "critical": {"ac": 0, "re": 1, "aql": 0.0},
    "major": {"ac": 1, "re": 2, "aql": 2.5},
    "minor": {"ac": 2, "re": 3, "aql": 4.0},
}
LOT = {"lot_size": 480, "critical_nonvisual_status": "done"}
SIDES = ("front", "back")


def view(state="reviewed_clean", *, required=True, image=True, evidence=True, preds=None):
    return {
        "side": "front",
        "required": required,
        "has_image": image,
        "review_state": state,
        "evidence_ok": evidence,
        "predictions": preds or [],
    }


def units(n=8, *, state="reviewed_clean", sides=SIDES):
    out = []
    for i in range(1, n + 1):
        out.append({"id": i, "views": [dict(view(state), side=s) for s in sides]})
    return out


def defect(unit_id=1, severity="critical", **kw):
    d = {
        "defect_id": unit_id * 10,
        "unit_id": unit_id,
        "severity": severity,
        "type": "hole",
        "zone": "II",
        "current_image": True,
        "view_reviewed": True,
    }
    d.update(kw)
    return d


def run(plan=PLAN, lot=LOT, units_=None, defects=None, present=None, required=8, **kw):
    u = units() if units_ is None else units_
    return engine.decide({
        "plan": plan,
        "lot": lot,
        "units": u,
        "defects": defects or [],
        "units_present": present if present is not None else len(u),
        "required_units": required,
        **kw,
    })


# ---------------------------------------------------------------- happy path
def test_clean_complete_sample_accepts():
    out = run()
    assert out["outcome"] == "ACCEPT"
    assert out["reasons"] == ["ACCEPT_PLAN_MET"]
    assert out["counts"] == {"critical": 0, "major": 0, "minor": 0}
    assert out["completeness"]["complete"] is True


def test_count_equal_to_acceptance_number_still_accepts():
    out = run(defects=[defect(1, "major")])
    assert out["outcome"] == "ACCEPT"
    assert out["counts"]["major"] == 1
    assert out["class_status"]["major"]["at_acceptance"] is True


# ------------------------------------------------------------------- rejects
def test_critical_defect_rejects_on_complete_sample():
    out = run(defects=[defect(1, "critical")])
    assert out["outcome"] == "REJECT"
    assert out["primary_reason"] == "REJECT_LIMIT_REACHED"
    assert out["class_status"]["critical"]["status"] == "FAIL"


def test_major_reject_number_is_inclusive():
    out = run(defects=[defect(1, "major"), defect(2, "major")])
    assert out["outcome"] == "REJECT"
    assert out["counts"]["major"] == 2


def test_minor_defects_below_reject_number_accept():
    out = run(defects=[defect(1, "minor"), defect(2, "minor")])
    assert out["outcome"] == "ACCEPT"
    assert out["counts"]["minor"] == 2


def test_critical_nonvisual_failure_rejects_even_when_sample_incomplete():
    u = units()
    u[0]["views"][0] = view(None, preds=[])
    out = run(lot={"lot_size": 480, "critical_nonvisual_status": "failed"},
              units_=u, present=8)
    assert out["outcome"] == "REJECT"
    assert out["primary_reason"] == "REJECT_CRITICAL_NONVISUAL_FAILED"


def test_no_reject_while_sample_is_incomplete():
    u = units()
    u[0]["views"][0] = view(None)
    out = run(units_=u, defects=[defect(1, "critical")])
    assert out["outcome"] == "HOLD"
    assert "REJECT_LIMIT_REACHED" not in out["reasons"]
    assert "HOLD_VIEWS_PENDING" in out["reasons"]


# ----------------------------------------------------------------- escalates
def test_open_critical_proposal_escalates():
    u = units()
    u[0]["views"][0]["predictions"] = [
        {"id": 1, "provisional_critical": True, "review_state": "proposed"}
    ]
    out = run(units_=u)
    assert out["outcome"] == "ESCALATE"
    assert out["primary_reason"] == "ESCALATE_CRITICAL_UNREVIEWED"


def test_unmapped_clause_escalates():
    out = run(defects=[defect(1, None)])
    assert out["outcome"] == "ESCALATE"
    assert out["primary_reason"] == "ESCALATE_UNMAPPED_CLAUSE"


def test_rejected_critical_needs_second_review():
    u = units()
    u[0]["views"][0]["predictions"] = [
        {"id": 1, "provisional_critical": True, "review_state": "rejected",
         "second_review": "pending"}
    ]
    out = run(units_=u)
    assert out["outcome"] == "ESCALATE"
    assert out["primary_reason"] == "ESCALATE_CRITICAL_REJECTION_UNCONFIRMED"


def test_second_opinion_request_escalates():
    u = units()
    u[0]["views"][0]["predictions"] = [
        {"id": 1, "provisional_critical": False, "review_state": "confirmed",
         "second_opinion": True}
    ]
    out = run(units_=u)
    assert out["outcome"] == "ESCALATE"
    assert out["primary_reason"] == "ESCALATE_SECOND_OPINION_REQUESTED"


# --------------------------------------------------------------------- holds
def test_missing_units_holds():
    out = run(present=5)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_UNITS_MISSING"


def test_retake_holds():
    u = units()
    u[2]["views"][1] = view("needs_retake")
    out = run(units_=u)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_VIEWS_PENDING"


def test_missing_required_photo_holds():
    u = units()
    u[1]["views"][0] = view(None, image=False)
    out = run(units_=u)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_VIEWS_PENDING"


def test_critical_nonvisual_pending_holds():
    out = run(lot={"lot_size": 480, "critical_nonvisual_status": "pending"})
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_CRITICAL_NONVISUAL_PENDING"


def test_state_contradiction_holds():
    u = units()
    u[0]["views"][0]["predictions"] = [
        {"id": 1, "provisional_critical": False, "review_state": "confirmed"}
    ]
    out = run(units_=u)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_VIEW_STATE_INCONSISTENT"


def test_evidence_integrity_failure_holds():
    u = units()
    u[3]["views"][0]["evidence_ok"] = False
    out = run(units_=u)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_EVIDENCE_INTEGRITY"


def test_compute_error_holds():
    out = run(compute_error="inference worker timeout")
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_COMPUTE_ERROR"


def test_plan_missing_beats_everything():
    out = run(plan=None, lot={"critical_nonvisual_status": "failed"},
              defects=[defect(1, "critical")], present=0)
    assert out["outcome"] == "HOLD"
    assert out["reasons"] == ["HOLD_PLAN_MISSING"]


# ------------------------------------------------------- plan validation, Re=Ac+1
@pytest.mark.parametrize("field", ["critical", "major", "minor"])
def test_re_must_equal_ac_plus_one(field):
    plan = copy.deepcopy(PLAN)
    plan[field]["re"] = plan[field]["ac"] + 2
    out = run(plan=plan)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_PLAN_INVALID"
    assert any(field in e for e in out["completeness"]["plan_errors"])


@pytest.mark.parametrize("mutate", [
    {"n": 0},
    {"n": "8"},
    {"counting_mode": "best_guess"},
    {"major": {"ac": -1, "re": 0}},
    {"minor": {"ac": 2}},
])
def test_invalid_plans_hold(mutate):
    plan = copy.deepcopy(PLAN)
    plan.update(mutate)
    out = run(plan=plan)
    assert out["outcome"] == "HOLD"
    assert out["primary_reason"] == "HOLD_PLAN_INVALID"


# --------------------------------------------------------------- counting modes
def test_highest_class_only_counts_a_garment_once():
    """One garment with a major and a minor is one major garment, not two."""
    out = run(defects=[defect(1, "minor", defect_id=1), defect(1, "major", defect_id=2)])
    assert out["counts"] == {"critical": 0, "major": 1, "minor": 0}
    # major Ac is 1, so a single major garment is still at acceptance
    assert out["outcome"] == "ACCEPT"
    assert out["class_status"]["major"]["at_acceptance"] is True


def test_every_class_mode_counts_each_class_per_garment():
    plan = copy.deepcopy(PLAN)
    plan["counting_mode"] = "every_class"
    out = run(plan=plan, defects=[
        defect(1, "major", defect_id=1),
        defect(1, "minor", defect_id=2),
    ])
    # the same garment now counts once in major and once in minor
    assert out["counts"] == {"critical": 0, "major": 1, "minor": 1}
    assert out["outcome"] == "ACCEPT"
    out2 = run(plan=plan, defects=[
        defect(1, "major", defect_id=1),
        defect(1, "minor", defect_id=2),
        defect(2, "minor", defect_id=3),
        defect(3, "minor", defect_id=4),
    ])
    assert out2["counts"]["minor"] == 3
    assert out2["outcome"] == "REJECT"


def test_retracted_or_stale_defects_never_count():
    out = run(defects=[
        defect(1, "critical", retracted=True),
        defect(2, "critical", current_image=False),
        defect(3, "critical", view_reviewed=False),
    ])
    assert out["counts"]["critical"] == 0
    assert out["outcome"] == "ACCEPT"


# ------------------------------------------------------------ precedence & purity
def test_escalate_beats_hold():
    u = units()
    u[0]["views"][0]["predictions"] = [
        {"id": 1, "provisional_critical": True, "review_state": "proposed"}
    ]
    out = run(units_=u, present=4)
    assert out["outcome"] == "ESCALATE"
    assert "HOLD_UNITS_MISSING" in out["reasons"]
    assert out["reasons"].index("ESCALATE_CRITICAL_UNREVIEWED") < \
        out["reasons"].index("HOLD_UNITS_MISSING")


def test_reject_beats_escalate():
    out = run(defects=[defect(1, "critical"), defect(2, None)])
    assert out["outcome"] == "REJECT"
    assert "ESCALATE_UNMAPPED_CLAUSE" in out["reasons"]


def test_decision_is_deterministic():
    a = run(defects=[defect(1, "critical")])
    b = run(defects=[defect(1, "critical")])
    assert a == b
    assert a["engine_version"] == engine.ENGINE_VERSION


def test_engine_imports_only_the_standard_library():
    import ast

    tree = ast.parse(inspect.getsource(engine))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "hashlib", "json"}, imported


def test_snapshot_hash_is_stable_and_order_insensitive():
    rows = [{"unit_id": 2, "defect_id": 7, "severity": "major"},
            {"unit_id": 1, "defect_id": 3, "severity": "critical"}]
    assert engine.snapshot_hash(rows) == engine.snapshot_hash(list(reversed(rows)))
    assert engine.snapshot_hash(rows) != engine.snapshot_hash(rows[:1])


def test_reason_codes_have_a_declared_outcome():
    for code, (outcome, text) in engine.REASONS.items():
        assert outcome in ("ACCEPT", "REJECT", "HOLD", "ESCALATE")
        assert text
    assert len(engine.REASONS) == 15
