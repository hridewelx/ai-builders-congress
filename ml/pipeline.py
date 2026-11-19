"""Run the model pipeline in order, and make the test split hard to score twice.

The expensive stages are easy to run by hand and easy to run in the wrong order:
evaluating before exporting, or re-scoring the held-out test split until a number
looks good. That second mistake is how a measurement becomes a fit, and it is not
visible in any single script. So the order and the "test is scored once" rule live
here, in one place, as state on disk.

    python -m ml.pipeline status
    python -m ml.pipeline plan
    python -m ml.pipeline run data
    python -m ml.pipeline run eval            # refuses if the test split was scored
    python -m ml.pipeline run eval --force    # a second measurement, recorded as such

State lives in `data/models/pipeline_state.json`. There is no network and no
database; a deleted state file is the only way to lose the record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MODELS = Path("data/models")
STATE_FILE = MODELS / "pipeline_state.json"
TEST_SPLIT_LOCK = "eval_test"
EVAL_RESULT = MODELS / "eval_test_v2.json"

STAGES: dict[str, dict] = {
    "data": {
        "about": "build det_v2 and verify the official test folder was never trained on",
        "steps": [["-m", "ml.data", "prepare"], ["-m", "ml.verify_split"]],
        "outputs": ["data/dataset/det_v2", "docs/split_integrity.json"],
    },
    "train": {
        "about": "train the detector; checkpoints are chosen on validation only",
        "steps": [["-m", "ml.train", "--data", "data/dataset/det_v2", "--epochs", "12",
                   "--lr", "0.0015", "--size", "640", "--batch", "4", "--workers", "0",
                   "--out", "data/models/det_v2b.pt"]],
        "outputs": ["data/models/det_v2b.pt"],
    },
    "operating_point": {
        "about": "choose the review threshold on validation, never on test",
        "steps": [["-m", "ml.operating_point"]],
        "outputs": ["data/models/operating_point_v2.json"],
    },
    "eval": {
        "about": "score the held-out test split exactly once",
        "steps": [["-m", "ml.evaluate", "--split", "test",
                   "--out", "data/models/eval_test_v2.json"]],
        "outputs": ["data/models/eval_test_v2.json"],
    },
    "calibrate": {
        "about": "fit temperature on validation; the result may be rejected",
        "steps": [["-m", "ml.calibrate"]],
        "outputs": ["data/models/calibration_v2.json"],
    },
    "export": {
        "about": "export ONNX from the same checkpoint and verify parity",
        "steps": [["-m", "ml.export_onnx"], ["-m", "ml.verify_runtime", "--split", "val"]],
        "outputs": ["data/models/det_v2.onnx", "data/models/runtime_parity_v2.json"],
    },
    "package": {
        "about": "zip the artifacts with a manifest a host can verify",
        "steps": [["scripts/package_model.py"]],
        "outputs": ["dist/lotline-det-v2.zip"],
    },
}
ORDER = list(STAGES)


def load_state(path: Path = STATE_FILE) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"runs": []}


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def has_scored_test(state: dict, eval_path: Path = EVAL_RESULT) -> bool:
    """True if this pipeline scored the test split, or a test result already exists on disk.

    The second half matters: the current checkpoint was scored before this file
    existed, so the lock cannot depend on the state file alone.
    """
    if any(run.get("lock") == TEST_SPLIT_LOCK and run.get("ok") for run in state["runs"]):
        return True
    try:
        saved = json.loads(eval_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return saved.get("split") == "test"


def guard(stage: str, state: dict, force: bool = False, eval_path: Path = EVAL_RESULT) -> None:
    """Refuse a second test-scoring run unless the operator says it is deliberate."""
    if stage == "eval" and has_scored_test(state, eval_path) and not force:
        raise SystemExit(
            "the held-out test split was already scored (see `python -m ml.pipeline status`).\n"
            "Re-scoring it turns a measurement into a fit. If this is a deliberate new\n"
            "measurement, pass --force; the extra run is recorded with force=true.")


def plan(stage: str | None = None) -> list[dict]:
    names = [stage] if stage else ORDER
    return [{"stage": name, "about": STAGES[name]["about"],
             "commands": ["python " + " ".join(step) for step in STAGES[name]["steps"]],
             "outputs": STAGES[name]["outputs"]} for name in names]


def _sha(path: Path) -> str | None:
    if path.is_dir():
        return None
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def run(stage: str, force: bool = False, state_path: Path = STATE_FILE,
        eval_path: Path = EVAL_RESULT, runner=subprocess.run,
        on_success=None) -> dict:
    """Execute one stage's commands in order and record what happened."""
    state = load_state(state_path)
    guard(stage, state, force, eval_path)
    record = {"stage": stage, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "ok": False, "force": bool(force),
              "lock": TEST_SPLIT_LOCK if stage == "eval" else None, "commands": []}
    for step in STAGES[stage]["steps"]:
        command = [sys.executable, *step]
        completed = runner(command, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        record["commands"].append({"command": " ".join(command), "returncode": completed.returncode})
        if completed.returncode != 0:
            record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            state["runs"].append(record)
            save_state(state, state_path)
            raise SystemExit(f"stage {stage!r} failed: {' '.join(command)}")
    record["outputs"] = {path: _sha(Path(path)) for path in STAGES[stage]["outputs"]}
    record["ok"] = True
    record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state["runs"].append(record)
    save_state(state, state_path)
    if on_success is not None:
        on_success(stage)
    return record


def status(state: dict, eval_path: Path = EVAL_RESULT) -> list[str]:
    done: dict[str, dict] = {}
    for item in state["runs"]:
        if item.get("ok"):
            done[item["stage"]] = item
    lines = []
    for name in ORDER:
        mark = "done" if name in done else "not run"
        when = done[name]["finished"] if name in done else ""
        lines.append(f"{name:<16} {mark:<8} {when}")
    if has_scored_test(state, eval_path):
        lines.append("test split: already scored (eval is locked; --force records an extra run)")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the model pipeline in order.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("plan")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("stage", choices=ORDER)
    run_parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "status":
        print("\n".join(status(load_state())))
        return 0
    if args.command == "plan":
        print(json.dumps(plan(), indent=2))
        return 0
    from . import registry

    record = run(args.stage, force=args.force,
                 on_success=lambda name: registry.record(f"pipeline stage: {name}"))
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
