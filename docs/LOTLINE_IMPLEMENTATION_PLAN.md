# Lotline — Phase 0 Implementation Plan (Checkpoint A draft)

**Constraint:** backend frozen. Frontend = Jinja2 templates + `static/app.css` + `static/app.js` + new static assets. No route, service, schema or `app/*.py` changes. No React/API build.
**Status:** proposed; not started. Stop at Checkpoint A.

## Frontend approach

The existing product is server-rendered. Every action is a form POST with a CSRF field and a 303 redirect; there is no JSON API. A React SPA would need new endpoints (forbidden) or a fully mocked app (dishonest for the P0 demo). Therefore:

- Keep the Jinja2 routes and form contracts; rebuild the presentation layer.
- Add reusable Jinja macros in `templates/components/` (Button, Input, Select, StatusBadge, DecisionBadge, PipelineStepper, DataTable, MetricCard, Dialog, Tabs, Toast, EmptyState, Skeleton, ErrorState, Timeline, DemoTag).
- Replace `static/app.css` with a token-based light theme (navy shell, lime accent) and a component stylesheet.
- Keep `static/app.js` small and dependency-free; use CSS/DOM for box overlay, zoom/pan, keyboard shortcuts, client-side validation, and the role switcher.
- Self-host Inter woff2 and vendor Lucide SVG paths; no runtime external requests.
- Adapt React-specific prompt items: `templates/components/` instead of `/src/components`; a generated static showcase at `/static/dev/components.html` instead of a `/dev/components` route (adding a route would modify the backend); JSDoc/data attributes instead of `/src/types` and TS.

## The 10-line implementation plan

1. **Phase 1 — Foundation (15%):** design tokens/type scale, self-hosted Inter, logo/favicon SVGs, Jinja component macros, app shell with role-based visibility, login, 15-code reason map, and a generated component/state showcase at `/static/dev/components.html`.
2. **Phase 2a — Lot detail control center (8%):** header, plan summary + assumption/test-config label, sample progress, status chips, two-line recommendation/final disposition, pipeline stepper, units/views grid, history.
3. **Phase 2a — Capture (8%):** unit/side picker, camera/file input, JPEG/PNG + 15 MB client checks, HEIC/iPhone hint, per-file progress/retry/result chips, inference state with manual-review fallback, no client resize.
4. **Phase 2a — Review (9%):** working-copy viewer, dashed AI boxes vs solid confirmed boxes, zoom/pan, proposal list, "score (uncalibrated)", confirm/edit/reject, add defect with zone/size band, server severity read-only, finish image, keyboard shortcuts.
5. **Phase 2b — Plan (8%):** supervisor form with no default `counting_mode`, `n`/Ac/Re per class, `Re = Ac + 1` guidance, read-back summary, warnings, test-configuration label, locked-after-decision explanation, Inspector read-only.
6. **Phase 2b — Decision Center (12%):** outcome, per-class n/Ac/Re/count/PASS-FAIL, reason codes in words + next step, completeness, critical-nonvisual control, compute, history, override panel (20-char reason), pending/effective badges, second-supervisor approval, server-driven refusals.
7. **Phase 3 — P1 (15%):** dashboard (open/HOLD/ESCALATE/recent/pending overrides from available data), lot list + create, audit log with client-side filters and Admin-only export; label anything unavailable.
8. **Phase 4 — P2 (7%):** report preview/download, configuration read-only (products/buyers/clauses; writes marked MISSING), user management (create/disable/enable/role/temp password; clear-counters marked MISSING).
9. **Phase 5 — QA + demo dry-run (13%):** Playwright screenshots at 375/768/1280, nav/filters/upload failure/role restrictions/decision consistency/dialogs/401/console checks, keyboard + contrast pass, then the 3-minute demo including manual fallback and two-supervisor approval.
10. **Checkpoint B + final report (0% extra):** post the P0 click path, stop for approval, then finish the final report with endpoints used, MISSING endpoints, demo-data paths, role-test results, conflicts and limitations.

## Time budget

Total build time `T` is **unknown**; the prompt's pre-flight field is empty. The shares below are the instructed allocation. Example hours are illustrative only and must be replaced when the owner supplies `T`.

| Phase | Share | Example at T=16h |
|---|---:|---:|
| 0 Recon | 5% | 0.8h (this report) |
| 1 Foundation | 15% | 2.4h |
| 2a Lot detail, Capture, Review | 25% | 4.0h |
| 2b Plan, Decision Center | 20% | 3.2h |
| 3 P1 screens | 15% | 2.4h |
| 4 P2 screens | 7% | 1.1h |
| 5 QA + demo dry-run | 13% | 2.1h |

If Phase 1 exceeds 20% of `T`, cut component variants, not P0 screens.

## Verification gates

- **Phase 1 done:** login works for all four seed accounts; shell at 375/768/1280 has no horizontal scroll; role nav is correct; `/static/dev/components.html` shows every component and state.
- **Phase 2a done:** on a phone-sized viewport, an Inspector can add a unit, upload a photo for a side, review every proposal, add a defect with zone, and finish the image against the real backend.
- **Phase 2b done:** all four outcomes and the pending override-to-ACCEPT flow are demonstrable; final disposition changes only after the second Supervisor approves; no browser-computed decision values.
- **Checkpoint B:** demo click path posted; stop.

## Dependency policy

No runtime JS/CSS dependency is required. Planned additions are assets only: Inter woff2 (OFL-1.1), Lucide SVG paths (ISC), and Playwright (dev-only). Every version is recorded in `VERSIONS.md`. No CDN, analytics or external font requests.

## Known deviations to list in the final report

- No React/TypeScript/Tailwind/shadcn/Recharts/Konva; equivalent Jinja/CSS/JS.
- No `/dev/components` route; generated static showcase instead.
- Missing backend features hidden/explained: change-password, withdraw, detail side, quality flags, decision clauses/model versions, reviewer-is-overrider, single-supervisor flag, product/buyer writes, clear-counters, 409/429/503/request IDs, Admin report view.
- Inference is synchronous; UI shows upload/inference progress and the manual-review fallback, not a durable queue.
- Demo detection is the numpy autoencoder on staged synthetic photos, labelled "Illustrative, not model output".
