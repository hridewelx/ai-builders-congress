"""The one schema. Applied on start-up by app.core.db.init()."""
from __future__ import annotations

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS organization (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id INTEGER NOT NULL REFERENCES organization(id),
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','inspector','supervisor')),
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  must_change INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_session (
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES app_user(id),
  verifier_hash TEXT NOT NULL,
  csrf TEXT NOT NULL,
  created_at REAL NOT NULL,
  last_seen REAL NOT NULL,
  absolute_expiry REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempt (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_key TEXT NOT NULL,
  at REAL NOT NULL,
  ok INTEGER NOT NULL,
  ip TEXT
);

CREATE TABLE IF NOT EXISTS buyer (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id INTEGER NOT NULL REFERENCES organization(id),
  name TEXT NOT NULL,
  country TEXT
);

CREATE TABLE IF NOT EXISTS clause_mapping (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buyer_id INTEGER NOT NULL REFERENCES buyer(id),
  defect_type TEXT NOT NULL,
  zone_code TEXT NOT NULL,
  size_band TEXT,
  severity TEXT NOT NULL CHECK (severity IN ('critical','major','minor')),
  clause_ref TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id INTEGER NOT NULL REFERENCES organization(id),
  name TEXT NOT NULL,
  family TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id INTEGER NOT NULL REFERENCES organization(id),
  lot_code TEXT NOT NULL UNIQUE,
  product_id INTEGER NOT NULL REFERENCES product(id),
  buyer_id INTEGER NOT NULL REFERENCES buyer(id),
  color TEXT,
  lot_size INTEGER NOT NULL CHECK (lot_size >= 1),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','decided','reopened','archived')),
  critical_nonvisual_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (critical_nonvisual_status IN ('pending','done','not_required','failed')),
  nonvisual_note TEXT,
  selection_method TEXT NOT NULL DEFAULT 'self-declared random',
  created_by INTEGER NOT NULL REFERENCES app_user(id),
  created_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS plan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER NOT NULL REFERENCES lot(id),
  version INTEGER NOT NULL,
  n INTEGER NOT NULL CHECK (n >= 1),
  counting_mode TEXT NOT NULL CHECK (counting_mode IN ('highest_class_only','every_class')),
  critical_aql REAL,
  critical_ac INTEGER NOT NULL CHECK (critical_ac >= 0),
  critical_re INTEGER NOT NULL CHECK (critical_re >= 0),
  major_aql REAL,
  major_ac INTEGER NOT NULL CHECK (major_ac >= 0),
  major_re INTEGER NOT NULL CHECK (major_re >= 0),
  minor_aql REAL,
  minor_ac INTEGER NOT NULL CHECK (minor_ac >= 0),
  minor_re INTEGER NOT NULL CHECK (minor_re >= 0),
  inspection_level TEXT NOT NULL DEFAULT 'II',
  sampling_type TEXT NOT NULL DEFAULT 'single',
  source_edition TEXT,
  source_reference TEXT,
  is_demo INTEGER NOT NULL DEFAULT 0,
  entered_by INTEGER NOT NULL REFERENCES app_user(id),
  created_at TEXT NOT NULL,
  UNIQUE (lot_id, version)
);

CREATE TABLE IF NOT EXISTS sample_unit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER NOT NULL REFERENCES lot(id),
  garment_code TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (lot_id, garment_code)
);

CREATE TABLE IF NOT EXISTS unit_view (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sample_unit_id INTEGER NOT NULL REFERENCES sample_unit(id),
  side TEXT NOT NULL CHECK (side IN ('front','back','detail')),
  required INTEGER NOT NULL DEFAULT 1,
  UNIQUE (sample_unit_id, side)
);

CREATE TABLE IF NOT EXISTS image (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER NOT NULL REFERENCES lot(id),
  view_id INTEGER NOT NULL REFERENCES unit_view(id),
  stored_name TEXT NOT NULL,
  original_name TEXT,
  sha256_original TEXT NOT NULL,
  sha256_working TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  bytes INTEGER NOT NULL,
  is_current INTEGER NOT NULL DEFAULT 1,
  purged INTEGER NOT NULL DEFAULT 0,
  uploaded_by INTEGER NOT NULL REFERENCES app_user(id),
  cloudinary_url TEXT,
  cloudinary_public_id TEXT,
  captured_at TEXT,
  inspection_id INTEGER,
  inspector_id INTEGER,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inference_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id INTEGER NOT NULL REFERENCES image(id),
  status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed','canceled')),
  model_version TEXT,
  error TEXT,
  latency_ms INTEGER,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS prediction (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL REFERENCES inference_job(id),
  image_id INTEGER NOT NULL REFERENCES image(id),
  defect_type TEXT NOT NULL,
  score REAL NOT NULL,
  x1 REAL NOT NULL, y1 REAL NOT NULL, x2 REAL NOT NULL, y2 REAL NOT NULL,
  review_state TEXT NOT NULL DEFAULT 'proposed'
    CHECK (review_state IN ('proposed','confirmed','rejected')),
  confirmed_type TEXT,
  zone_code TEXT,
  size_band TEXT,
  severity TEXT,
  clause_ref TEXT,
  provisional_critical INTEGER NOT NULL DEFAULT 0,
  second_review TEXT,
  note TEXT,
  reviewed_by INTEGER REFERENCES app_user(id),
  reviewed_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS view_review (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id INTEGER NOT NULL REFERENCES image(id) UNIQUE,
  state TEXT NOT NULL CHECK (state IN ('confirmed_defects','reviewed_clean','needs_retake')),
  note TEXT,
  reviewed_by INTEGER NOT NULL REFERENCES app_user(id),
  reviewed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decision (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER NOT NULL REFERENCES lot(id),
  sequence INTEGER NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('ACCEPT','REJECT','HOLD','ESCALATE')),
  primary_reason TEXT NOT NULL,
  reasons TEXT NOT NULL,
  counts TEXT NOT NULL,
  class_limits TEXT NOT NULL,
  plan_snapshot TEXT,
  snapshot_hash TEXT NOT NULL,
  completeness TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  manual_inspection INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  created_by INTEGER NOT NULL REFERENCES app_user(id),
  created_at TEXT NOT NULL,
  supersedes_id INTEGER,
  UNIQUE (lot_id, sequence)
);

CREATE TABLE IF NOT EXISTS override (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  decision_id INTEGER NOT NULL REFERENCES decision(id) UNIQUE,
  supervisor_id INTEGER NOT NULL REFERENCES app_user(id),
  final_disposition TEXT NOT NULL CHECK (final_disposition IN ('OVERRIDE_ACCEPT','OVERRIDE_REJECT')),
  reason TEXT NOT NULL CHECK (length(reason) >= 20),
  status TEXT NOT NULL CHECK (status IN ('effective','pending_approval')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS override_approval (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  override_id INTEGER NOT NULL REFERENCES override(id) UNIQUE,
  approver_id INTEGER NOT NULL REFERENCES app_user(id),
  decision TEXT NOT NULL CHECK (decision IN ('approved','refused')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  actor_id INTEGER,
  actor_label TEXT NOT NULL,
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id TEXT,
  before_json TEXT,
  after_json TEXT,
  ip TEXT
);

CREATE TABLE IF NOT EXISTS model_version (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  artifact_sha TEXT NOT NULL,
  classes TEXT NOT NULL,
  eval_note TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_selftest (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_name TEXT NOT NULL,
  passed INTEGER NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_activation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_name TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('activate','rollback')),
  actor TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""
