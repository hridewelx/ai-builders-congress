# PROGRESS — Lotline frontend build

**Instruction:** `docs/LOTLINE_BUILD.md` (v4)
**Current phase:** 1 — Foundation (complete; awaiting Phase 2a approval)
**Checkpoint:** A approved (six recommendations); B pending after Phase 2b
**Last updated:** 18 November 2026
**Repo:** `D:\ai-builders-congress`

## Phase status

| Phase | Status | Budget | Notes |
|---|---|---:|---|
| 0 Recon | **Done** | 5% | Report + plan + this file + VERSIONS in repo; Checkpoint A approved |
| 1 Foundation | **Done** | 15% | Tokens, Inter, logos, component macros, shell, login, reason codes, showcase, DataTable/dialog/toast/tooltip |
| 2a Lot detail, Capture, Review | Not started | 25% | **Awaiting owner approval** |
| 2b Plan, Decision Center | Not started | 20% | — |
| 3 P1 screens | Not started | 15% | — |
| 4 P2 screens | Not started | 7% | — |
| 5 QA + demo dry-run | Not started | 13% | — |

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

## Verification

- **Backend tests:** `python -m pytest -q` → 36 passed.
- **Role page matrix** (Python, all roles en + bn): inspector (8 pages), supervisor (10), admin (9), lead (6) all 200 except `/audit` for inspector (correct 403 role enforcement). No template errors, no tracebacks.
- **Playwright 1.65.1** (chromium): 14/14 checks pass — login render, dashboard, lot tabs, capture, review, decision, audit, components (dialog open/close/Esc, toast, data-table filter/sort), rail collapse, mobile drawer, illustrative label present. **0 console errors.**
- **Responsive overflow:** 1280 / 768 / 375 all `scrollWidth == clientWidth` across login, dashboard, lot, capture, review, decision, audit, admin, components.

## Changed files (Phase 1)

Modified: `static/app.css`, `static/app.js`, `templates/base.html`, `templates/login.html`, `templates/_lotnav.html`, `templates/lot.html` (History anchor), `templates/dashboard.html` (inline color → token), `templates/how.html`, `templates/capture.html`, `templates/review.html`, `templates/report.html` (inline JS → data-print), `PROGRESS.md`, `VERSIONS.md`.
Added: `static/fonts/inter-latin-{400,500,600,700}-normal.woff2`, `static/brand/{logo-full,logo-full-light,logo-icon,favicon}.svg`, `templates/components/{icons,ui}.html`, `templates/_reason_codes.html`, `static/dev/components.html`.

## In progress

- None. Phase 1 complete.

## Next (after approval)

1. Phase 2a: lot detail, Capture, Review — apply the new component system to these screens.
2. Phase 2b: Plan, Decision Center, override/approval UI.
3. Post P0 click path, prepare demo dry-run, stop at **Checkpoint B**.

## Blockers

- Phase 2a requires explicit owner approval (per build constraints).
- Backend freeze (unchanged): no change-password route, withdraw, detail side, quality flags, decision-time model/clause data, reviewer-is-overrider, single-supervisor flag, product/buyer writes, clear-login-counters, 409/429/503/request IDs, or Admin report view. These are hidden/explained in the UI, never mocked.
- Trained detector / real garment images still unknown; demo remains staged synthetic photos + numpy autoencoder baseline, labelled "Illustrative, not model output".

## Decisions made

- In-place Jinja redesign; no React/API rewrite.
- No mocks for missing server actions; hide/explain controls and list them.
- Preserve en/bn toggle, append-only history, two-line disposition, override/approval, snapshot hash, PDF.
- Demo detection labelled "Illustrative, not model output"; photos "staged synthetic".
- Static component showcase at `static/dev/components.html` (adding a `/dev/components` route would modify the frozen backend).
- New bilingual copy lives in templates/macros (app/i18n.py frozen).

## Dependencies added

- None at runtime. Vendored assets: Inter 5.3.0 (OFL-1.1), Lucide 1.75.0 (ISC). Playwright 1.65.1 used for verification only (not shipped). No new pip/npm dependency added.