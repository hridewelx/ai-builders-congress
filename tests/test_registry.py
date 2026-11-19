"""The registry is append-only and hash-based; it must not invent a file."""
from __future__ import annotations

from ml import registry


def test_entry_records_hashes_and_missing_files(tmp_path):
    present = tmp_path / "model.onnx"
    present.write_bytes(b"weights")
    missing = tmp_path / "absent.pt"
    record = registry.entry("test", {"onnx": present, "checkpoint": missing})
    assert record["model"] == registry.MODEL_NAME
    assert record["artifacts"]["onnx"]["sha256"]
    assert record["artifacts"]["checkpoint"]["sha256"] is None
    assert record["note"] == "test"


def test_append_is_append_only(tmp_path):
    path = tmp_path / "registry.jsonl"
    registry.append({"version": "v1"}, path)
    registry.append({"version": "v2"}, path)
    entries = registry.history(path)
    assert [entry["version"] for entry in entries] == ["v1", "v2"]
    assert registry.latest(path)["version"] == "v2"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_history_of_a_missing_registry_is_empty(tmp_path):
    assert registry.history(tmp_path / "nope.jsonl") == []
    assert registry.latest(tmp_path / "nope.jsonl") is None


def test_pipeline_records_only_after_success(tmp_path, monkeypatch):
    from ml import pipeline

    class Ok:
        returncode = 0

    calls: list[str] = []
    state = tmp_path / "state.json"
    pipeline.run("data", state_path=state, eval_path=tmp_path / "none.json",
                 runner=lambda *a, **k: Ok(), on_success=calls.append)
    assert calls == ["data"]

    class Bad:
        returncode = 1

    with_error = tmp_path / "state2.json"

    def boom(*args, **kwargs):
        return Bad()

    import pytest

    with pytest.raises(SystemExit):
        pipeline.run("data", state_path=with_error, eval_path=tmp_path / "none.json",
                     runner=boom, on_success=calls.append)
    assert calls == ["data"], "a failed stage must not be recorded as a model version"
