# LOTLINE: Phased UI/UX Build Prompt (v4)

> Usage: keep this file in the repo at `docs/LOTLINE_BUILD.md`. Start the agent with: "Read docs/LOTLINE_BUILD.md and begin Phase 0." After any context reset: "Read docs/LOTLINE_BUILD.md and PROGRESS.md, then resume."
>
> v4 aligns v3 with PRD v0.3, Security v0.4 and System Design v1.2. See "What changed from v3" at the end.

## ROLE

You are a Senior Product Designer and Senior Frontend Engineer. You will redesign and build the frontend of **LOTLINE**, an AI-assisted garment quality inspection and lot-acceptance decision-support platform, for live demonstration at an AI Builders Hackathon.

Work in phases. Finish and verify each phase before starting the next. At the end of each phase: (1) git commit, (2) update `PROGRESS.md` (done / in progress / next / blockers / decisions made), (3) post a short status.

## HUMAN CHECKPOINTS (hard stops)

Stop and wait for my explicit approval at exactly these two points. Do not continue past them on your own:

- **Checkpoint A:** after the Phase 0 report and implementation plan.
- **Checkpoint B:** after Phase 2b (all P0 work). I will run the P0 flow myself and may redirect before P1/P2 begin.

Between checkpoints, continue without asking unless you hit a real blocker (missing information that cannot be found in the repo or the documents below).

## PRE-FLIGHT (owner fills before running; the agent never invents these)

- Repo path: `[REPO_PATH]`
- Sources of truth, in this order of precedence (the PRD owns product rules; where documents disagree, the PRD wins and you list the difference in `PROGRESS.md`):
  1. `docs/PRD_v0_3.md` (read fully; screens are in section 15, business rules in section 9, API list in section 14)
  2. `docs/SYSTEM_DESIGN_v1_2.md` (API, schema, states, reason-code crosswalk in Appendix E.1)
  3. `docs/security-v0_4.md` (auth, session, upload, headers, dependency rules)
- Backend status: `[REAL backend running at <base URL, how to run> | NOT BUILT or NOT REACHABLE -> run the whole app in MOCK MODE]`
- Trained detector: `[exists: checkpoint and model version | not yet: recorded and illustrative data only, labeled as such]`
- Existing frontend stack: `[React/Vite/Tailwind/none]`
- OpenAPI spec or endpoint list: `[path or URL]`. PRD section 14 marks many endpoints "Proposed"; any endpoint not found in the running backend is MISSING, not assumed.
- Sample real detection response: `[paste one real JSON]`
- Demo setup: primary = laptop on projector; secondary = live phone demo of the inspector flow `[adjust if different]`
- Demo date/time: `[date/time]`. Total build time available: `[hours]`

If a field is empty, look in the repo and documents. If it cannot be found, list it as an open question in the Phase 0 report. **If backend status or detector status is empty, stop at Checkpoint A and ask.**

## TIME BUDGET

Allocate the total build time roughly as follows and tell me in `PROGRESS.md` if you are running over:

| Phase | Share |
|---|---|
| 0 Recon | 5% |
| 1 Foundation | 15% |
| 2a Lot detail, Capture, Review | 25% |
| 2b Plan, Decision Center | 20% |
| 3 P1 screens | 15% |
| 4 P2 screens | 7% |
| 5 QA + demo dry-run | 13% |

Do not over-invest in the design system at the expense of P0. If Phase 1 passes 20%, cut component variants, not P0 screens.

## CORE PRINCIPLE (non-negotiable)

**AI proposes. Humans verify. The decision engine decides.**

- AI never approves or rejects a lot. The browser never computes a decision, severity, count or high-risk flag: it renders what the server returns.
- The UI must always make three things visually distinct: AI prediction, human-confirmed defect, deterministic engine recommendation.
- Never show fake AI output as real model output. Never show success unless the backend confirmed it. Do not invent fields the API does not return.
- Demo, mock or recorded data must be labeled in the UI (persistent "Demo data" or "Recorded result" tag) and isolated in `/src/mocks` and `/src/demo-data` behind a single flag. Never mix real and demo records on the same lot.
- **Labels required by the PRD:** every AI score is shown as "score (uncalibrated)", never "confidence" and never as a percentage probability of being a defect. Wherever a sampling plan appears, show its assumption label.

**Pipeline indicator (UI only, no new data):** show a persistent three-step stepper "AI Detection -> Human Review -> Decision Engine" on the lot detail page, the Capture and Review screens, and the Decision Center. Each step shows its real state derived from lot data:

- AI Detection: per image `pending | ok | failed | not_inferred`, summarized as a count. A failed or not-inferred image is a valid state shown as "Manual review", not an error: manual review is never blocked.
- Human Review: images reviewed of required.
- Decision Engine: no decision / current recommendation / stale (needs recompute).

## DECISION RULES (PRD section 9; take exact definitions from it, do not create thresholds)

- Outcomes: ACCEPT, REJECT, HOLD, ESCALATE. The recommendation comes only from the server.
- Always show two separate lines: **System recommendation** and **Final disposition**. Final disposition is the latest *effective* override, else the recommendation. A pending override never changes it (FR-OVR-007).
- Only a Supervisor can override; Admin and Inspector cannot. Only ACCEPT or REJECT can be overridden. HOLD and ESCALATE never can. A decision with `REJECT_CRITICAL_NONVISUAL_FAILED` is not overridable (OV-10, still PROPOSED: build it as a server-driven refusal message, so it follows the server if the owner changes it).
- An override needs a written reason of at least 20 characters.
- **High-risk** means an override to ACCEPT over a system REJECT (FR-OVR-003, OV-04, BRL-19). It takes effect only after approval by a **different** active Supervisor. An override to REJECT (stricter) is effective at once. Self-approval is refused. **Render the server's `high_risk` flag; never compute it in the browser.** (PRD W-14 describes high-risk more broadly than FR-OVR-003: do not resolve this yourself; log it as an open question.)
- If the overriding Supervisor confirmed any defect on the lot, show the "reviewer is overrider" flag (FR-OVR-008).
- Single-Supervisor mode (only one active Supervisor): show a HIGH RISK flag and the text that the Admin is notified (S5, still an open question: render what the server returns).
- Unavailable actions must show a visible explanation of why and the next step (NFR-USA-002), never a silent disabled button. Actions a role never has (for example the override panel for an Inspector) are hidden or shown read-only with a one-line note; the server enforces permissions regardless.

## ROLES (confirm every cell against the PRD role matrix in section 5)

- **Inspector:** create lots, register units, capture, review, compute decision, generate report for own lots. Sampling plan read-only.
- **Supervisor:** everything an Inspector does on any lot, plus enter the sampling plan, set critical non-visual status, override, approve or reject another Supervisor's high-risk override, read the audit log, manage products and buyers.
- **Admin:** no QC action: cannot create lots, review, override or set the plan. Manages users, reads lots, decisions and reports, reads and exports the audit log, sees system alerts.

## SCOPE GUARDRAILS (do not)

- Do not add features, fields, or configuration options that are not in the PRD.
  - **Exemption:** demo infrastructure explicitly described in this document (login-based role switcher, seed accounts, mock mode, recorded-result lots, seeded demo lots, pipeline indicator) is allowed. Keep it isolated and marked demo-only.
- Do not modify the backend. If an API gap blocks a feature, mock it in `/src/mocks`, label it, and list it in the final report.
- Do not rewrite working existing logic; wrap or restyle it.
- Do not add a dependency without a one-line justification in `PROGRESS.md`. Pin every dependency to an exact version and record it in `VERSIONS.md` (Security AI-06).
- Do not use the tagline anywhere except the login screen. (Report headers are rendered by the server in the PDF; do not alter them.)
- Do not build any ISO 2859-1 / ANSI Z1.4 table, AQL lookup or "suggest a plan" feature (FR-PLAN-007). Plans are entered by a Supervisor. Demo plans carry the source label "test configuration" (FR-PLAN-009).
- Do not leave placeholder buttons that look functional but do nothing. Hide the control or mark it "Coming soon".
- Not in the PRD, so not built: notifications bell, global search, user "profile" page, aggregate report builder (filters, summaries, defect breakdown), buyer-clause editing (clause list is read-only in Version 1, FR-CLS-001), configurable defect classes or "inspection config" (the defect type list is fixed, FR-REV-002), acceptance-rate KPIs.

## PRIORITIES

- **P0 (must be excellent, this is what judges see):** Login, Lot detail (control center), Image capture and upload, Image review and defect confirmation, Sampling plan, Decision summary with override and approval, mobile inspector flow.
- **P1 (polished and functional):** App shell, Dashboard, Lot list and create lot, Audit log.
- **P2 (functional, clean, consistent; do not over-polish):** Report view, Configuration (products, buyers, read-only clauses), User management.

If time or context runs short, cut P2 depth first, never P0.

## DESIGN SYSTEM

**Brand:** LOTLINE. Tagline (login only): "Inspect Intelligently. Decide Consistently. Deliver Confidently."

**Visual reference (for feel, not to copy):** Linear for information density and spacing discipline; Vercel dashboard for typographic restraint and calm hierarchy; Stripe Dashboard for data tables and status clarity. Aim for quiet confidence: lots of structure, little decoration.

**Tokens (define once as CSS variables / Tailwind theme):**

| Token | Value |
|---|---|
| Midnight Navy | #101E2B |
| Deep Navy | #172A3A |
| Electric Lime (accent) | #B7F36B |
| Background | #F6F8FA |
| Surface | #FFFFFF |
| Text primary | #182230 |
| Text secondary | #64748B |
| Border | #E5EAF0 |
| Success | #16834A |
| Warning | #D99020 |
| Danger | #D64545 |
| Info | #4263A8 |

**Color rules:**
- Lime is an accent only: on navy backgrounds, as small indicators, or as a fill with navy text. Never as text on white (fails contrast). Never as a page or card background.
- Decision colors are fixed everywhere: ACCEPT = Success green, REJECT = Danger red, HOLD = Warning amber, ESCALATE = Info blue. Lime never represents ACCEPT.
- AI prediction vs human-confirmed must differ by more than color: AI proposal = dashed box + "AI" chip; confirmed = solid box + check icon; rejected = grey, struck-through label. Works for color-blind users.

**Typography:** Inter, **self-hosted** (no CDN or external font request; the CSP is restrictive, Security DEP-07). Define a scale for page title, section heading, card heading, body, table, label, status, metadata. Tabular numerals for counts and metrics.

**Style:** Minimal, information-dense, 4/8px spacing scale, restrained radii (6-10px), subtle borders and shadows, Lucide icons only (no emoji as UI icons), subtle transitions, no decorative gradients.

**Logo (deliver as SVG files):** `logo-full.svg` (icon + wordmark, light backgrounds), `logo-full-light.svg` (navy backgrounds), `logo-icon.svg` (compact / sidebar collapsed), `favicon.svg` (and `favicon.ico` if practical). Concept: inspection frame or measurement line combined with a subtle checkmark. Simple, geometric, legible at 16px. No brain icons, no random gradients.

## GLOBAL ENGINEERING RULES

- Inspect the existing stack first and preserve its architecture. If a new frontend is required, use React + TypeScript + Tailwind + shadcn/ui + Lucide + Recharts, and Konva (or equivalent) for annotation.
- TypeScript types for all API shapes in one place (`/src/types`). Reusable components, consistent naming.
- **Security rules from Security v0.4:**
  - Session is a server-side cookie (`__Host-`, HttpOnly). Send the CSRF token and custom header exactly as the API contract says. Keep the CSRF token in memory only. **No tokens or sensitive data in `localStorage` or `sessionStorage`** (SES-06).
  - Escape all stored text (notes, filenames, names). Never use `dangerouslySetInnerHTML` on user or stored content.
  - No external network requests other than the API (no CDN fonts, scripts or analytics).
  - Error bodies show the request ID and no stack trace or internal detail (NFR-USA-003).
  - A 401 (idle 30 min, absolute 8 h) returns the user to login and back to the same page afterwards. A 429 shows a plain "too many requests" message.
- Accessible: keyboard navigable, visible focus states, WCAG AA contrast, aria labels on icon buttons.
- Every async view has loading (skeleton), empty, and error states. Use the PRD section 15 empty-state wording where it gives one (for example "No proposals. This is not a pass. Review the photo").
- No horizontal scroll at 375px, 768px, or 1280px widths.

## DEMO RELIABILITY (required)

A live demo must survive a slow or failed model call and an expired session.

1. **Seed accounts:** one Inspector, two Supervisors (A and B), one Admin. A dev-only role switcher (excluded from production builds, credentials never bundled in production) that performs a **real logout and login** with the seed credentials. It never fakes a role in the client. Remember the login delay and the 30/min rate limit: do not script failed logins. Log in fresh shortly before the demo so the session does not expire during it.
2. **Inference failure path (real):** inference is an asynchronous job, not a call with a timeout. Show queued / running / ok / failed per image. If the detector is unavailable or a job fails, show the "Not inferred, detector unavailable" state and let the reviewer continue with **manual review** (add defects by hand). This is the real fallback and must work on a real lot.
3. **Recorded results (demo lots only):** prepare 4-5 real garment images with the real saved detection outputs produced by the actual model beforehand (`/src/demo-data`). They exist only in lots whose data source is `demo`, with a persistent "Recorded result" tag. They never create or modify real prediction rows (predictions are append-only and tied to a model hash). In a demo lot the whole flow is fixture-driven and tagged. If no trained detector exists, the data is tagged "Illustrative, not model output" instead, and Phase 0 must say so.
4. **Seeded demo lots** (seed through the real API as the seed users when in real mode; as fixtures in mock mode; decisions are append-only so never edit rows directly): one lot in each outcome (ACCEPT, REJECT, HOLD, ESCALATE), plus one lot with a system REJECT and a **pending override to ACCEPT** awaiting a different Supervisor, plus optionally one effective override to REJECT. The plan on every demo lot is labeled "test configuration".

## MOBILE / FACTORY-FLOOR REALITY

- Capture uses `<input type="file" accept="image/jpeg,image/png" capture="environment">`.
- **Do not resize, re-encode or compress client-side.** The server limits are 15 MB and 50 megapixels, JPEG and PNG only, and the server makes the canonical working copy itself (FR-CAP-004 to 006, UP-05). Typical 8-12 MB phone photos are within the limit. Client checks are limited to: type is JPEG or PNG, size at most 15 MB; show the reason and the next step if not.
- HEIC or other formats: show the PRD message with the iPhone hint "Settings, Camera, Formats, Most Compatible". Also show the guidance "no faces, no badges".
- Per-file upload progress, retry, retake and withdraw. Show duplicates with a link to the existing image, rate-limit and storage messages as the API returns them. Never show "uploaded" until the backend confirms. Clear offline / weak-network state; nothing is stored on a failed upload.
- Display, boxes and zoom use only the server's **working copy**, so box coordinates match what the reviewer sees. Never show the original file.
- Touch targets at least 44px. Review actions reachable with one thumb. Full-width image. Touch zoom and box placement. No hover-only controls.

## PHASES

### Phase 0: Recon (no code changes)
1. Read the three documents fully. Read repo structure, routes, API client, auth, role handling.
2. Report: stack, existing screens and features to preserve, API endpoints that exist vs PRD section 14 (list each as FOUND or MISSING), detection response shape, role and permission model, decision-engine inputs and outputs, backend mode (real or mock), detector status, document conflicts found, gaps and open questions.
3. Propose a 10-line implementation plan with the time budget applied.
4. Create `PROGRESS.md` and `VERSIONS.md`.

**STOP: Checkpoint A.** Wait for my approval.

### Phase 1: Foundation
1. Design tokens, typography (self-hosted), base theme.
2. Logo and favicon SVGs.
3. Core components: Button, Input, Select, Dropdown, StatusBadge, DecisionBadge, PipelineStepper, DataTable (sort, filter, pagination), MetricCard, Dialog, ConfirmDialog, Tabs, Tooltip, Toast, EmptyState, Skeleton, ErrorState, Timeline, DemoTag.
4. **Login screen:** branded, navy/lime, logo, tagline, uses existing auth. **One generic error for every failure** (no hint whether an account exists). First-login "change temporary password" with the policy reason shown.
5. App shell: collapsible sidebar with role-based visibility: Dashboard (all), Lots (all), Configuration (Admin, Supervisor), Audit log (Supervisor, Admin), User management (Admin). Active indicator, user menu at bottom. Top bar: breadcrumb, demo/environment tag, avatar menu. Admin alert banner area. Mobile: bottom navigation or drawer. Inspection, review and decision live **inside the lot** (tabs: Overview, Plan, Capture, Review, Decision, History and Report), not as separate sidebar items.
6. Role-based route guards. Server remains the authority.
7. Reason-code map `/src/domain/reasonCodes.ts`: the 15 active canonical codes (`HOLD_PLAN_MISSING`, `HOLD_PLAN_INVALID`, `REJECT_CRITICAL_NONVISUAL_FAILED`, `REJECT_LIMIT_REACHED`, `ESCALATE_CRITICAL_UNREVIEWED`, `ESCALATE_UNMAPPED_CLAUSE`, `ESCALATE_CRITICAL_REJECTION_UNCONFIRMED`, `ESCALATE_SECOND_OPINION_REQUESTED`, `HOLD_UNITS_MISSING`, `HOLD_VIEWS_PENDING`, `HOLD_CRITICAL_NONVISUAL_PENDING`, `HOLD_VIEW_STATE_INCONSISTENT`, `HOLD_EVIDENCE_INTEGRITY`, `HOLD_COMPUTE_ERROR`, `ACCEPT_PLAN_MET`). Plain-language text and next step come from the "Resolution" column of PRD section 9.4, written once here and nowhere else. `CALIBRATED_INTERVAL` is inactive in Version 1. An unknown code renders as the raw code, never a guess.

**Done when:** login works for each seed role, shell renders at 375 / 768 / 1280 with no horizontal scroll, navigation respects roles, `/dev/components` shows every component and state.

### Phase 2a: Lot detail, Capture, Review (P0)
1. **Lot detail (control center):** header; plan summary with assumption label; sample progress (units registered, images reviewed, required); status chips (not inferred, retake, escalate); recommendation and final disposition (both lines); history; pipeline stepper. Actions: add unit (garment ID unique in lot), capture, review, compute, open plan, report.
2. **Capture and upload:** unit picker, side picker (front, back, detail), camera or file picker, rules from MOBILE section, per-file progress and result chips, inference job status per image with the manual-review fallback.
3. **Image review:** working copy with box overlay, zoom/pan, previous/next image, proposal list with class, "score (uncalibrated)", flags (BLUR, DARK, LOW_SCORE, UNKNOWN, possible critical) as the API returns them, "not inferred" banner.
4. **Defect confirmation and manual add:** per proposal confirm / edit / reject (optional note on reject); add a defect by hand; fixed type list (hole, dropped stitch, skipped stitch, needle line, oil stain, shade band, other); **zone picker** from the buyer's list and size band as the API supports it (severity is looked up by buyer, type, zone, size band); **severity is server-assigned and read-only**, or "no clause: a person must decide" (`needs_clause` leads to ESCALATE). "Possible critical" highlight, and a "possible critical, need a second opinion" flag.
5. **Finish image:** "Reviewed, defects" or "Reviewed, clean" (reviewer's own confirmation), "needs retake", next image. A refusal shows the reason; a stale 409 shows a reload prompt. Review progress indicator at image level. Keyboard shortcuts for fast review, documented in a tooltip.

**Done when:** on a phone, an inspector can capture an image for a unit and side, see detections (or fall back to manual), review every proposal, add a defect with a zone, and finish the image; state persists via the real API (or is tagged demo).

### Phase 2b: Plan and Decision Center (P0)
1. **Sampling plan (Supervisor; Inspector read-only):** one `n` per plan, `Ac` and `Re` per class (critical, major, minor), `counting_mode` (`highest_class_only` or `every_class`, no default), plan source, assumption label, read-back summary, warnings (`Re != Ac + 1`, `n` mismatch, `n >=` lot size means whole lot), locked after a decision with an explanation. Not set: "Plan not set. Decisions will HOLD".
2. **Decision Center:** outcome; per class `n`, `Ac`, `Re`, count, PASS/FAIL; counting mode; reason codes in words with the next step; applicable buyer clauses; plan assumption label; "uncalibrated" label; model versions; **critical non-visual status** (`pending | done | not_required | failed`, Supervisor sets it, `pending` blocks ACCEPT); explicit **Compute decision** action; decision history; pipeline stepper.
3. **Override and approval:** override panel (Supervisor, not for HOLD or ESCALATE) with final disposition and reason (20 characters minimum); high-risk and pending-approval badges; approve or reject by a different Supervisor with a reason; self-approval refused with an explanation; "Nothing was saved" on a 503; stale decision 409 shows a reload prompt. Explanations for every unavailable action.

**Done when:** all four outcomes, the pending override-to-ACCEPT approval flow (Supervisor A requests, Supervisor B approves, final disposition changes only then) and an immediate override-to-REJECT can be demonstrated with the seeded demo lots and accounts; status is consistent across Lot list, Lot detail, Decision Center, Audit log and Dashboard.

**STOP: Checkpoint B.** Post the demo click path for P0, then wait for my approval.

### Phase 3: P1 screens
- **Dashboard:** open lots, lots on HOLD or ESCALATE, recent decisions, pending overrides awaiting approval (Supervisor); Admin sees system alerts (inference down, disk low, backup failed, reconciler problems, audit gap, login-failure spikes). Any chart is allowed only if computed from real returned data and labeled; otherwise omit.
- **Lot list and create lot:** filters (state, buyer, outcome, date), sort, pagination, outcome badge; create lot (lot code unique, product, color, lot size integer of at least 1, buyer); "No lots match" empty state.
- **Audit log (Supervisor, Admin):** filters (lot, user, action, date), before and after values, denied rows visible, escaped text; export for Admin only.

**Done when:** all three work against real endpoints where they exist, with labeled demo fallbacks.

### Phase 4: P2 screens
- **Report view:** preview, download and generate (Inspector own lots, Supervisor) of the **server-rendered one-page PDF**. The browser never builds the PDF. Show the two-line recommendation and final-disposition wording as the server returns it.
- **Configuration (Admin, Supervisor):** products and buyers (create, edit), buyer clause list **read-only**.
- **User management (Admin):** user table, role, status; create; disable/enable; change role; issue a temporary password (shown once); clear login counters. Last Admin protected and own-role change blocked, with explanations.

**Done when:** each screen is functional, consistent with the design system, and unsupported actions are explicit.

### Phase 5: QA and polish
1. Run the app. Use Playwright (or equivalent) to screenshot every screen at 375, 768 and 1280 and review them.
2. Test: all nav links, filters, image upload (including failure, retry, HEIC, over 15 MB), review actions, each role's UI restrictions (Admin cannot do QC actions, Inspector sees no audit log), decision-state consistency, dialogs, 401 and 429 handling, console errors (must be zero).
3. Confirm no `localStorage` or `sessionStorage` use for tokens or sensitive data, no external requests, no client-side resize.
4. Fix everything found and re-test.
5. Keyboard-only pass and contrast check on P0 screens.
6. Dry-run the demo script end to end, including the manual-review fallback and the two-supervisor approval.

**Done when:** zero console errors, no horizontal scroll, no dead buttons, P0 flow demoable end to end on laptop and phone.

## FINAL REPORT (required)

Concisely:
- What was implemented; which screens are complete.
- What is functional against the real backend (list endpoints used) and which PRD endpoints were MISSING.
- What uses demo, recorded or mock data (list each, with file paths).
- Role-restriction test results.
- Document conflicts and open questions found (high-risk definition, single-Supervisor mode, OV-10, counting mode).
- Known limitations.
- How to run the app, the seed account credentials (demo only), and a 3-minute demo script covering AI inspection, human review, and an explainable decision (including the two-supervisor approval).

## DEMO QUALITY BAR

A judge must clearly see:
1. AI-powered detection on a real garment image, or an honestly labeled recorded result.
2. Human-in-the-loop correction of AI proposals.
3. An explainable, deterministic ACCEPT / REJECT / HOLD / ESCALATE with clear reasoning and accountable overrides.

Begin with Phase 0.

## What changed from v3

- **Upload:** removed client-side resize to 2048px; JPEG/PNG only, 15 MB limit, server-side working copy, HEIC hint.
- **Overrides:** "high-risk ACCEPT" replaced by the PRD definition (override to ACCEPT, second Supervisor); two-line recommendation vs final disposition; 20-character reason; OV-10; server-driven flags.
- **Labels:** "confidence" replaced by "score (uncalibrated)"; plan assumption label; zero proposals is not a pass.
- **Inference:** asynchronous job with manual-review fallback; recorded results limited to labeled demo lots.
- **Security:** real login for the role switcher, no browser storage of tokens, CSRF, 401/429 handling, self-hosted font, pinned dependencies in `VERSIONS.md`, generic login error.
- **Added P0 content:** sample units and sides, zone picker, finish image and retake, sampling plan screen, critical non-visual status, `counting_mode`, reason-code map, Compute decision.
- **Scope trimmed to PRD section 15:** removed notifications, global search, profile page, aggregate reports, clause editor, configurable defect classes, acceptance-rate KPIs; inspection, review and decision moved inside the lot.
- **Pre-flight block** added: backend and detector status must be stated; Phase 0 stops if they are empty.
