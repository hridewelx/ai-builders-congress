# Lotline — master prompt (single-prompt challenge entry)

This is the one prompt that reproduces the build. Paste the whole file into a
coding agent with an empty repository, then run the acceptance checks at the end.
It is written the way the product is built: constraint first, then evidence,
then screens, then the honest limits.

---

## Prompt

Build **Lotline**, a runnable knitwear lot-acceptance system, in one repository.
It must run locally with `python -m uvicorn app.main:app --port 8077` after
`pip install -r requirements.txt` and `python -m app.seed`. No Docker, no GPU,
no network calls at runtime.

### 1. The invariant (non-negotiable)

**AI proposes defects. A human confirms them. A deterministic rule decides.**

- `app/domain/engine.py` must be a pure function: only `hashlib` and `json` may be
  imported. It receives a plan, lot evidence, units with views, and
  human-confirmed defects. It returns an outcome, counts, class status,
  completeness, and an ordered list of reason codes.
- Proposals are never counted. Only defects with `review_state='confirmed'` on a
  reviewed, current image from a reviewed view are eligible.
- Every failure path ends in `HOLD`, `ESCALATE` or `REJECT`. The only ACCEPT
  reason is `ACCEPT_PLAN_MET`, and it requires a complete sample with zero
  reject numbers reached.
- Provide a test that parses the engine's AST and fails if it imports anything
  beyond `__future__`, `hashlib`, `json`.

### 2. Decision rules

Precedence, first match wins:
`plan → REJECT → ESCALATE → other HOLD → ACCEPT`.

Reason codes (canonical, stable strings):
`HOLD_PLAN_MISSING`, `HOLD_PLAN_INVALID`,
`REJECT_CRITICAL_NONVISUAL_FAILED`, `REJECT_LIMIT_REACHED`,
`ESCALATE_CRITICAL_UNREVIEWED`, `ESCALATE_UNMAPPED_CLAUSE`,
`ESCALATE_CRITICAL_REJECTION_UNCONFIRMED`, `ESCALATE_SECOND_OPINION_REQUESTED`,
`HOLD_UNITS_MISSING`, `HOLD_VIEWS_PENDING`, `HOLD_CRITICAL_NONVISUAL_PENDING`,
`HOLD_VIEW_STATE_INCONSISTENT`, `HOLD_EVIDENCE_INTEGRITY`,
`HOLD_COMPUTE_ERROR`, `ACCEPT_PLAN_MET`.

Plan validation: `n ≥ 1`; `counting_mode ∈ {highest_class_only, every_class}`;
each class needs integer `ac ≥ 0` and `re = ac + 1` (single sampling, version 1).
Reject a class when `count ≥ re`; `count == ac` is still acceptance.

Counting: `highest_class_only` counts a garment once in its highest class;
`every_class` counts it once in every class it has. Retracted defects, defects on
a replaced image, and defects on an unreviewed view never count.

Completeness gates: units present vs required, required views without a review,
`needs_retake`, a `reviewed_clean` view that still has confirmed predictions,
missing/altered evidence files, a pending critical non-visual check, an
unanswered critical proposal, a rejected critical proposal awaiting a second
review, a requested second opinion, and a compute error.

### 3. Data model (SQLite, WAL, foreign keys on)

Tables: `organization, app_user, user_session, login_attempt, buyer,
clause_mapping, product, lot, plan, sample_unit, unit_view, image,
inference_job, prediction, view_review, decision, override, override_approval,
audit_event, model_version, model_selftest, model_activation`.

- `decision` and `override` are append-only; each decision stores the plan
  snapshot, counts, class status, completeness, engine version and a SHA-256
  snapshot hash. Never update a decision row.
- `audit_event` is written for every state change (who, what, entity, before,
  after, timestamp).
- Views per garment: `front`, `back`, `detail`. Review states:
  `confirmed_defects`, `reviewed_clean`, `needs_retake`. Prediction states:
  `proposed`, `confirmed`, `rejected`. Lot states: `open`, `decided`,
  `reopened`, `archived`.

### 4. Vision

Implement a real, small, honest detector in `app/services/vision.py` using numpy + Pillow:
an unsupervised autoencoder trained only on synthetic **clean** knit patches
(procedural texture), scored by per-patch reconstruction residual, with robust
z-scoring (median/MAD), connected components, IoU dedupe, and top-k boxes.
Return proposals with `type`, `score`, `box`, plus a heat map image and quality
flags, `calibrated: False`.

Generate staged photos procedurally: a garment panel in a colour, optional
defects (hole, oil stain, dropped stitch, skipped stitch, needle line), and
normalised truth boxes for evaluation. Provide `selftest()` and
`evaluate_staged()`; the UI must show the evaluation domain as
"staged synthetic panels only" and the scores as uncalibrated.

Defect-type classification may be heuristic; the reviewer can change the type
before confirming. A failed inference must never block manual review.

### 5. Web app

FastAPI + Jinja2, server-rendered, phone-first, dark design system.
Bangla and English as first-class locales (language toggle in the header).

Login: email + password, Argon2id, server-side sessions (30 min idle / 8 h
absolute), HttpOnly + SameSite=Lax cookie, CSRF double-submit on every POST,
Origin check, progressive login delay per account+IP, password policy ≥ 15
characters with context-word rejection. One-click demo login buttons
(`/demo/inspector`, `/demo/supervisor`, `/demo/admin`) enabled only when
`LOTLINE_DEMO=1`.

Roles: `admin`, `inspector`, `supervisor` (one per user, enforced server-side).
Admin manages accounts, model activation, audit, and can never view evidence or
override a decision. Inspector captures and reviews. Supervisor sets the plan,
computes decisions, second-reviews rejected criticals, and overrides.

Screens: dashboard, lots list, new lot, lot overview, sampling plan (with
read-back of exactly what will be stored), capture, review queue, review
workspace (image, boxes, attention map, per-proposal confirm/edit/reject, add a
missed defect by clicking the photo, close view), decision (outcome band, counts
table with Ac/Re, reasons, completeness, append-only history, recompute),
report (HTML + one-page PDF), audit (filter + CSV), admin (users, model versions,
system health, buyer clauses), how-it-works.

Hardening: 15 MB upload cap, magic-byte check, 50 MP cap, EXIF transpose,
SHA-256 dedupe, filesystem fsync; uploads run inference synchronously.

### 6. Overrides

Only a supervisor may override, and only an ACCEPT or REJECT. Override to ACCEPT
requires approval by a **second, different supervisor**. Admin cannot override.
Overrides append rows; the final disposition is shown as overridden everywhere
and printed on the report.

### 7. Seed data (staged, clearly fake)

One organisation, three roles (four users), one product, two buyers — one with a
complete clause map, one deliberately missing an oil-stain zone — and six lots
that cover five distinct outcomes:

| lot | state |
|---|---|
| LT-2026-014 | REJECT_LIMIT_REACHED (confirmed critical, plus AI proposals humans rejected) |
| LT-2026-015 | ACCEPT_PLAN_MET |
| LT-2026-016 | HOLD_UNITS_MISSING (5 of 8 garments) |
| LT-2026-017 | ESCALATE_UNMAPPED_CLAUSE |
| LT-2026-018 | HOLD_PLAN_MISSING |
| LT-2026-019 | ESCALATE_CRITICAL_UNREVIEWED (open lot for the live demo) |

Demo password `QualityFloor2026!`. Seed must be idempotent with `--force`
(rebuild) and must not require network access.

### 8. Report

One page: outcome band, override banner if any, entered plan with Ac/Re and
source reference, confirmed counts, canonical reason codes with plain-language
text, evidence and gates, snapshot hash, signature lines, and a short honest
disclaimer: no reconstructed AQL table, no percentage allowance, no calibration
claim, staged images only. Support a Unicode-capable TTF for Bangla; fall back to
Helvetica rather than crashing.

### 9. Acceptance checks

```bash
python -m pytest -q                 # engine: 30+ tests, all reason codes,
                                    # precedence, Re=Ac+1, counting modes, purity
python -m app.seed --force          # 6 lots, ~70 photos, decisions, audit trail
python -m uvicorn app.main:app --port 8077
```

Then, in a browser:

1. `/login` → Inspector one-click → dashboard shows six lots and no AI approvals.
2. Open LT-2026-019 → decision is `ESCALATE_CRITICAL_UNREVIEWED`.
3. Review the flagged view → confirm the hole (zone II), reject the second
   proposal, close the view.
4. As supervisor, recompute → `REJECT_LIMIT_REACHED`.
5. Open the report → PDF downloads and matches the screen.
6. As inspector, attempt an override → refused. As supervisor, override to
   ACCEPT → pending; approve as a different supervisor → final disposition
   ACCEPT (overridden).
7. As admin, open `/images/1` → 403.
8. Toggle বাংলা → every screen and the PDF still work.
9. `curl -I /healthz` → 200.

### 10. Do not

- Do not let the model produce a count, severity, or outcome.
- Do not auto-confirm a proposal, and do not let an unanswered proposal be
  closed silently.
- Do not invent ISO 2859-1 values or claim certification, calibration, accuracy,
  or time savings that are not measured.
- Do not store worker names, faces, or real buyer data.
- Do not present staged images as factory evidence.

---

## Expected output

A repository with `app/` (`domain/engine.py`, `core/db.py`, `core/security.py`,
`services/{vision,review,report,seed}.py`, `web/{pages,deps,routes}`, `main.py`),
`templates/`, `static/`, `tests/`, `scripts/build_dataset.py`, `ml/`, `README.md`,
`PITCH.md`, `DEPLOY.md`, a Dockerfile, and seed data. The engine must be readable in one
sitting: that is the point of the product.
