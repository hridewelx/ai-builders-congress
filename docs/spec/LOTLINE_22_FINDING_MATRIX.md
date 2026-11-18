# Lotline — resolution matrix for the 22 audit findings

**Date:** 17 November 2026. **Repository:** none was supplied, so every "source file" below is a **planned path from System Design 5.1** that must be checked against the repository; nothing has been changed in code.
**Original audit report:** not supplied. Only the IDs, severities and one-line titles of LL-01 to LL-10 and the counts for the rest (8 Medium, 4 Low) are known from the project brief. LL-11 to LL-22 are **BLOCKED**; no finding was invented.

**Status vocabulary.** *Documents* = whether the four documents now agree and are implementable. *Verification* uses only PASS, FAIL, NOT TESTED, BLOCKED, DEFERRED; **PASS means evidence exists** (the spike on a reduced schema; the cross-document audit script). No repository test has been run.

## Summary

| ID | Severity | Documents | Verification | Pending approval |
|---|---|---|---|---|
| LL-01 | Critical | RESOLVED (Option A approved) | Spike DB side: PASS (39/39, PostgreSQL 16.x and 18.7). Network, containers, RF-DETR loading, outage handling: NOT TESTED | none |
| LL-02 | Critical | RESOLVED (v3 §H order confirmed) | NOT TESTED (T-91) | DP-OQ-1 |
| LL-03 | Critical | RESOLVED (Security 0.3 policy adopted) | NOT TESTED (T-92) | OV-10 |
| LL-04 | High | RESOLVED (Security matrix is canonical; SD matrix replaced) | NOT TESTED | DL-05 confirmation |
| LL-05 | High | RESOLVED (gate added to PRD and Security; `failed` confirmed) | NOT TESTED (T-90) | none |
| LL-06 | High | RESOLVED (one `n` per plan, D6) | NOT TESTED (T-46 to T-48, TC-PLAN-05) | none |
| LL-07 | High | RESOLVED (`counting_mode` in PRD and Security) | NOT TESTED (T-93) | none |
| LL-08 | High | RESOLVED (zone and size-band key in PRD and Security) | NOT TESTED (T-94) | none |
| LL-09 | High | RESOLVED (SD 4.12 and Security DB-15 to DB-22) | Reduced schema: PASS (spike). Full schema and guard: NOT TESTED | none |
| LL-10 | High | RESOLVED (manual mode never blocks) | Reduced schema: PASS (S-30, S-37). End to end: NOT TESTED (T-84) | none |
| LL-11 to LL-22 | 8 Medium, 4 Low | **BLOCKED** (original report needed) | BLOCKED | n/a |

## LL-01 — Inference architecture and trust boundary (Critical)

| Item | Content |
|---|---|
| Conflict found | Security: API sends bytes to an `inference` container over `infer_net`, no queue. SD: separate worker with DB access and the model in-process. RP D2: no Vision container. PRD: no worker or queue. |
| Resolution | Option A (approved). `API` has no route to `Vision`. `InferenceWorker` (no table privilege; six `dispatcher_*` functions) is the only bridge. `Vision` is DB-less with a read-only model mount. Job table is the source of truth; image inference status is a derived view. |
| Documents changed | Security 4.2, 4.3, 4.5, 4.6, upload rows UP-07, W6, W7, AI-01 to AI-18 and the model procedure rows M4, M5, diagram 7.3, DEP rows, TM-26 to TM-29, TM-46 to TM-48, FH-01 to FH-03, FH-23, T-34, T-38, T-40, T-41, T-79 to T-89; SD Revision 1.2, 1.3, 3.1, 4.5, 4.12, 5.7, 7.5, 7.9, 10.1, 10.5, 11.1, 11.2, 12.2, 12.3, ADR-018, ADR-022; PRD 11.0, 11.8, FR-VIS-001 to 012, W-07 flow; RP D2, H, canonical names |
| Related concerns | `SKIP LOCKED` privilege (S-01, S-02: needs UPDATE, so it sits with the function owner); dispatcher privileges (DB-15, DB-16); prediction immutability (DL-08); model activation immutability (DL-11); RF-DETR loading (U21, T-88: unverified for the pinned version); crash recovery (lease, heartbeat, fencing); duplicate prevention (unique `(job, ordinal)`); Vision outage (worker stops claiming); superseded images and concurrent decisions (lot lock, S-21, S-22) |
| Planned source files | `backend/app/workers/inference_worker.py` (rewrite: health check, claim, read-only image read and hash check, HTTP call, heartbeat thread, fail and record); `backend/app/modules/vision/{contracts,detector,preprocess}.py` plus a new server entry point for the `Vision` image; `backend/app/modules/vision/client.py` (new, HTTP only); `backend/app/storage/model_store.py` (hash verification in `Vision`); `backend/app/modules/capture/service.py` (W6 inserts the job; supersession calls `api_cancel_job`); `backend/app/api/v1/images.py` (enqueue, cancel endpoint); `docker-compose.yml`, `backend/Dockerfile` (worker and `Vision` targets), import-linter config |
| Migration | M-01 to M-08 in `LOTLINE_MIGRATION_TASKS.md` |
| API / config | `POST /images/{id}/inference/cancel`; `WORKER_LEASE_SECONDS`, `WORKER_CONCURRENCY`, `INFERENCE_ENABLED`, `AUTO_ENQUEUE_INFERENCE`, Vision URL and timeout; networks `app_net`, `db_net`, `infer_net` |
| Tests required | T-38, T-79 to T-82, T-85 to T-89, T-95 (Security 10); spike S-01 to S-39 as the reference |
| Acceptance | The worker login role has no table privilege; a stale writer writes nothing; `Vision` has no route to `db` or `api`; `api` has no route to `Vision`; invalid output is stored nowhere; a malicious checkpoint cannot reach the network, database or images |
| Verification | Spike on a reduced schema: PASS, 39/39 on PostgreSQL 16.x and on 18.7 (`spike_results_pg16.txt`, `spike_results_pg18.txt`). Everything outside the database: NOT TESTED |
| Residual | U21 (RF-DETR pinned-version loading) unverified; container hardening and network tests not run |

## LL-02 — QC decision precedence conflict (Critical)

| Item | Content |
|---|---|
| Conflict found | SD and RP: HOLD(plan), REJECT, ESCALATE, other HOLD, ACCEPT. Security A28 and PRD: HOLD, ESCALATE, ACCEPT/REJECT. Reason-code names differed in all documents. Two outcome-changing differences: complete sample with a class at `Re` plus an open ESCALATE; unreviewed view with an open critical proposal. |
| Resolution | v3 §H order (confirmed), with H4 to H6 and E4 added, one set of reason-code strings (SD 8.6, Appendix E.1), and a **corrected monotonicity argument** (holds for `every_class`, can fail for `highest_class_only`; failure direction is safe; DP-OQ-1 pending). |
| Documents changed | Security A28, 5.2 table, BR-07, BR-18, EV-10; SD 8.5, 8.6, B enums, E.1; PRD BRL-10, BRL-11, BRL-18, BRL-27, 9.4, 9.5, 9.7, 9.8, FR-DEC-004 to 007; RP H |
| Planned source files | `backend/app/modules/decision/engine.py` (tier order, reason-code enum), `decision/schemas.py`, `decision/service.py`, the `record_decision` migration, `alembic` `CHECK` on `decision.reasons` values |
| Tests required | T-91 (one case per tier and adjacent pair, plus the `highest_class_only` corner), TC-DEC-12, TC-DEC-17, TC-DEC-18 |
| Acceptance | Outcome and primary reason match the table in every case; all matching reasons are recorded; no retired code is accepted by the API or stored |
| Verification | Documents: audit sections A and B executed, 0 reason-like codes outside the canonical 15 in all four files (`crossdoc_audit_results.txt`). Engine: NOT TESTED (no code) |

## LL-03 — Override policy conflict (Critical)

| Item | Content |
|---|---|
| Conflict found | SD 8.9: Supervisor or Admin; HOLD and ESCALATE may be overridden to REJECT. Security and PRD: Admin cannot; HOLD never; PRD also allowed ESCALATE overrides. |
| Resolution | Security 0.3 policy (approved): Supervisor only; ACCEPT or REJECT decisions only; `OVERRIDE_ACCEPT` needs a different Supervisor; one override per decision; reason at least 20 characters; `OVERRIDE_RELEASE` does not exist. OV-10 proposed. |
| Documents changed | Security OV-10 (new), 6 matrix; SD 4.6 (`override`, `override_approval`), 8.9, 9.2, 5.4, C-18, ADR-008 superseded, ADR-021; PRD line 63, BRL-19, FR-OVR-002, FR-OVR-003, OQ-11 closed, TC-OVR-02, TC-OVR-05, TC-OVR-06; RP R6 |
| Planned source files | `decision/service.py` (override orchestration), `app/api/v1/decisions.py` (override and approval endpoints), `app/api/deps.py` (Supervisor-only dependency), triggers on `override` and `override_approval` |
| Tests required | T-92, T-55, T-56, TC-OVR-01 to TC-OVR-06 |
| Acceptance | Admin override refused with an audit row; HOLD and ESCALATE refused; `OVERRIDE_ACCEPT` ineffective until a different Supervisor approves; self-approval refused |
| Verification | NOT TESTED |
| Residual | OV-10 pending; S5 open |

## LL-04 — Role permissions (High)

| Item | Content |
|---|---|
| Conflict found | SD 5.4 gave Admin plan, upload, review, decide, reopen, override and critical non-visual rights; Security A4 and PRD 5.1 give Admin none of them. |
| Resolution | Security section 6 matrix is canonical; SD 5.4 replaced; PRD matrix gained two rows. "Inspector+" is defined as Inspector or Supervisor; every `Supervisor+` was changed to `Supervisor`. |
| Documents changed | SD 5.4, 9.2, C-19; Security matrix rows; PRD matrix rows |
| Planned source files | `app/api/deps.py`, route decorators in `app/api/v1/*.py`, role tests |
| Tests required | A matrix test that exercises every row for every role (Security T-xx for AZ rows) |
| Acceptance | Every denied action returns 403 and an audit row |
| Verification | Audit pattern F: 0 occurrences of `Supervisor+`. Authorization behaviour NOT TESTED |

## LL-05 — Missing critical non-visual gate (High)

| Item | Content |
|---|---|
| Resolution | `lot.critical_nonvisual_status` (`pending`, `done`, `not_required`, `failed`) added to PRD (BRL-24, FR-DEC-016, FR-DEC-018) and Security (BR-16, EV-10, A32); only a Supervisor sets it; `pending` blocks ACCEPT; `failed` rejects even an incomplete sample. |
| Planned source files | `app/modules/lots` model and service, `POST /lots/{id}/critical-nonvisual-status`, `decision/engine.py`, guard function, report template |
| Tests required | T-90, TC-DEC-17, TC-DEC-19 |
| Acceptance | See PRD TC-DEC-19; Admin and decided lot refused; guard path EV-10 works without completeness checks |
| Verification | NOT TESTED |

## LL-06 — One `n` per plan versus per-class `n` (High)

| Item | Content |
|---|---|
| Resolution | One `n` per plan (D6, approved); `(Ac, Re)` per class; `Re = Ac + 1`; required sample = `min(n, lot size)`; `PLAN_N_MISMATCH` retired. |
| Documents changed | Security A27, BR-05, data model (`plan`, `plan_class`), S15; PRD BRL-02, BRL-08, BRL-13, FR-PLAN-001, 003, 004, 005, OQ-02, CG-12, entity table, TC-PLAN-03, TC-PLAN-05; SD unchanged (already single `n`; N-09 closed); RP R3 |
| Planned source files | `modules/plan/{models,schemas,engine}.py`, plan screen, migration M-09 |
| Tests required | T-46 to T-48, TC-PLAN-02, TC-PLAN-03, TC-PLAN-05 |
| Acceptance | A plan with a second `n`, a missing `n`, or `Re != Ac + 1` is refused at entry and by the database |
| Verification | NOT TESTED |

## LL-07 — Configurable counting mode versus hard-coded behaviour (High)

| Item | Content |
|---|---|
| Resolution | `counting_mode` is a required plan field (`highest_class_only` or `every_class`), immutable with the plan version, printed on the report and stored in the evidence snapshot (BR-15, BRL-23, FR-DEC-002, FR-DEC-017). |
| Planned source files | `modules/plan` model and engine, SQL view `v_unit_class` (both modes), `decision/engine.py`, report |
| Tests required | T-93, TC-DEC-04 |
| Verification | NOT TESTED |

## LL-08 — Missing zone and size-band severity mapping (High)

| Item | Content |
|---|---|
| Resolution | Severity key `(buyer, defect_type, zone_code, size_band)`; exact match then empty-band fallback; no match gives `needs_clause` and ESCALATE (BR-17, BRL-25, FR-CLS-005, A31). SD 8.4 already had it. |
| Planned source files | `modules/review/service.py` (lookup, zone choice), `clause_mapping` seed JSON, review screen zone selector, migration M-11 |
| Tests required | T-94, TC-CLS-05 |
| Verification | NOT TESTED |

## LL-09 — Missing DB roles and decision guard in System Design (High)

| Item | Content |
|---|---|
| Resolution | SD 4.12 (roles, function catalogue, column-level grants, append-only limit and detection, locks, permission of every database operation) and Security DB-15 to DB-22. Eight roles; `lotline_dispatcher` has no table privilege. The reference implementation is the spike. |
| Spike gaps found and closed | P-01 owner can disable triggers (documented limit plus detection view); P-02, P-03, P-07 API could forge or revive jobs (column-level `INSERT (image_id)`, `api_cancel_job`); P-04 no heartbeat or fail function (added); P-05 no output validation (added, and a NULL-handling bug in the first version was found by test S-33 and fixed); P-06 table-level `UPDATE` on `lot` (now `UPDATE (updated_at)`) |
| Planned source files | `alembic/versions/*` (M-01, M-05, M-06), `app/db/session.py` (two engines: `lotline_app`, `lotline_dispatcher`), worker DB config |
| Tests required | T-79, T-80, T-81, T-82, T-83, T-95 |
| Verification | Reduced schema: PASS (S-01 to S-39 as listed in Security Appendix F). Full decision guard (EV-04, EV-05, EV-10) and full schema: NOT TESTED |

## LL-10 — Manual mode may deadlock if the worker is unavailable (High)

| Item | Content |
|---|---|
| Resolution | A job never blocks a view that already has a human review (SD 8.5, 8.6 H2; PRD BRL-26, FR-REV-014; Security BR-13, AI-16). `api_cancel_job` cancels a queued job (queued to canceled only) and frees the one-active-job index; a running job is fenced at write time (`manual_review`). |
| Planned source files | `modules/review/service.py` (finish image manually calls the cancel), `app/api/v1/images.py` (cancel endpoint), `decision/service.py` (completeness read), `dispatcher_record_predictions` |
| Tests required | T-84, TC-VIS-08 |
| Verification | Reduced schema: PASS (S-30, S-37). End to end: NOT TESTED |

## LL-11 to LL-22 — remaining findings (8 Medium, 4 Low)

| Item | Content |
|---|---|
| Status | **BLOCKED.** The original audit report was not supplied (the placeholder in the owner's message was left unfilled). Severities and descriptions are unknown. |
| What is available | `LOTLINE_CROSSDOC_AUDIT.md` lists **candidate issues found during this reconciliation** (section 5). They are **not** assigned LL IDs and must not be assumed to be the original findings. |
| Next action | Supply the report; each finding then gets the same table as above. |
