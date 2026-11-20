"""Import consented factory photos as their own domain, and refuse everything else.

BDFD9 is one domain: four factories, one capture habit. A second factory is the
only way to learn whether the detector travels, and photos from it may only be
used if the factory said yes in writing. So this importer is deliberately
suspicious:

- a photo with no consent row is refused, not imported with a warning;
- a photo that duplicates something already in `det_v2` is refused, so training
  data cannot leak into a new domain by copy;
- duplicates inside the batch are refused too (same bytes, or a near-identical
  perceptual hash);
- the consent file's own hash is recorded, so the manifest proves what was agreed.

Layout expected in the photo folder:

    consent.csv          file,consent_date,consent_by,factory,notes
    annotations.jsonl    {"file": "...", "split": "train", "defects": [{"type": "hole", "box": [x1,y1,x2,y2]}]}
    *.jpg

`defects` uses normalised boxes like the staged set; `ml.data.read_jsonl` reads it.

    python -m ml.import_consented --photos data/raw/ext_a --consent data/raw/ext_a/consent.csv \
        --out data/dataset/ext_v1 --domain external_factory_a --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import date
from pathlib import Path

from .config import CLASSES, DATA, DET
from .data import Record, dhash, export, hamming, read_jsonl, sha256_file

CONSENT_COLUMNS = ("file", "consent_date", "consent_by", "factory")
NEAR_DUPLICATE_BITS = 6


def read_consent(path: Path) -> dict[str, dict]:
    """Parse the consent file. A row without a signature or a date is not consent."""
    if not path.exists():
        raise SystemExit(f"no consent file at {path}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [name for name in CONSENT_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"consent file is missing columns: {', '.join(missing)}")
        granted: dict[str, dict] = {}
        for line, row in enumerate(reader, start=2):
            name = (row.get("file") or "").strip()
            if not name:
                continue
            by = (row.get("consent_by") or "").strip()
            when = (row.get("consent_date") or "").strip()
            if not by or not when:
                raise SystemExit(f"line {line}: {name} has no consent_by or consent_date")
            try:
                date.fromisoformat(when)
            except ValueError:
                raise SystemExit(f"line {line}: consent_date {when!r} is not YYYY-MM-DD") from None
            granted[Path(name).name] = {"consent_by": by, "consent_date": when,
                                        "factory": (row.get("factory") or "").strip(),
                                        "notes": (row.get("notes") or "").strip()}
    if not granted:
        raise SystemExit("consent file lists no photos")
    return granted


def reference_index(dataset_root: Path) -> tuple[set[str], list[str]]:
    """Hashes of every image already in the training dataset, to refuse copies."""
    hashes: set[str] = set()
    phashes: list[str] = []
    if not dataset_root.exists():
        return hashes, phashes
    for path in sorted(dataset_root.rglob("images/**/*")):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            hashes.add(sha256_file(path))
            try:
                phashes.append(dhash(path))
            except OSError:
                continue
    return hashes, phashes


def screen(records: list[Record], consent: dict[str, dict],
           known_sha: set[str], known_phash: list[str]) -> tuple[list[Record], list[dict]]:
    """Accept only photos that are consented, new, and distinct from each other."""
    accepted: list[Record] = []
    refused: list[dict] = []
    seen_sha: set[str] = set()
    seen_phash: list[tuple[str, str]] = []
    for record in records:
        name = record.path.name
        row = consent.get(name)
        if row is None:
            refused.append({"file": name, "reason": "no consent row"})
            continue
        digest = sha256_file(record.path)
        if digest in known_sha:
            refused.append({"file": name, "reason": "identical to an image already in det_v2"})
            continue
        if digest in seen_sha:
            refused.append({"file": name, "reason": "duplicate inside this batch"})
            continue
        phash = dhash(record.path)
        twin = next((other for other, bits in seen_phash if hamming(phash, bits) <= NEAR_DUPLICATE_BITS), None)
        if twin:
            refused.append({"file": name, "reason": f"near-duplicate of {twin} in this batch"})
            continue
        for existing in known_phash:
            if hamming(phash, existing) <= NEAR_DUPLICATE_BITS:
                refused.append({"file": name, "reason": "near-duplicate of an image already in det_v2"})
                break
        else:
            record.sha256 = digest
            record.phash = phash
            record.group = row.get("factory") or record.group
            seen_sha.add(digest)
            seen_phash.append((name, phash))
            accepted.append(record)
    return accepted, refused


def guard_target(out: Path, reference: Path, force: bool = False) -> None:
    """An import may replace a previous import of its own; it may never eat a dataset.

    ``--out data/dataset/det_v2`` used to delete the training set. A target is
    only overwritten when its manifest proves it is an earlier import.
    """
    target = out.resolve()
    for protected in (reference.resolve(), DET.resolve()):
        if target == protected or protected in target.parents:
            raise SystemExit(f"refusing to write into {out}: that is a training dataset, not an import")
    if not target.exists():
        return
    try:
        previous = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    looks_like_import = bool(previous.get("domain")) and bool(previous.get("consent_file"))
    if not looks_like_import and not force:
        raise SystemExit(
            f"refusing to delete {out}: it does not look like a previous consent import "
            "(no manifest with a domain and consent file). Pass --force if you are sure.")


def import_photos(photos: Path, consent_path: Path, out: Path, domain: str,
                  reference: Path | None = None, dry_run: bool = False,
                  force: bool = False) -> dict:
    consent = read_consent(consent_path)
    if not (photos / "annotations.jsonl").exists():
        raise SystemExit(f"no annotations.jsonl in {photos}; boxes are required, not optional")
    records = read_jsonl(photos, source=domain)
    known_sha, known_phash = reference_index(reference or (DATA / "dataset" / "det_v2"))
    accepted, refused = screen(records, consent, known_sha, known_phash)

    consent_faces = [{"file": name, **row} for name, row in sorted(consent.items())]
    meta = {
        "domain": domain,
        "consent_file": consent_path.name,
        "consent_file_sha256": sha256_file(consent_path),
        "consent_rows": len(consent_faces),
        "accepted": len(accepted),
        "refused": len(refused),
        "licence": "written consent on file; not redistributable without the factory's permission",
        "classes": CLASSES,
        "note": "Imported as its own domain. Never merged into det_v2 and never added to its test split.",
    }
    report = {"meta": meta, "refused": refused}
    if dry_run:
        report["dry_run"] = True
        return report

    if not accepted:
        raise SystemExit("nothing to import: every photo was refused")
    guard_target(out, reference or (DATA / "dataset" / "det_v2"), force)
    if out.exists():
        shutil.rmtree(out)
    manifest = export(accepted, out, meta, strip_metadata=True)
    (out / "consent.json").write_text(
        json.dumps({"granted": consent_faces, "refused": refused}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    report["manifest"] = manifest
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import consented photos as a separate domain.")
    parser.add_argument("--photos", type=Path, required=True)
    parser.add_argument("--consent", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DATA / "dataset" / "ext_v1")
    parser.add_argument("--domain", default="external_factory_a")
    parser.add_argument("--reference", type=Path, default=None,
                        help="dataset to check for copies (default: det_v2)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="overwrite a target folder that is not a previous import")
    args = parser.parse_args(argv)
    report = import_photos(args.photos, args.consent, args.out, args.domain,
                           reference=args.reference, dry_run=args.dry_run, force=args.force)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["refused"]:
        print(f"{report['refused'].__len__()} photo(s) refused — see the report above")
    return 0


if __name__ == "__main__":
    sys.exit(main())
