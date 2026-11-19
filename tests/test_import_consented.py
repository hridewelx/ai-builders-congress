"""A consented import must refuse unconsented and duplicate photos."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ml import import_consented as imp
from ml.data import Record, dhash, sha256_file


def _photo(path: Path, seed: int = 1) -> None:
    """A patterned image: flat colours collide on dHash and are not realistic."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 255, (96, 96, 3), dtype=np.uint8)
    pixels[::8, :, :] = 255
    pixels[:, ::5, :] = 0
    Image.fromarray(pixels).save(path, quality=95)


def _annotations(root: Path, rows: list[dict]) -> None:
    (root / "annotations.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def _consent(root: Path, rows: list[str]) -> Path:
    path = root / "consent.csv"
    path.write_text("file,consent_date,consent_by,factory,notes\n" + "\n".join(rows), encoding="utf-8")
    return path


def test_photo_without_consent_is_refused(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg", 1)
    _photo(photos / "b.jpg", 2)
    _annotations(photos, [
        {"file": "a.jpg", "split": "train", "seed": 1, "defects": [{"type": "hole", "box": [0.1, 0.1, 0.3, 0.3]}]},
        {"file": "b.jpg", "split": "train", "seed": 1, "defects": []},
    ])
    consent = _consent(photos, ["a.jpg,2026-11-19,Quality Manager,Factory A,verbal consent recorded"])
    report = imp.import_photos(photos, consent, tmp_path / "out", "external_a",
                               reference=tmp_path / "empty", dry_run=True)
    assert report["meta"]["accepted"] == 1
    assert report["refused"] == [{"file": "b.jpg", "reason": "no consent row"}]


def test_duplicate_inside_batch_is_refused(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg", 3)
    (photos / "a_copy.jpg").write_bytes((photos / "a.jpg").read_bytes())
    _annotations(photos, [
        {"file": "a.jpg", "split": "train", "seed": 1, "defects": []},
        {"file": "a_copy.jpg", "split": "train", "seed": 1, "defects": []},
    ])
    consent = _consent(photos, ["a.jpg,2026-11-19,QM,Factory A,",
                                "a_copy.jpg,2026-11-19,QM,Factory A,"])
    report = imp.import_photos(photos, consent, tmp_path / "out", "external_a",
                               reference=tmp_path / "empty", dry_run=True)
    assert report["meta"]["accepted"] == 1
    assert report["refused"][0]["reason"] == "duplicate inside this batch"


def test_copy_of_a_training_image_is_refused(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg", 4)
    _annotations(photos, [{"file": "a.jpg", "split": "train", "seed": 1, "defects": []}])
    consent = _consent(photos, ["a.jpg,2026-11-19,QM,Factory A,"])
    reference = tmp_path / "det_v2"
    _photo(reference / "images" / "train" / "bdfd9_00000.jpg", 4)
    report = imp.import_photos(photos, consent, tmp_path / "out", "external_a",
                               reference=reference, dry_run=True)
    assert report["meta"]["accepted"] == 0
    assert "already in det_v2" in report["refused"][0]["reason"]


def test_real_import_writes_domain_and_consent_manifest(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg", 5)
    _photo(photos / "b.jpg", 6)
    _annotations(photos, [
        {"file": "a.jpg", "split": "train", "seed": 1, "defects": [{"type": "hole", "box": [0.2, 0.2, 0.4, 0.4]}]},
        {"file": "b.jpg", "split": "train", "seed": 1, "defects": [{"type": "oil_stain", "box": [0.5, 0.5, 0.7, 0.7]}]},
    ])
    consent = _consent(photos, ["a.jpg,2026-11-19,QM,Factory A,",
                                "b.jpg,2026-11-19,QM,Factory A,"])
    out = tmp_path / "ext_v1"
    report = imp.import_photos(photos, consent, out, "external_factory_a",
                               reference=tmp_path / "empty")
    assert report["manifest"]["domain"] == "external_factory_a"
    assert report["manifest"]["splits"]["train"] == 2
    assert (out / "manifest.json").exists()
    saved = json.loads((out / "consent.json").read_text(encoding="utf-8"))
    assert len(saved["granted"]) == 2
    assert saved["granted"][0]["consent_by"] == "QM"
    assert (out / "data.yaml").exists()


def test_consent_file_without_signature_is_rejected(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg")
    _annotations(photos, [{"file": "a.jpg", "split": "train", "seed": 1, "defects": []}])
    consent = _consent(photos, ["a.jpg,2026-11-19,,"])
    with pytest.raises(SystemExit, match="no consent_by or consent_date"):
        imp.import_photos(photos, consent, tmp_path / "out", "external_a", dry_run=True)


def test_missing_consent_file_is_rejected(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg")
    _annotations(photos, [{"file": "a.jpg", "split": "train", "seed": 1, "defects": []}])
    with pytest.raises(SystemExit, match="no consent file"):
        imp.import_photos(photos, tmp_path / "missing.csv", tmp_path / "out", "external_a")


def test_screen_sets_hashes_and_factory_group(tmp_path):
    photos = tmp_path / "photos"
    _photo(photos / "a.jpg")
    record = Record(path=photos / "a.jpg", boxes=[], source="external_a")
    accepted, refused = imp.screen([record], {"a.jpg": {"consent_by": "QM", "consent_date": "2026-11-19",
                                                       "factory": "Factory A", "notes": ""}},
                                   set(), [])
    assert not refused
    assert accepted[0].sha256 == sha256_file(photos / "a.jpg")
    assert accepted[0].phash == dhash(photos / "a.jpg")
    assert accepted[0].group == "Factory A"
