# PROGRESS — Lotline frontend build

**Instruction:** `docs/LOTLINE_BUILD.md` (v4)
**Current phase:** 2b — Plan, Decision Center, Override flow (complete; Checkpoint B reached)
**Checkpoint:** A approved; B reached (pending owner approval)
**Last updated:** 18 November 2026
**Repo:** `D:\ai-builders-congress`

## Phase status

| Phase | Status | Budget | Notes |
|---|---|---:|---|
| 0 Recon | **Done** | 5% | Report + plan + this file + VERSIONS in repo; Checkpoint A approved |
| 1 Foundation | **Done** | 15% | Tokens, Inter, logos, component macros, shell, login, reason codes, showcase, DataTable/dialog/toast/tooltip |
| 2a Lot detail, Capture, Review | **Done** | 25% | P0 screens upgraded: Control Center, Capture/Upload, Image Review & Defect Confirmation, Review Queue |
| 2b Plan, Decision Center | **Done** | 20% | Upgraded Sampling Plan, Decision Center, PRD §9.4 reason codes, 2-supervisor override & approval flow |
| 3 P1 screens | Not started | 15% | Lots list, Reports, Buyer summary, Audit log, Evidence export (Awaiting Checkpoint B approval) |
| 4 P2 screens | Not started | 7% | Calibration & Metrics, Admin |
| 5 QA + demo dry-run | Not started | 13% | Full click-path test, bilingual parity verification, responsiveness |

## Done

### Phase 0 (complete)
- Recon report, implementation plan, `PROGRESS.md`, `VERSIONS.md` copied into repo; `LOTLINE_BUILD.md` moved to `docs/`.
- Checkpoint A approved: in-place Jinja redesign, backend freeze, bilingual parity, illustrative label, no pending-override data yet, local install/run permitted.

### Setup (complete)
- Installed `requirements.txt` (FastAPI 0.163.2, Uvicorn 0.51.0, python-multipart 0.0.34, fpdf2 2.9.0, pytest 9.2.0, etc.) without changing version files.
- `python -m app.seed` → lots 1–6 seeded.
- Server running at `http://127.0.0.1:8077` (background). `/healthz` → `{"ok":true}`.
- Login verified for all four roles via `/demo/{inspector,supervisor,admin}` and form login for `lead@lotline.demo`.

### Phase 1 (complete)
- **Design tokens** (`static/app.css`): light navy/lime palette replacing dark theme; every legacy class name preserved (`.shell`, `.rail`, `.topbar`, `.content`, `.card`, `.btn`, `.badge`, `.kpi`, `.tblwrap`, `.tabs`, `.hero`, `.workspace`, `.viewer`, `.box`, `.prop`, `.timeline`, `.login`, …).
- **Self-hosted Inter 5.3.0** (4 weights, latin woff2) in `static/fonts/`; no CDN/font request.
- **Brand assets** in `static/brand/`: `logo-full.svg`, `logo-full-light.svg`, `logo-icon.svg`, `favicon.svg`.
- **Lucide 1.75.0 icon macro** (`templates/components/icons.html`, 70 icons) — vendor paths inline, no icon font/CDN.
- **Component macros** (`templates/components/ui.html`): button, badge, decision/status badge, metric card, pipeline stepper, empty/error/skeleton, timeline, tabs, form field/select, demo tag, AI illustrative label, dialog, confirm dialog, toast, tooltip.
- **App shell** (`templates/base.html`): collapsible role-aware sidebar, top bar (breadcrumb / demo tag / lang / avatar menu), honest admin alert area, mobile drawer + scrim, skip link, CSP meta, footer with persistent "Illustrative, not model output" label.
- **Sidebar nav** (`_lotnav` breadcrumb active states; `_lotnav.html` lot tabs): added History anchor; Configuration marked "Coming soon" with explanation (no product/buyer write routes exist).
- **Login redesign** (`templates/login.html`): logo, headline, build proof (4 outcomes / 0 AI approvals / 100% auditable), demo role grid (inspector/supervisor/admin one-click + lead form), generic bilingual error, demo password hint, explicit note that change-password is unavailable.
- **Reason code map** (`templates/_reason_codes.html`): all 15 active PRD §9.4 codes with bilingual title / plain-language condition / next step; `CALIBRATED_INTERVAL` intentionally absent (inactive); unknown codes render raw.
- **Component showcase** (`static/dev/components.html`): 13 sections covering tokens, buttons, forms, badges, KPIs, pipeline, tabs/menu, data table, dialogs/toasts/tooltips, empty/skeleton/error, timeline, reason codes, AI-vs-human proposal panel.
- **Interaction layer** (`static/app.js`): rail collapse, mobile drawer (Esc + scrim close), avatar menu outside-click, dialog open/close/Esc/backdrop, toast show/auto-hide, progressive data table (filter/sort/paginate), print, preserved review workspace (box↔proposal, heat map, manual box), form busy state.
- Fixed: login overflow at 768px (single-column breakpoint raised to 820, min-width:0 on login grid children); removed `frame-ancestors` from meta CSP (browsers ignore it there; header-level enforcement is backend work, out of scope).

### Phase 2a (complete)
- **Lot detail (Control Center — `templates/lot.html`)**:
  - Persistent 3-step pipeline stepper (`AI Detection -> Human Review -> Decision Engine`) derived dynamically from lot evidence.
  - Two-line recommendation & final disposition display per PRD (System recommendation vs Final disposition with pending vs effective override status).
  - Status alert chips: manual review active (not inferred), retake needed, second opinion pending, persistent illustrative AI label.
  - Action bar: Add Garment (+ unit with code validation hint), Capture, Review, Compute Decision (`POST /lots/{id}/decisions`), Sampling Plan, View Report.
  - Sampling plan summary with explicit ISO 2859-1 assumption note ("Normal inspection · Single sampling · General Level II").
  - Garments and views grid with status badges, defect indicators, thumbnails, and quick review links.
  - Critical non-visual check (Supervisor update form, notes) and audit history timeline.
- **Capture & Upload (`templates/capture.html`)**:
  - Persistent pipeline stepper and progress summary cards (sample units, photos uploaded, inference & review counts).
  - Factory-floor mobile filters: Unit quick-jumper (`#unitPicker`) and side filter buttons (`[data-filter-side]: all, front, back`) for rapid navigation on phone screens.
  - Camera/upload forms using `<input type="file" accept="image/jpeg,image/png" capture="environment">`.
  - Client checks: 15 MB limit, JPEG/PNG validation, iPhone HEIC detection and guidance ("Settings → Camera → Formats → Most Compatible"), "No faces, no badges" guidance.
  - Inference job status indicator per view with honest manual review fallback banner and direct review links.
- **Image Review & Defect Confirmation (`templates/review.html`)**:
  - Working copy inspection viewer with interactive zoom/pan (in, out, reset, mouse wheel, touch pan, pointer drag).
  - Synchronized `boxLayer` scaling and panning in lockstep with `mainImage`.
  - Attention map (heat map) toggle (`Show attention map` / `Show photo`).
  - Proposal list with defect class (bilingual), explicitly labeled `Score (uncalibrated)`, and flags (`LOW_SCORE`, `Critical routing`).
  - Proposal confirmation workflow: defect type select, buyer zone select, size band, notes, server-assigned severity notice, confirm/reject forms.
  - Second review workflow for supervisor other than reviewer on provisional critical rejections.
  - Manual defect placement on click (`#pendingBox`, coordinates calculation, type, zone, second opinion request).
  - Finish image view validation: blocks closing view with open proposals, enables "Reviewed clean" vs "Defects confirmed (X)" based on confirmed defect count, retake workflow.
  - Keyboard shortcuts dialog (`+`, `-`, `0`, `C`, `X`/`R`, `]`/`N`, `[`).
- **Review Queue (`templates/review_queue.html`)**:
  - Priority-sorted queue table (critical routing, manual, review) with pipeline stepper and direct review continuation link.
- **Interaction Layer & Styling Updates (`static/app.js`, `static/app.css`)**:
  - Synchronized `boxLayer` transform with `mainImage` during zoom and pan.
  - Keyboard navigation shortcuts in review workspace.
  - Mobile unit and side filter event listeners in capture view.
  - Added `.badge.badge-lime` and `.score-label` styling.

## Verification

- **Backend tests:** `python -m pytest -q` → **40 passed** (36 engine tests + 4 Phase 2a rendering tests in `tests/test_p2a_pages.py`).
- **Role page matrix:** Verified across all roles (`inspector`, `supervisor`, `admin`) in both English (`en`) and Bengali (`bn`).
- **Role gating verified:** Admin correctly receives 403 on `/lots/{id}/capture` and `/review/{img_id}`.
- **Template syntax & bilingual parity:** All Phase 2a templates verified 100% clean with zero template syntax errors.

## Changed files (Phase 2a)

Modified: `static/app.css`, `static/app.js`, `templates/lot.html`, `templates/capture.html`, `templates/review.html`, `templates/review_queue.html`, `PROGRESS.md`.
Added: `tests/test_p2a_pages.py`.

### Phase 2b (complete)
- **Sampling Plan (`templates/plan.html`)**:
  - Full Supervisor configuration form with sample size $n$, counting mode (`highest_class_only` vs `every_class`), per-class Acceptance/Rejection numbers ($Ac / Re$), and source edition/ref.
  - Client-side auto-helper setting $Re = Ac + 1$ automatically when modifying Acceptance number.
  - Dedicated Inspector read-only view with clear role notice (only Supervisor can edit).
  - Lot locked notice when lot is decided.
  - Mandatory ISO 2859-1 Level II assumption notice with clear disclaimer ("assumption, not a standard lookup; Lotline never looks up plans automatically").
  - Plan Read-back verification card summarizing the configured acceptance threshold per defect class.
  - 100% inspection warning banner if $n \ge \text{lot\_size}$.
- **Decision Center (`templates/decision.html`)**:
  - Prominent Decision Outcome Hero covering all 4 PRD outcomes (`ACCEPT`, `REJECT`, `HOLD`, `ESCALATE`) with explicit two-line disposition (System recommendation vs Final disposition).
  - Explicit PRD §9.4 plain-language reason code mapping with bilingual "Next step" cards via `_reason_codes.html`.
  - Detailed class breakdown table (Critical, Major, Minor) with counts, $Ac/Re$ thresholds, and visual PASS/FAIL status tags.
  - Completeness & Evidence Integrity card displaying unit capture count ($k/n$), image views, unreviewed views count, and evidence snapshot SHA-256 hash.
  - Critical non-visual check status block with verification status and supervisor notes.
  - Explicit "Recompute Decision" button with loading state.
- **Supervisor Override & Two-Supervisor Approval Flow**:
  - Supervisor override form requiring minimum 20-character reason with live counter in `static/app.js`.
  - Automatic client detection of High-Risk overrides (`REJECT -> ACCEPT` or when Critical defects exist), informing the user that a second supervisor's approval is mandatory.
  - Pending approval state banner showing who requested the override, timestamp, and justification.
  - Self-approval block: Initiating Supervisor A sees "Self-approval forbidden — awaiting review by another supervisor".
  - Second Supervisor B actions: Supervisor B sees "Second Supervisor Action" panel with Approve and Refuse buttons and notes field.
  - Immutable audit history of past overrides.

## Verification

- **Backend tests:** `python -m pytest -q` → **43 passed** (36 engine tests + 4 Phase 2a rendering tests + 3 Phase 2b rendering tests in `tests/test_p2b_pages.py`).
- **Role page matrix:** Verified across `inspector`, `supervisor`, `admin` roles in both `en` and `bn`.
- **All 4 decision outcomes verified:** ACCEPT (Lot 2), REJECT (Lot 1), HOLD (Lot 3, 5), ESCALATE (Lot 4).
- **Override safety verified:** Self-approval forbidden, second supervisor approve/refuse actions verified.

## Changed files (Phase 2b)

Modified: `templates/plan.html`, `templates/decision.html`, `static/app.js`, `PROGRESS.md`.
Added: `tests/test_p2b_pages.py`.

## Checkpoint B: Awaiting Owner Approval

Phase 2b is complete and verified. As mandated by the phased roadmap, execution is paused at **Checkpoint B** for owner review before starting Phase 3 (P1 screens).

## Blockers

- Checkpoint B pending after Phase 2b.
- Backend freeze (unchanged).

## Decisions made

- Pipeline stepper derived dynamically from lot evidence in templates (UI only, no schema changes).
- Two-line recommendation & final disposition display strictly separates deterministic system recommendation from latest effective supervisor override.
- Mobile unit jumper & side filters in Capture view enhance factory-floor usability without altering data structures.
- Synchronized bounding box layer transform with working copy image transform ensures accurate defect overlay during zoom and pan.
