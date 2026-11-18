# Lotline — Phase 0 Recon Report

**Date:** 18 November 2026
**Repo:** `D:\ai-builders-congress`
**Instruction:** `LOTLINE_BUILD.md` (found at the repo root; the file says it should live at `docs/LOTLINE_BUILD.md`)
**Mode:** Phase 0 only — no application code changed, no server started, no data generated.
**Status:** STOPPED AT CHECKPOINT A.

---

## 1. Pre-flight fields

| Field | Finding |
|---|---|
| Repo path | `D:\ai-builders-congress` |
| Sources of truth | Actual paths are `docs/spec/PRD_v0_3.md`, `docs/spec/SYSTEM_DESIGN_v1_2.md`, `docs/spec/security-v0_4.md`. The build prompt's paths (`docs/PRD_v0_3.md`, etc.) do not exist. `docs/SYSTEM_DESIGN.md` is superseded v1.0. |
| Backend status | **Implemented but not currently runnable in this environment.** FastAPI is not installed in the current Python 3.11.9 interpreter; server `127.0.0.1:8077` refuses connections. Startup path: `pip install -r requirements.txt` → `python -m app.seed` → `python -m uvicorn app.main:app --host 127.0.0.1 --port 8077`. |
| Detector status | **No trained detector checkpoint in the repo.** Default is `ae-knit-v1`, an unsupervised numpy autoencoder trained at first run on synthetic clean knit patches. The optional Faster R-CNN ONNX path requires `data/models/det_v1.onnx` + `onnxruntime`; neither exists/installed. `ml/README.md`'s mAP figures describe the separate ML workstream, **not** the shipped default. All current demo proposals must be labelled **"Illustrative, not model output"**, not "Recorded result". |
| Existing frontend stack | Jinja2 server-rendered templates, one hand-written CSS file, one small vanilla-JS file. **No React, Vite, Tailwind, shadcn/ui, TypeScript, npm build, or JSON API client.** |
| OpenAPI / endpoint list | None. FastAPI docs are disabled (`docs_url=None`, `redoc_url=None`). Endpoints are HTML form posts + redirects; there is no `/api/v1`. |
| Sample real detection response | Not available without starting the backend and generating data. Source contract is documented in §7; it is not a live capture. |
| Demo setup | Laptop/projector assumed; phone for Inspector flow assumed. Not stated by owner. |
| Demo date/time | **Unknown.** Total build hours: **unknown.** |
| Frontend deps | Node 22.19.0 / npm 10.9.3 available for dev tooling; Playwright CLI 1.65.1 available. No package.json exists. |

**Build-prompt rule applied:** backend and detector status are not empty, so Phase 0 proceeds to this report, but both need owner confirmation at Checkpoint A.

---

## 2. Executive summary

1. **The repo is a working server-rendered demo, not the React app the build prompt assumes.** There is no JSON API to build against. A React SPA would require either a new backend API (forbidden by the scope guardrails) or a fully mocked frontend (dishonest for the P0 flow). **Recommendation: redesign in place with Jinja2 + CSS + vanilla JS, preserving every route and the backend.**
2. **The P0 flow already exists end to end** — login, lot detail, capture/upload, review/confirm, plan, compute, override, second-supervisor approval, PDF. Much of Phase 2 is visual/UX redesign, not new capability.
3. **The shipped detector is an unsupervised numpy baseline on staged synthetic images.** No trained checkpoint is committed. The UI must say "Illustrative, not model output" and "staged synthetic photo", never imply a trained model or real factory evidence.
4. **The backend lacks a number of P0/P1 fields and routes the prompt requires** — change-password, image withdraw, detail-side creation, per-image quality flags, decision-time model versions/clauses, reviewer-is-overrider, single-supervisor flag, server-side 409/429/request IDs, product/buyer writes, clear-login-counters. Under "do not modify the backend", these must be hidden or explicitly explained, not mocked.
5. **Security v0.4 cannot be fully satisfied by frontend-only work**: session cookie is `ll_session` (not `__Host-`), CSRF is also placed in a readable cookie, login is a form post (not JSON + custom header), and there is no CSP/request-ID middleware. The redesign can reduce exposure (stop reading the CSRF cookie, add a meta CSP), but cannot fix the server contract.

---

## 3. Stack and architecture

```
Browser
  └─ Jinja2 HTML (templates/*.html)
       ├─ /static/app.css        one global stylesheet
       ├─ /static/app.js         box/heat/manual-box interactions
       └─ form POST + 303 redirect (no fetch/JSON client)
FastAPI app factory (app/main.py)
  ├─ routes: auth, dashboard, lots, capture, review, decisions, reports, admin, system
  ├─ services: review (evidence/decisions/overrides/progress), vision, detector, report, seed
  ├─ domain: engine.py (pure deterministic decision function)
  └─ core: db.py (SQLite WAL), security.py (Argon2id, sessions, CSRF)
```

- **Database:** SQLite at `data/lotline.db` (created at runtime), schema in `app/core/db.py`.
- **Session:** server-side `user_session` row; cookie is `ll_session` containing `sid.verifier`; idle 30 min / absolute 8 h.
- **CSRF:** per-session token, checked as a form field `csrf` plus Origin/Host comparison. The token is also written to a non-HttpOnly `ll_csrf` cookie, which the current JS does not need.
- **Uploads:** streamed, 15 MB / 50 MP limit, JPEG/PNG signature check, EXIF transpose, server working copy resized to max 1600 px, SHA-256 recorded, duplicate rejected, inference runs **synchronously** inside the upload request.
- **Legacy shims:** `app/db.py`, `app/engine.py`, etc. re-export the new modules; no UI impact.

---

## 4. Existing screens to preserve

| Route | Template | Current capability |
|---|---|---|
| `GET /login` | `login.html` | Branded split login, Inspector/Supervisor/Admin one-click demo buttons, error banner, Bangla toggle |
| `GET /` | `dashboard.html` | Counters, first 6 lot cards, model self-test state, demo stats |
| `GET /lots` | `lots.html` | Search `q`, state filter, outcome filter, lot cards |
| `GET /lots/new` | `lot_new.html` | Create lot (code, product, color, size, buyer) |
| `GET /lots/{id}` | `lot.html` | KPIs, units/views grid, decision summary, history timeline |
| `GET /lots/{id}/plan` | `plan.html` | Plan form, validation, read-only for non-supervisors, locked state |
| `GET /lots/{id}/capture` | `capture.html` | Unit list, per-view upload, add unit, progress, manual-review guidance |
| `GET /lots/{id}/review` | `review_queue.html` | Queue sorted by priority (critical, failed, proposals) |
| `GET /review/{img}` | `review.html` | Image viewer, box overlay, confirm/reject, add defect, zone/size band, second opinion, finish image |
| `GET /lots/{id}/decision` | `decision.html` | Recommendation, class table, reasons, completeness, override panel, approval, history |
| `GET /lots/{id}/report` | `report.html` | HTML report preview + PDF download/print |
| `GET /audit` | `audit.html` | Audit rows, free-text filter, before/after, CSV export for Admin |
| `GET /admin` | `admin.html` | Users, models/self-test/activation, health, read-only clause list |
| `GET /how` | `how.html` | Explainer page with stats |
| Error | `error.html` | 403/404/etc. friendly page |

**Features that must not regress:** Bangla/English toggle, append-only decision history, recommendation vs final disposition on separate lines, override/approval flow, evidence snapshot hash, reason codes, plan assumption label, seed accounts, demo role access, print/PDF.

---

## 5. API endpoints: PRD §14 vs this backend

**Important:** no endpoint exists as specified. There is no `/api/v1`, no JSON login, no JSON decision response, no `GET /auth/me`. Status below means **functional server-rendered equivalent**:

- **FOUND** = a route performs the action (HTML/form).
- **PARTIAL** = a route exists but a required field/behavior is missing.
- **MISSING** = no route.

| PRD endpoint | Status | Existing route / note |
|---|---|---|
| `POST /auth/login` | FOUND | `POST /login`; generic failure, progressive delay. No JSON/CSRF header, no 30/min limiter. |
| `POST /auth/logout` | FOUND | `POST /logout` |
| `POST /auth/password` | **MISSING** | No change-password route or page, despite `must_change` column and `policy_errors()`. |
| `GET /auth/me` | **MISSING** | Session/user is injected server-side into every template. |
| `GET /users` | PARTIAL | `/admin?tab=users`; no JSON/filter/pagination. |
| `POST /users` | FOUND | `POST /admin/users` |
| `PATCH /users/{id}` | PARTIAL | `POST /admin/users/{id}` actions disable/enable/role; no name/email edit. |
| `POST /users/{id}/temporary-password` | FOUND | `action=reset`; password shown once in query string. |
| `POST /users/{id}/clear-login-counters` | **MISSING** | `security.clear_attempts()` exists, no route. |
| `GET/POST/PATCH /products` | PARTIAL | Read-only product list in create-lot/admin contexts; no write routes. |
| `GET/POST/PATCH /buyers` | PARTIAL | Read-only buyer list; no write routes. |
| `GET /buyers/{id}/clauses` | PARTIAL | Read-only clause table on `/admin?tab=clauses`; Admin only. |
| `POST /lots` | FOUND | `POST /lots/new` |
| `GET /lots`, `GET /lots/{id}` | FOUND | HTML pages. |
| `PATCH /lots/{id}` | **MISSING** | No edit-metadata route. |
| `POST /lots/{id}/archive` | **MISSING** | No archive route. |
| `GET /lots/{id}/plan` | FOUND | `GET /lots/{id}/plan` |
| `PUT /lots/{id}/plan` | PARTIAL | `POST /lots/{id}/plan`; no `confirmed_readback`, no version concurrency. |
| `GET /lots/{id}/units` | FOUND | Embedded in lot/capture pages; no JSON. |
| `POST /lots/{id}/units` | FOUND | `POST /lots/{id}/units`; auto-creates front/back only (no detail side). |
| `POST /lots/{id}/units/{unit_id}/images` | PARTIAL | `POST /lots/{lot}/views/{view}/upload`; side is implicit in the view, no `side` field. |
| `GET /images/{id}` | FOUND | Working copy; Admin denied. |
| `POST /images/{id}/withdraw` | **MISSING** | No route. |
| `POST /images/{id}/needs-retake` | PARTIAL | `POST /review/{img}/state` with `needs_retake`; not a separate image flag. |
| `POST /images/{id}/inference` | PARTIAL | `POST /images/{img}/infer`; **synchronous**, no queued state, no queue id. |
| `GET /images/{id}/predictions` | **MISSING** | Predictions embedded in review HTML; no JSON. |
| `POST /predictions/{id}/confirm` | FOUND | `POST /review/{img}/confirm` |
| `POST /predictions/{id}/reject` | FOUND | `POST /review/{img}/reject` |
| `POST /units/{unit_id}/defects` | FOUND | `POST /review/{img}/add` (takes image id) |
| `PATCH /defects/{id}` | **MISSING** | Re-confirm can change a prediction; no standalone defect edit. |
| `POST /images/{id}/review` | FOUND | `POST /review/{img}/state` |
| `POST /lots/{id}/decisions` | FOUND | `POST /lots/{id}/decisions` |
| `GET /lots/{id}/decisions`, `GET /decisions/{id}` | PARTIAL | History embedded in decision page; no JSON. |
| `POST /decisions/{id}/override` | FOUND | `POST /decisions/{id}/override` |
| `POST /overrides/{id}/approval` | PARTIAL | `POST /overrides/{id}/approval`; no reason field, refused override stays `pending_approval`, no re-request. |
| `POST /decisions/{id}/report` | **MISSING** | PDF is built on GET. |
| `GET /decisions/{id}/report` | PARTIAL | `GET /lots/{id}/report.pdf`; **Admin is denied**, while PRD allows Admin view. |
| `GET /audit` | FOUND | `GET /audit`; only free-text `q`, 200-row cap, no pagination. |
| `POST /audit/export` | FOUND | `GET /audit.csv`; Admin only. |
| `GET /health` | FOUND | `/healthz`, `/readyz` |
| `GET /admin/alerts` | **MISSING** | No alerts data or route. |
| `GET /admin/models` | PARTIAL | Admin tab; no JSON. |

**Counts:** 20 FOUND, 14 PARTIAL, 10 MISSING (44 catalog rows). Zero JSON endpoints as specified.

**Extra existing routes (not in PRD):** `/demo/{role}` (demo login bypass), `/lang/{code}`, `/how`, `/healthz`, `/readyz`, `/audit.csv`.

---

## 6. Detection response shape (source contract, not a live sample)

`app/services/vision.detect()` and `app/services/detector.detect()` return:

```json
{
  "proposals": [
    {
      "type": "hole | oil_stain | needle_line | dropped_stitch",
      "score": 0.0,
      "box": [0.0, 0.0, 1.0, 1.0],
      "raw_error": null
    }
  ],
  "quality": {"blur_score": 0.0, "brightness": 0.0, "flags": ["BLUR", "DARK"]},
  "heat_png": "<bytes>",
  "model": "ae-knit-v1 | frcnn-mnv3-v1",
  "threshold": 0.0,
  "calibrated": false,
  "note": "uncalibrated research model; proposals require human confirmation"
}
```

- Boxes are **normalised 0–1** relative to the server working copy.
- `score` is **uncalibrated** on the default backend. The ONNX path can apply a temperature from `data/models/calibration.json`; no such file is committed.
- `quality.flags` is computed but **not persisted** by `capture.run_inference()` and **not passed to any template**. The review UI therefore cannot show BLUR/DARK/LOW_SCORE/UNKNOWN as server-returned flags.
- DB prediction row: `id, job_id, image_id, defect_type, score, x1..y2 (normalised), review_state, confirmed_type, zone_code, size_band, severity, clause_ref, provisional_critical, second_review, note, reviewed_by, reviewed_at`.
- `severity` and `clause_ref` are assigned by clause lookup at confirmation; `NULL` means `needs_clause` → ESCALATE.
- Working image is `image.stored_name` (server copy), never the original.

---

## 7. Roles and permission model

| Action | PRD | Implementation | Gap |
|---|---|---|---|
| Create lot | Inspector, Supervisor | `require_role("inspector","supervisor")` | none |
| Enter plan | Supervisor | Supervisor only | none |
| Capture/review/compute | Inspector own lot, Supervisor any | `can_write_lot()` + `ensure_write()` | none |
| Override | Supervisor only | Supervisor only | none |
| Approve high-risk | Different Supervisor | Server blocks self-approval | No single-supervisor flag/mode |
| Audit read | Supervisor, Admin | Supervisor/Admin | none |
| Audit export | Admin | Admin | none |
| Garment images | Inspector, Supervisor; Admin denied | Same | none |
| Report view | All roles (Admin view only) | Inspector/Supervisor; **Admin 403** | PRD mismatch |
| Product/buyer write | Admin, Supervisor | No routes | Both roles blocked |
| User management | Admin | Admin; last-admin/self-role guards | Missing clear-counters |
| Plan view | All read | All read | none |
| Decision view | All read | All read | none |
| Reopen/archive/edit lot | Supervisor | No routes | Missing |

The server is the authority. The new UI will hide controls a role cannot use and explain blocked actions, but must not pretend to enforce permissions.

---

## 8. Decision engine: exact inputs and outputs

**Pure function:** `app/domain/engine.decide(inp)`; imports only `hashlib` and `json` (AST-tested).

Input keys:

```
plan, lot, units[], defects[], units_present, required_units, compute_error
unit:   {id, views:[{side, required, has_image, review_state, evidence_ok,
                     live_job, inference_status,
                     predictions:[{id, provisional_critical, review_state,
                                   second_review, second_opinion,
                                   confirmed_severity}]}]}
defect: {defect_id, unit_id, severity, type, zone, size_band, image_id,
         current_image, view_reviewed, retracted}
```

Output:

```
{outcome, reasons[], primary_reason, counts{critical,major,minor},
 class_status{...}, plan, detail[], completeness{...},
 engine_version, counting_mode}
```

Precedence: `plan → REJECT → ESCALATE → HOLD → ACCEPT`.
15 canonical reason codes match PRD §9.4 exactly. `CALIBRATED_INTERVAL` is intentionally absent (inactive in v1).
`REJECT_LIMIT_REACHED` requires a complete sample; `REJECT_CRITICAL_NONVISUAL_FAILED` does not.
`ACCEPT` requires complete/reviewed/verified evidence and critical-nonvisual `done|not_required`.

**UI consequence:** counts, severity, high-risk, staleness and disposition must be read from these server values. The browser may render, label and link them; it must not recompute them.

---

## 9. Data available to each template (the hard boundary)

Because the backend is frozen, a screen can only show what its route already passes:

| Screen | Available context |
|---|---|
| Login | `csrf`, `lang`, `tr`, `err` |
| Dashboard | first 6 `cards` (incl. override), `counters`, `model`, `model_ok`, `stats` |
| Lots | `cards`, `state`, `outcome`, `q` |
| New lot | `buyers`, `products` |
| Lot detail | `lot`, `plan`, `plan_d`, `progress`, `units` (views/job/predictions), `decision`, `override`, `final`, `history`, `audit`, `is_admin`, `can_write` |
| Plan | `lot`, `plan`, `plan_d`, `is_supervisor`, `locked` |
| Capture | `lot`, `units`, `progress`, `can_write` |
| Review queue | `lot`, `queue` |
| Review | `lot`, `image`, `view`, `review`, `job`, `preds`, `clauses`, `status`, `next_item`, `can_write`, `is_supervisor` |
| Decision | `lot`, `plan`, parsed `decision`, `override`, `final`, `history`, `progress`, `is_supervisor`, `can_write`, `reason_text` |
| Report | `rc` (rich server report context), `lot` |
| Audit | `rows` (before/after parsed), `q`, `can_export` |
| Admin | `tab`, `users`, `models`, `tests`, `activations`, `clauses`, `health`, `card` |
| How | `card`, `stats` |

**Missing from decision context:** applicable buyer clauses, model versions, reviewer-is-overrider, active-supervisor count, per-prediction quality flags. These cannot be added without touching `app/web/routes/*.py`.

---

## 10. Document conflicts found

| # | Conflict | Consequence |
|---|---|---|
| C1 | Build prompt says `docs/LOTLINE_BUILD.md`, `docs/PRD_v0_3.md`, etc.; actual build file is at root and specs are `docs/spec/*`. | Move build file to `docs/` and use actual spec paths in PROGRESS/plan. |
| C2 | Build prompt's fallback stack is React/TS/Tailwind/shadcn; repo is Jinja/CSS/JS with no API. | Building React would require new backend endpoints (forbidden) or a fully mocked app. **In-place redesign recommended.** |
| C3 | Build prompt requires `__Host-` session cookie, CSRF in memory/custom header, JSON login, CSP, 429, request IDs; backend uses `ll_session`, form CSRF, readable `ll_csrf` cookie, no CSP/429/request ID. | Frontend can stop using the cookie and add a meta CSP, but cannot fix the server contract. List as limitations. |
| C4 | Build prompt requires first-login change-password; backend has `must_change` and `policy_errors()` but **no route/page**. | Cannot implement honestly. Hide/defer; needs owner decision. |
| C5 | Build prompt requires image withdraw, detail side, product/buyer writes, clear login counters; **no routes exist**. | Hide/defer; list as MISSING. |
| C6 | Build prompt requires per-image quality flags and decision-time clauses/model versions; **not passed/persisted**. | Omit or show only what exists; do not fabricate. |
| C7 | Build prompt says Admin can view reports; PRD matrix says Admin view only; implementation returns 403 for Admin. | Backend mismatch. Do not link Admin to report; note it. |
| C8 | PRD W-14 describes high-risk more broadly than FR-OVR-003; build prompt says log, don't resolve. | Open question; render server `pending_approval` state only. |
| C9 | Single-Supervisor mode: PRD S5 open; backend has no flag/notification. | Cannot show real HIGH RISK single-supervisor state. Seed has two supervisors, so flow works. |
| C10 | OV-10 (`REJECT_CRITICAL_NONVISUAL_FAILED` not overridable) is PROPOSED in PRD, but implemented in `decisions.py`. | UI may hide override for that reason (server data), but note status is proposed. |
| C11 | Shipped detector is numpy autoencoder; `ml/README.md` documents a trained Faster R-CNN (mAP 0.867), not shipped. | Label demo output "Illustrative, not model output". |
| C12 | README says staged images only; `docs/DATA.md` documents BDFD9 real photos. Seed uses staged synthetic images only. | Label "staged synthetic photo"; do not claim real factory data. |
| C13 | Build prompt says tagline only on login; current base rail/footer repeat it. | Remove from rail/footer in redesign. |
| C14 | Build prompt shell lists no "How it works"; existing app has it. | Preserve as a secondary help link, not primary nav (or owner decides). |
| C15 | Build prompt is English-only; existing UI is fully bilingual. | Preserve Bangla toggle; new copy needs a translation approach. |

---

## 11. Gaps and blockers (needs owner decision)

**Hard blockers for literal prompt compliance (backend change required):**

1. Change temporary password / forced first-login password change.
2. Withdraw image; add `detail` side; edit lot metadata; archive lot; reopen lot.
3. Product/buyer create/edit; clear login counters.
4. Persist/pass quality flags (BLUR/DARK/LOW_SCORE/UNKNOWN) and decision-time clauses/model versions.
5. Reviewer-is-overrider flag; single-supervisor flag; server `high_risk` field.
6. 409 stale-version, 429 rate-limit, 503 "Nothing was saved", request IDs, `__Host-` cookie, CSP headers.
7. Asynchronous inference job states (current upload blocks until inference completes).
8. Admin report view (currently 403).

**Frontend-only work can still deliver:** the full P0 visual/UX flow, all four outcomes, plan entry, capture, review/confirm/add defect, compute, override, second-supervisor approval, reason explanations, audit views, report preview/download, responsive/mobile, role-aware shell, loading/empty/error states, and honest demo labels.

**No mocks will be used for missing API actions.** Hiding a control with an explanation is honest; a fake withdraw/password-change success is not. Demo-only fixtures are limited to the existing seeded lots and are labelled.

---

## 12. Demo data status

Seed (`python -m app.seed`, six lots):

| Lot | Current seeded state | Intended demo outcome |
|---|---|---|
| `LT-2026-014` | Complete, one critical hole confirmed | REJECT |
| `LT-2026-015` | Complete clean sample | ACCEPT |
| `LT-2026-016` | 5 of 8 required units | HOLD (`HOLD_UNITS_MISSING`) |
| `LT-2026-017` | Sakura oil stain in zone II with no clause | ESCALATE (`ESCALATE_UNMAPPED_CLAUSE`) |
| `LT-2026-018` | No plan | HOLD (`HOLD_PLAN_MISSING`) |
| `LT-2026-019` | One open critical proposal on unit 1 front | Live ESCALATE demo |

Accounts: `admin@lotline.demo`, `supervisor@lotline.demo` (Farhan), `lead@lotline.demo` (Ayesha, second supervisor), `inspector@lotline.demo`; password `QualityFloor2026!`.

**Missing from seed for the prompt's demo set:** a system-REJECT lot with a **pending override to ACCEPT** awaiting a different Supervisor, and an effective override-to-REJECT example. These can be created through the real UI during demo setup (no DB edits): request the override on `LT-2026-014` as Farhan, approve as Ayesha. This changes `LT-2026-014`'s final disposition only after approval; the system recommendation stays REJECT. Owner to confirm this setup path.

---

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Backend deps not installed / server not running | Cannot verify P0 flow or capture a real detection sample | Install deps and start server in Phase 1 (owner approval). |
| No trained detector / no real photos | Judge may read staged panels as fake AI | Persistent "Staged synthetic · illustrative, not model output" tag; explain the numpy baseline honestly. |
| Synchronous inference in upload request | Slow/failed model blocks upload; no queued state | Client progress + timeout/error state; manual review path remains. |
| Frozen backend lacks fields | Some prompt requirements cannot be met | Hide/explain; list in final report; ask owner whether to authorize minimal backend exceptions. |
| Plan mode restricts file writes | PROGRESS.md/VERSIONS.md cannot be created in repo yet | Staged in `C:\Users\Jitu\.opencode\plan`; copy on switch to build agent. |
| Time budget unknown | Cannot allocate hours | Owner supplies demo date/time and total hours at Checkpoint A. |

---

## 14. Checkpoint A — decisions requested

1. **Frontend approach:** approve in-place Jinja2/CSS/JS redesign (recommended) instead of React. React would require a new API and violate the "do not modify backend" rule.
2. **Backend freeze:** confirm missing features are hidden/explained, not mocked. Or authorize a small, named backend exception list (e.g. change-password, withdraw, detail side, quality flags, decision context).
3. **Bangla:** keep full en/bn parity, or English-first with Bangla preserved on existing screens?
4. **Detector/photos:** is a trained checkpoint or 4–5 real garment images available? If not, confirm the "Illustrative, not model output" label.
5. **Demo logistics:** demo date/time, total build hours, phone availability, and whether the pending-override setup may be created on `LT-2026-014`.
6. **Environment:** approval to install `requirements.txt` and start the server on `127.0.0.1:8077` for Phase 1 verification.

**STOP — no code changed. Awaiting explicit approval.**
