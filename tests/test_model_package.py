"""Packaging and fetching must fail closed.

A model package is downloaded by a host and then executed. These tests cover the
two rules that matter: the zip checksum is checked before anything is written,
and a member name that tries to escape the destination is refused.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))
import fetch_model  # noqa: E402
import package_model  # noqa: E402


def _make_package(tmp_path: Path) -> tuple[Path, str]:
    files = {}
    for name in ("det_v2.onnx", "calibration_v2.json", "operating_point_v2.json"):
        path = tmp_path / name
        path.write_bytes(f"content of {name}".encode())
        files[name] = path
    card = tmp_path / "MODEL_CARD.md"
    card.write_text("# card\n", encoding="utf-8")
    files["MODEL_CARD.md"] = card
    out = tmp_path / "pkg.zip"
    manifest = package_model.package(out, files)
    return out, manifest["zip_sha256"]


def test_package_refuses_to_ship_missing_artifacts(tmp_path):
    with pytest.raises(SystemExit, match="missing artefacts"):
        package_model.package(tmp_path / "bad.zip",
                               {"det_v2.onnx": tmp_path / "nope.onnx"})


def test_fetch_installs_matching_package(tmp_path):
    archive, digest = _make_package(tmp_path)
    dest = tmp_path / "installed"
    written = fetch_model.install(archive.read_bytes(), digest, dest)
    assert {path.name for path in written} == {
        "det_v2.onnx", "calibration_v2.json", "operating_point_v2.json", "MODEL_CARD.md"}
    assert (dest / "calibration_v2.json").exists()


def test_fetch_refuses_wrong_checksum(tmp_path):
    archive, _ = _make_package(tmp_path)
    with pytest.raises(SystemExit, match="checksum mismatch"):
        fetch_model.install(archive.read_bytes(), "0" * 64, tmp_path / "installed")


def test_fetch_refuses_path_traversal(tmp_path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"files": {"../escape.onnx": {"sha256": "x"}}}))
        zf.writestr("../escape.onnx", b"payload")
    import hashlib

    digest = hashlib.sha256(evil.read_bytes()).hexdigest()
    with pytest.raises(SystemExit, match="unsafe member name"):
        fetch_model.install(evil.read_bytes(), digest, tmp_path / "installed")
    assert not (tmp_path / "escape.onnx").exists()


def test_fetch_refuses_member_hash_mismatch(tmp_path):
    archive, _ = _make_package(tmp_path)
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(broken, "w") as dst:
        for item in src.infolist():
            payload = src.read(item.filename)
            if item.filename == "calibration_v2.json":
                payload = b"tampered"
            dst.writestr(item.filename, payload)
    import hashlib

    digest = hashlib.sha256(broken.read_bytes()).hexdigest()
    with pytest.raises(SystemExit, match="does not match the manifest hash"):
        fetch_model.install(broken.read_bytes(), digest, tmp_path / "installed")
