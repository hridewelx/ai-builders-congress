"""The test split is scored once; the pipeline is what enforces it."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml import pipeline


class FakeCompleted:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


def _state_with_eval(tmp_path: Path) -> Path:
    state_path = tmp_path / "state.json"
    state = {"runs": [{"stage": "eval", "ok": True, "lock": "eval_test",
                       "finished": "2026-11-19T10:00:00+00:00", "outputs": {}}]}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def test_plan_covers_every_stage_in_order():
    names = [item["stage"] for item in pipeline.plan()]
    assert names == pipeline.ORDER
    assert names.index("eval") > names.index("train")
    assert names.index("export") > names.index("eval")


def test_second_test_scoring_is_refused(tmp_path):
    state_path = _state_with_eval(tmp_path)
    with pytest.raises(SystemExit, match="already scored"):
        pipeline.run("eval", state_path=state_path, runner=lambda *a, **k: FakeCompleted())


def test_force_records_a_deliberate_second_run(tmp_path):
    state_path = _state_with_eval(tmp_path)
    record = pipeline.run("eval", force=True, state_path=state_path,
                          runner=lambda *a, **k: FakeCompleted())
    assert record["ok"] and record["force"] is True
    state = pipeline.load_state(state_path)
    assert len(state["runs"]) == 2
    assert pipeline.has_scored_test(state)


def test_failed_step_is_recorded_and_stops_the_stage(tmp_path):
    state_path = tmp_path / "state.json"
    with pytest.raises(SystemExit, match="failed"):
        pipeline.run("data", state_path=state_path, runner=lambda *a, **k: FakeCompleted(2))
    state = pipeline.load_state(state_path)
    assert state["runs"][0]["ok"] is False
    assert state["runs"][0]["commands"][0]["returncode"] == 2


def test_status_reports_unrun_stages(tmp_path):
    lines = pipeline.status(pipeline.load_state(tmp_path / "missing.json"),
                            tmp_path / "no-eval.json")
    assert len(lines) == len(pipeline.ORDER)
    assert all("not run" in line for line in lines)


def test_saved_test_result_locks_eval_without_any_state(tmp_path):
    """The current checkpoint was scored before the state file existed."""
    eval_path = tmp_path / "eval_test_v2.json"
    eval_path.write_text(json.dumps({"split": "test", "map50": 0.9474}), encoding="utf-8")
    state_path = tmp_path / "state.json"
    with pytest.raises(SystemExit, match="already scored"):
        pipeline.run("eval", state_path=state_path, eval_path=eval_path,
                     runner=lambda *a, **k: FakeCompleted())
    lines = pipeline.status(pipeline.load_state(state_path), eval_path)
    assert any("already scored" in line for line in lines)
