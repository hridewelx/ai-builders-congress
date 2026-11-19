"""A backup must prove the evidence still matches its hashes."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
import backup  # noqa: E402


def _make_data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "store").mkdir(parents=True)
    con = sqlite3.connect(data / "lotline.db")
    con.execute("CREATE TABLE image (id INTEGER PRIMARY KEY, stored_name TEXT, "
                "sha256_working TEXT, is_current INTEGER, purged INTEGER)")
    good = b"good evidence bytes"
    bad = b"evidence that was edited later"
    (data / "store" / "good.jpg").write_bytes(good)
    (data / "store" / "bad.jpg").write_bytes(bad)
    con.executemany("INSERT INTO image VALUES (?,?,?,1,0)", [
        (1, "good.jpg", hashlib.sha256(good).hexdigest()),
        (2, "bad.jpg", hashlib.sha256(b"the original bytes").hexdigest()),
        (3, "gone.jpg", hashlib.sha256(b"never stored").hexdigest()),
    ])
    con.commit()
    con.close()
    return data


def test_verify_reports_missing_and_mismatched_files(tmp_path):
    data = _make_data_dir(tmp_path)
    report = backup.verify(data / "lotline.db", data / "store")
    assert report["images"] == 3
    assert report["checked"] == 2
    assert report["ok"] is False
    problems = {item["id"]: item["problem"] for item in report["problems"]}
    assert problems == {2: "hash mismatch", 3: "missing"}


def test_backup_copies_db_and_store_and_writes_manifest(tmp_path):
    data = _make_data_dir(tmp_path)
    out = tmp_path / "backup"
    manifest = backup.backup(data, out)
    assert (out / "lotline.db").exists()
    assert (out / "store" / "good.jpg").read_bytes() == b"good evidence bytes"
    assert manifest["store_files"] == 2  # every stored file is copied, good or bad
    saved = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert saved["evidence"]["ok"] is False
    copied_hash = hashlib.sha256((out / "store" / "good.jpg").read_bytes()).hexdigest()
    assert saved["files"]["good.jpg"] == copied_hash


def test_verify_only_exits_non_zero_on_corruption(tmp_path, capsys):
    data = _make_data_dir(tmp_path)
    code = backup.main(["--data", str(data), "--verify-only"])
    assert code == 1
    assert "hash mismatch" in capsys.readouterr().out


def test_backup_succeeds_on_a_clean_store(tmp_path):
    data = _make_data_dir(tmp_path)
    (data / "store" / "bad.jpg").write_bytes(b"the original bytes")
    (data / "store" / "gone.jpg").write_bytes(b"never stored")
    out = tmp_path / "clean-backup"
    assert backup.main(["--data", str(data), "--out", str(out)]) == 0
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["evidence"]["ok"] is True
