"""Lotline demo database: SQLite, append-only history, one schema.

Faithful to SYSTEM_DESIGN_v1_2 at demo scale. Every state change that can
affect a decision writes an audit row. Decisions and overrides are append-only.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid

from ..config import DATA_DIR, DB_PATH, STORE_DIR  # noqa: F401  (re-exported)
from .schema import SCHEMA  # noqa: F401  (kept as db.SCHEMA)

_local = threading.local()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def connect() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(STORE_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init() -> None:
    conn = connect()
    conn.executescript(SCHEMA)


def q(sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    return list(connect().execute(sql, args))


def one(sql: str, args: tuple = ()):
    rows = q(sql, args)
    return rows[0] if rows else None


def x(sql: str, args: tuple = ()) -> int:
    cur = connect().execute(sql, args)
    return cur.lastrowid if cur.lastrowid is not None else cur.rowcount


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
