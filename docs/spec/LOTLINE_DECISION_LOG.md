# Lotline — Architecture and business-rule decision log

**Revision:** 17 November 2026 (reconciliation of `PRD_v0_3.md`, `security-v0_4.md`, `SYSTEM_DESIGN_v1_2.md`, `lotline_research_prompt_v3_1.md`).
**Status labels:** APPROVED (the project owner approved it in writing on 17 Nov 2026), CONFIRMED (the owner confirmed an existing proposal), FOLLOWS (a direct consequence of an approved decision; listed so it is visible), PROPOSED / PENDING APPROVAL (not approved; the documents say so), SUPERSEDED.

## 1. Decisions taken by the owner on 17 November 2026

| ID | Decision | Status | Finding | Affects | Evidence |
|---|---|---|---|---|---|
| DL-01 | **Execution architecture, Option A:** a separate `InferenceWorker` container whose login role has **no table privilege** and that works only through `SECURITY DEFINER` functions, plus an isolated **DB-less `Vision`** container with a read-only model mount, a durable PostgreSQL `inference_job` queue, an isolated internal network, no API route to `Vision`, and job status as the source of truth with a derived image-status view. Extends Research Prompt D2 by one service. | APPROVED | LL-01 | Security 4.2, 4.6, 5.7, 5.9, 7.3; SD 1.3, 3.1, 4.12, 5.7, 7.5, 10.5, 11; PRD 5.4, 11.0, 11.8, FR-VIS; RP D2, H | Spike rev. 2: 39 of 39 PASS, PostgreSQL 16.x and 18.7 (DB side only). Network and container isolation NOT TESTED. |
| DL-02 | **Override policy** of Security 0.3 in all documents: Admin cannot override; only ACCEPT and REJECT decisions are overridable; a second, different Supervisor is required for a high-risk override (`OVERRIDE_ACCEPT`). | APPROVED | LL-03 | Security 5.6; SD 4.6, 8.9, 9.2, 5.4; PRD 9.6, FR-OVR; RP R6 | Documents only. T-92 NOT TESTED. |
| DL-03 | **Decision precedence** is Research Prompt v3 §H: HOLD (plan) → REJECT → ESCALATE → other HOLD → ACCEPT. Confirmed after the monotonicity re-check (see DP-OQ-1). | CONFIRMED | LL-02 | Security A28, 5.2; SD 8.6; PRD 9.4, FR-DEC-007; RP H | Documents only. T-91 NOT TESTED. |
| DL-04 | `critical_nonvisual_status` has the value **`failed`**; `failed` gives REJECT (`REJECT_CRITICAL_NONVISUAL_FAILED`). | CONFIRMED | LL-05 | Security BR-16; SD 8.3, 8.6; PRD FR-DEC-016; RP R13 | Documents only. T-90 NOT TESTED. |

## 2. Decisions that follow from the approved ones

| ID | Decision | Status | Why it follows |
|---|---|---|---|
| DL-05 | **Only a Supervisor sets `critical_nonvisual_status`.** v1.1 System Design also allowed Admin. | FOLLOWS (from DL-02 and Security A4: Admin is a system role with no QC action). **Owner: please confirm.** | Admin cannot override or decide; letting Admin set a gate that decides REJECT would contradict A4. |
| DL-06 | **`Re = Ac + 1` for every class** is the rule in all four documents (Research Prompt R3 said "Re not greater than Ac"). | FOLLOWS (Security BR-05 and SD 8.2 already enforce it; D6 fixes one `n`). | One rule, enforced by `CHECK` constraints and the guard. |
| DL-07 | **PostgreSQL 18** is the target (SD said 17). | FOLLOWS (Security A21; spike ran on 18.7). | One version across documents. |
| DL-11 | **Model self-test by the worker, then Admin activation.** `app_register_model` → `dispatcher_claim_selftest` / `dispatcher_record_selftest` → `app_activate_model`, which refuses without a passing self-test. `model_version` is immutable; activation is append-only (`model_activation`, view `v_active_model`). | FOLLOWS (the API has no route to `Vision`, so Security M4 cannot stay API-driven). | Spike S-19, S-20, S-38. |
| DL-12 | **Detector baseline is RF-DETR Small** (Security A15 and PRD ASM-15, TCON-02, ML-005 said Ultralytics YOLO). | FOLLOWS (approved D3, ADR-004). | One detector assumption. |
| DL-14 | **Manual mode never blocks (LL-10).** A queued job on a manually finished image is cancelled with `api_cancel_job` (queued to canceled only); a running job is fenced at write time; a live job blocks completeness only on a view with no human review. | FOLLOWS (the queue created the hazard; this is the narrowest fix). | Spike S-30, S-37. |
| DL-15 | **Reason-code strings are the System Design strings**; earlier Security and PRD names are retired (crosswalk in SD Appendix E.1). | FOLLOWS (DL-03 needs one vocabulary). | Audit section A and B: 0 non-canonical codes. |

## 3. Proposed, not approved

| ID | Proposal | Status | Options | Effect if rejected |
|---|---|---|---|---|
| **OV-10** | A decision whose primary reason is `REJECT_CRITICAL_NONVISUAL_FAILED` is **not overridable**. (v1.1 §8.9 already refused an override to ACCEPT; Security 0.3 did not mention it.) | PROPOSED, PENDING APPROVAL | Accept; or allow `OVERRIDE_ACCEPT` with second approval | Remove OV-10, FR-OVR-002 clause, T-92 case, TC-OVR-06 |
| **DP-OQ-1** | Under `highest_class_only`, evaluate ESCALATE **before** REJECT when an E2 or E3 condition touches a unit that contributes to the rejecting class. The monotonicity argument fails in that corner (example in Security 5.2 and SD 8.6). | PENDING APPROVAL (order in force: DL-03) | Keep §H order (a lot may be rejected and recomputed; never wrongly accepted); or add the exception | None: documents already state the approved order |
| DL-08 | **Prediction immutability by column:** detector-output columns are written once by `dispatcher_record_predictions` and never changed (`lotline_app` has no INSERT and only review-state UPDATE); a trigger rejects other changes. | PROPOSED | Column-level immutability (chosen in the documents, fewer edits); or split review state into `prediction_review` | Move the seven review columns to a new table and edit SD 4.5, 8.6, 9.2 |
| DL-09 | `provisional_critical` is a **stored routing hint** written with the prediction and **re-derived from the current clause table at decision time**. (Security 0.3 said "derived at read time, not stored"; SD 1.1 stored it.) | PROPOSED | As written; or drop the column | Remove the column and the stored-hint wording in SD 4.5 and 7.5 |
| DL-10 | PRD CG-17 (b) and (c) triggers become `ESCALATE_SECOND_OPINION_REQUESTED` (E4); PRD `CLASS_OUTSIDE_LIST` merges into `ESCALATE_UNMAPPED_CLAUSE`. | PROPOSED | As written; or keep separate codes | Add codes and tiers to SD 8.6 and the crosswalk |
| DL-13 | Three reason codes the System Design lacked are added to the precedence table: `HOLD_EVIDENCE_INTEGRITY`, `HOLD_COMPUTE_ERROR` (both existed in Security and the PRD) and `ESCALATE_SECOND_OPINION_REQUESTED`. | PROPOSED | As written | Remove tiers 6, 11, 12 and the Security/PRD rows |
| S5 | Behaviour when only one active Supervisor exists (override stays pending; Admin notified). | OPEN (PRD OQ-03) | n/a | n/a |

## 4. Superseded

| ID | Was | Replaced by |
|---|---|---|
| ADR-008 (SD) | Override on open/reopened latest decision; ACCEPT/REJECT reversible; ESCALATE/HOLD to REJECT only | DL-02 / ADR-021 |
| Security A15 (YOLO baseline) | Ultralytics baseline | DL-12 |
| PRD BRL-18 (HOLD gates before ESCALATE) | PRD 0.2 precedence | DL-03 |
| SD `model_version.is_active` and `uq_model_one_active` | Mutable activation flag | DL-11 |

## 5. Open question numbers closed in this revision

PRD OQ-02 (one `n` per plan) and OQ-11 (`OVERRIDE_RELEASE` does not exist); System Design N-01 and N-09; Security S15.
