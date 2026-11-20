"""Lotline demo database: SQLite, append-only history, one schema.

Faithful to SYSTEM_DESIGN_v1_2 at demo scale. Every state change that can
affect a decision writes an audit row. Decisions and overrides are append-only.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid

from ..config import DATA_DIR, DB_PATH, STORE_DIR  # noqa: F401  (re-exported)
from .schema import SCHEMA  # noqa: F401  (kept as db.SCHEMA)

_local = threading.local()
DATABASE_URL = os.environ.get("LOTLINE_DATABASE_URL", "").strip()


def dialect() -> str:
    """``postgres`` when a DSN is configured, otherwise the demo's SQLite file."""
    return "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"


def translate_sql(sql: str) -> str:
    """SQLite's ``?`` placeholders become psycopg's ``%s``."""
    if dialect() != "postgres":
        return sql
    return re.sub(r"\?", "%s", sql)


def postgres_schema() -> str:
    """The same constraints as the SQLite schema, in Postgres spelling."""
    schema = re.sub(r"PRAGMA[^;]+;", "", SCHEMA)
    return schema.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def connect():
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(STORE_DIR, exist_ok=True)
        if dialect() == "postgres":
            conn = _connect_postgres()
        else:
            conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def _connect_postgres():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - exercised only with a DSN set
        raise RuntimeError(
            "LOTLINE_DATABASE_URL is set but psycopg is not installed; "
            "pip install -r requirements-postgres.txt") from exc
    return psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)


def init() -> None:
    conn = connect()
    if dialect() == "postgres":
        for statement in postgres_schema().split(";"):
            if statement.strip():
                conn.execute(statement)
        return
    conn.executescript(SCHEMA)


def q(sql: str, args: tuple = ()) -> list:
    conn = connect()
    if dialect() == "postgres":
        return list(conn.execute(translate_sql(sql), args).fetchall())
    return list(conn.execute(sql, args))


def one(sql: str, args: tuple = ()):
    rows = q(sql, args)
    return rows[0] if rows else None


def x(sql: str, args: tuple = ()) -> int:
    conn = connect()
    if dialect() == "postgres":
        statement = translate_sql(sql).rstrip().rstrip(";")
        if statement.lstrip().upper().startswith("INSERT"):
            row = conn.execute(statement + " RETURNING id", args).fetchone()
            return int(row["id"]) if row and "id" in row else 0
        cursor = conn.execute(statement, args)
        return int(cursor.rowcount)
    cur = conn.execute(sql, args)
    return cur.lastrowid if cur.lastrowid is not None else cur.rowcount


def reset_sequences() -> None:
    """Restart identity values after a demo reset, on either dialect."""
    conn = connect()
    if dialect() != "postgres":
        conn.execute("DELETE FROM sqlite_sequence")
        return
    tables = [row["tablename"] for row in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()]
    for table in tables:
        sequence = conn.execute(
            "SELECT pg_get_serial_sequence(%s, 'id') AS name", (table,)).fetchone()["name"]
        if sequence:
            conn.execute(f"ALTER SEQUENCE {sequence} RESTART WITH 1")


def audit(actor_id, actor_label: str, action: str, entity: str, entity_id=None,
          before=None, after=None, ip: str | None = None) -> None:
    x(
        "INSERT INTO audit_event(at,actor_id,actor_label,action,entity,entity_id,before_json,after_json,ip)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (now(), actor_id, actor_label, action, entity, str(entity_id) if entity_id is not None else None,
         json.dumps(before, ensure_ascii=False) if before is not None else None,
         json.dumps(after, ensure_ascii=False) if after is not None else None, ip),
    )


def new_id() -> str:
    return uuid.uuid4().hex
