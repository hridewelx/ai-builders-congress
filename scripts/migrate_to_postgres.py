"""Copy a seeded SQLite demo into Postgres for a pilot deployment.

    pip install -r requirements-postgres.txt
    LOTLINE_DATABASE_URL=postgresql://... python scripts/migrate_to_postgres.py \
        --source data/lotline.db

IDs are preserved so audit links and evidence hashes keep pointing at the same
rows. The target schema is the one the application itself creates; the script
refuses to copy into a non-empty target unless ``--force`` is given.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core import db as app_db  # noqa: E402

# Parents before children, because every table has foreign keys.
ORDER = [
    "organization", "app_user", "buyer", "clause_mapping", "product", "lot", "plan",
    "sample_unit", "unit_view", "image", "inference_job", "prediction", "view_review",
    "decision", "override", "override_approval", "audit_event", "model_version",
    "model_selftest", "model_activation", "user_session", "login_attempt",
]


def source_tables(path: Path) -> list[str]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        present = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    finally:
        con.close()
    return [table for table in ORDER if table in present]


def copy(source: Path, target_url: str, force: bool) -> dict[str, int]:
    os.environ["LOTLINE_DATABASE_URL"] = target_url
    app_db.DATABASE_URL = target_url
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit("install requirements-postgres.txt first") from exc

    target = psycopg.connect(target_url, autocommit=True, row_factory=dict_row)
    try:
        app_db.init()
        if not force:
            occupied = target.execute(
                "SELECT COUNT(*) AS n FROM lot").fetchone()["n"]
            if occupied:
                raise SystemExit(f"target already has {occupied} lot(s); pass --force to append")

        sqlite = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        sqlite.row_factory = sqlite3.Row
        copied: dict[str, int] = {}
        try:
            for table in source_tables(source):
                rows = sqlite.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
                if not rows:
                    copied[table] = 0
                    continue
                columns = list(rows[0].keys())
                placeholders = ",".join(["%s"] * len(columns))
                statement = (f"INSERT INTO {table}({','.join(columns)}) VALUES ({placeholders})"
                             " ON CONFLICT (id) DO NOTHING")
                with target.cursor() as cursor:
                    cursor.executemany(statement, [[row[column] for column in columns]
                                                   for row in rows])
                copied[table] = len(rows)
        finally:
            sqlite.close()

        # SERIAL sequences do not advance when ids are inserted explicitly.
        for table in copied:
            sequence = target.execute(
                "SELECT pg_get_serial_sequence(%s, 'id') AS name", (table,)).fetchone()["name"]
            if not sequence:
                continue
            target.execute(
                "SELECT setval(%s, COALESCE((SELECT MAX(id) FROM " + table + "), 1),"
                " (SELECT COUNT(*) > 0 FROM " + table + "))", (sequence,))
        return copied
    finally:
        target.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=BASE_DIR / "data" / "lotline.db")
    parser.add_argument("--target", default=os.environ.get("LOTLINE_DATABASE_URL", ""),
                        help="postgresql:// DSN (defaults to LOTLINE_DATABASE_URL)")
    parser.add_argument("--force", action="store_true", help="append even when the target has lots")
    args = parser.parse_args(argv)
    if not args.target:
        parser.error("--target or LOTLINE_DATABASE_URL is required")
    if not args.source.exists():
        parser.error(f"no SQLite database at {args.source}")
    copied = copy(args.source, args.target, args.force)
    print(f"{sum(copied.values())} row(s) copied across {len(copied)} table(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
