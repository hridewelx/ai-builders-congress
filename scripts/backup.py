"""Back up the database and the evidence store, and prove the evidence is intact.

The audit story depends on the stored photo keeping the hash that was recorded
when it was uploaded. A backup that silently copies a corrupted store is worse
than no backup, so this script hashes every stored file and compares it with
`image.sha256_working` before it claims success.

    python scripts/backup.py --out /backups/lotline-2026-11-19
    python scripts/backup.py --verify-only          # no copy, just the check

Layout of a backup: `lotline.db` (a consistent copy taken through SQLite's
backup API, not a raw file copy), `store/` (byte copies), and `manifest.json`
with the per-file hashes and the verification counts.

Restore: stop the app, copy `lotline.db` and `store/` back into `$LOTLINE_DATA`,
start the app, then run `--verify-only` against the restored directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_rows(db_path: Path) -> list[dict]:
    """Current, unpurged images with the hash recorded at upload time."""
    if not db_path.exists():
        raise SystemExit(f"no database at {db_path}")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT id, stored_name, sha256_working FROM image "
            "WHERE is_current=1 AND purged=0 ORDER BY id").fetchall()
    finally:
        con.close()
    return [dict(row) for row in rows]


def verify(db_path: Path, store_dir: Path) -> dict:
    """Compare every stored file with its recorded hash. Never raises on a bad file."""
    problems: list[dict] = []
    checked = 0
    rows = evidence_rows(db_path)
    for row in rows:
        path = store_dir / row["stored_name"]
        if not path.exists():
            problems.append({"id": row["id"], "file": row["stored_name"], "problem": "missing"})
            continue
        checked += 1
        actual = sha256(path)
        if actual != row["sha256_working"]:
            problems.append({"id": row["id"], "file": row["stored_name"],
                             "problem": "hash mismatch", "expected": row["sha256_working"],
                             "actual": actual})
    return {"images": len(rows), "checked": checked, "problems": problems,
            "ok": not problems}


def copy_database(src: Path, dest: Path) -> None:
    """Copy through SQLite so a WAL database is copied consistently."""
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def backup(data_dir: Path, out_dir: Path) -> dict:
    db_path = data_dir / "lotline.db"
    store_dir = data_dir / "store"
    report = verify(db_path, store_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_database(db_path, out_dir / "lotline.db")
    files: dict[str, str] = {}
    if store_dir.exists():
        for path in sorted(store_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(store_dir)
            target = out_dir / "store" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            files[str(relative).replace("\\", "/")] = sha256(target)
    manifest = {"source": str(data_dir), "db_sha256": sha256(out_dir / "lotline.db"),
                "store_files": len(files), "evidence": report, "files": files}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def default_data_dir() -> Path:
    return Path(os.environ.get("LOTLINE_DATA", BASE_DIR / "data"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up and verify the evidence store.")
    parser.add_argument("--data", type=Path, default=default_data_dir())
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_only:
        report = verify(args.data / "lotline.db", args.data / "store")
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1

    if not args.out:
        parser.error("--out is required unless --verify-only is used")
    manifest = backup(args.data, args.out)
    report = manifest["evidence"]
    print(f"{report['checked']}/{report['images']} stored images hashed, "
          f"{manifest['store_files']} files copied -> {args.out}")
    if report["problems"]:
        print(json.dumps(report["problems"], indent=2))
        print("backup written, but the evidence store does not match its hashes")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
