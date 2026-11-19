"""Remove duplicate images without ever merging a test image into train."""
from __future__ import annotations

from .records import Record, dhash, hamming


def dedupe(records: list[Record]) -> tuple[list[Record], int]:
    """Drop exact and near-duplicate images, recording what was dropped."""
    kept: list[Record] = []
    seen_sha: dict[str, Record] = {}
    hashes: list[tuple[str, Record]] = []
    dropped = 0
    for record in records:
        record.sha256 = sha256_file(record.path)
        if record.sha256 in seen_sha:
            seen_sha[record.sha256].duplicates.append(str(record.path))
            dropped += 1
            continue
        record.phash = dhash(record.path)
        near = next((other for h, other in hashes
                     if hamming(h, record.phash) <= 2 and pixel_mae(other.path, record.path) <= 1.5), None)
        if near is not None:
            near.duplicates.append(str(record.path))
            dropped += 1
            continue
        seen_sha[record.sha256] = record
        hashes.append((record.phash, record))
        record.group = record.phash
        kept.append(record)
    return kept, dropped


def dedupe_preserving_test(records: list[Record]) -> tuple[list[Record], int]:
    """Dedupe within splits and drop train/val copies of test images.

    Test records are deduped first. Any train/val image that is an exact or
    near-duplicate of a test image is then dropped. That keeps the official
    test split isolated instead of letting dedupe absorb it into training.
    """
    test_records = [record for record in records if record.split == "test"]
    other_records = [record for record in records if record.split != "test"]
    test_kept, test_dropped = dedupe(test_records)
    other_kept, other_dropped = dedupe(other_records)

    test_sha = {record.sha256 for record in test_kept}
    test_hashes = [(record.phash, record) for record in test_kept]
    kept_other: list[Record] = []
    cross_dropped = 0
    for record in other_kept:
        duplicate = record.sha256 in test_sha
        if not duplicate:
            duplicate = any(
                hamming(record.phash, phash) <= 2 and pixel_mae(record.path, other.path) <= 1.5
                for phash, other in test_hashes)
        if duplicate:
            cross_dropped += 1
            continue
        kept_other.append(record)
    return test_kept + kept_other, test_dropped + other_dropped + cross_dropped
