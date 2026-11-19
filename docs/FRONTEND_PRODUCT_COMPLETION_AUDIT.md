# LOTLINE — Frontend Product Completion & Production UX Audit

**Date:** November 18, 2026  
**Auditor Roles:** Senior Frontend Engineer, Enterprise SaaS Product Designer, HCI Specialist, Frontend QA Engineer  
**Scope:** Frontend inspection of all 13 screens across `templates/`, `static/css/`, and `static/js/`  
**Architecture Boundary:** Jinja2 + Vanilla JavaScript + CSS Design System (FastAPI backend contracts strictly preserved)  
**Baseline Test Matrix:** 57 passing unit & regression tests  

---

## 1. Executive Summary

This comprehensive audit evaluates the production readiness of LOTLINE's frontend interface. Following the visual redesign to a Linear/Stripe-inspired aesthetic, this audit systematically evaluates every interactive element, user input, state transition, bilingual string, accessibility indicator, and factory-floor usability heuristic across all 13 operational screens.

The frontend is structurally sound, with no client-side decision logic and strict adherence to backend contracts. However, critical frontend completion opportunities have been identified:
1. **Interactive Feedback & State Transitions:** Several buttons and forms lacked immediate client-side feedback (busy/loading indicators, file upload drag-and-drop zones, live image preview before submission).
2. **Actionable Navigation:** Dashboard KPI metric cards were static informational displays rather than actionable query shortcuts to filtered lot views.
3. **Data Table Enhancements:** While `static/app.js` contained a progressive table sorting and pagination engine, table headers on several key screens (`lots.html`, `review_queue.html`) lacked the requisite `data-table` and `th[data-sort]` attributes.
4. **Error Prevention & Form Polish:** Password visibility toggles, dynamic override risk warnings, Ac/Re client-side invariant helpers, and one-click clipboard copying for generated temporary credentials were missing.
5. **Bilingual Completeness:** Isolated microcopy strings lacked Bengali localization or suffered ascender/descender boundary crowding.

---

## 2. Screen-by-Screen Product Audit

### Screen 1: Login (`templates/login.html`)

* **Current Behavior:**
  * Displays split-screen layout with value proposition on the left and sign-in card on the right.
  * Provides quick-access demo sign-in for Inspector, Supervisor A, Admin (via `<a>`), and Supervisor B (via `<form>` POST).
  * Password input is standard type `password` without visibility toggling.
  * Form inputs do not autofocus on initial landing.
* **Evidence:**
  * Source: `templates/login.html` lines 50–60.
  * Inspection: Users entering credentials manually cannot verify complex seeded passwords (e.g. `QualityFloor2026!`) without unmasking.
* **Required Frontend Changes:**
  1. Add an accessible "Show/Hide Password" toggle button with SVG eye icon inside the password field.
  2. Add `autofocus` attribute to `#email` input.
  3. Ensure password input toggle preserves field focus and updates `aria-label` dynamically (`Show password` / `Hide password`).
* **Backend Dependency:** None. Standard POST `/login` endpoint contract preserved.
* **Acceptance Criteria:**
  * Clicking the eye button toggles password input type between `password` and `text`.
  * Keyboard navigation allows toggling via Enter/Space.
  * Eye icon changes state and updates accessible label.

---

### Screen 2: Dashboard (`templates/dashboard.html`)

* **Current Behavior:**
  * Top KPI cards display Open Lots, HOLD count, ESCALATE count, and Decided count.
  * Cards are static and non-interactive; clicking them does not navigate.
  * Client-side search and pills filter only the top 6 lots supplied to the dashboard (`cards[:6]`).
  * If a searched lot is not among the top 6, the empty match state provides no pathway to search the full directory.
  * High-risk override awaiting banner displays pending approvals with a "Review & Decide" link.
* **Evidence:**
  * Source: `templates/dashboard.html` lines 18–54 and 281–283.
* **Required Frontend Changes:**
  1. Make the 4 top KPI metric cards actionable links (`href="/lots?state=open"`, `href="/lots?outcome=HOLD"`, `href="/lots?outcome=ESCALATE"`, `href="/lots?state=decided"`).
  2. In `#lotEmptyMatch`, add a direct link: *"Looking for another lot? Search all lots in the Directory →"*.
  3. Add hover micro-interactions (`transform: translateY(-1px)`) to metric cards indicating clickability.
* **Backend Dependency:** None. Backend `/lots` route already accepts query params `state` and `outcome`.
* **Acceptance Criteria:**
  * Clicking the HOLD metric card navigates to `/lots?outcome=HOLD`.
  * Empty search state offers a one-click redirect to full directory search.

---

### Screen 3: Lots Management (`templates/lots.html`)

* **Current Behavior:**
  * Displays a full table of inspection lots with filters (Search query `q`, Status `state`, Outcome `outcome`).
  * Displays Two-Line Disposition (`Rec:` and `Final:`).
  * Table sorting is inactive; clicking column headers does nothing.
* **Evidence:**
  * Source: `templates/lots.html` lines 77–90. The `<table>` lacks `data-table` and `th[data-sort]`.
* **Required Frontend Changes:**
  1. Add `data-table` to the table container and `data-sort` attributes to sortable column headers (Lot Code, Buyer, Product, Size).
  2. Implement visual sort direction chevrons (`ascending` / `descending`) via CSS.
* **Backend Dependency:** None. Client-side DOM sorting via existing `app.js` table engine.
* **Acceptance Criteria:**
  * Clicking "Lot Code" sorts rows alphabetically A–Z / Z–A.
  * Clicking "Lot Size" sorts rows numerically.
  * Header displays `aria-sort` and visual indicator.

---

### Screen 4: Create Lot (`templates/lot_new.html`)

* **Current Behavior:**
  * Form collects Lot Code, Color, Buyer, Product, Lot Size, and Selection Method.
  * Submits via POST `/lots/new`.
  * Displays error alert if `?err=exists` or `?err=invalid`.
  * No visual client-side indicator while form submission is in flight.
* **Evidence:**
  * Source: `templates/lot_new.html` lines 47–123.
* **Required Frontend Changes:**
  1. Auto-capitalize input on `#lot-code` as the user types.
  2. Enforce minimum size validation ($N \ge 1$) client-side with descriptive validation message.
  3. Ensure submit button displays loading state during submission.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * User typing `lt-2026-025` sees uppercase `LT-2026-025`.
  * Form cannot be submitted with size $0$ or negative.

---

### Screen 5: Lot Cockpit (`templates/lot.html`)

* **Current Behavior:**
  * Displays overall lot status, units progress, views progress, and decision summary.
  * Grid of units with view chips (`Front`, `Back`) linking to review or capture.
  * In the Critical Non-Visual Check card, if the lot is decided and no note was written, only the status pill is visible without descriptive contextual confirmation.
* **Evidence:**
  * Source: `templates/lot.html` lines 330–362.
* **Required Frontend Changes:**
  1. In the Critical Non-Visual Check card, show clear confirmation text when check is completed (`Status recorded: [done/not_required/failed]`) even when notes are empty.
  2. Add smooth scrolling to `#history` anchor with visual highlight pulse.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Non-visual card clearly displays audit status in both active and decided lot states.
  * Clicking the "History" tab smoothly scrolls to the timeline.

---

### Screen 6: Sampling Plan (`templates/plan.html`)

* **Current Behavior:**
  * Supervisor configures sample size $n$, counting mode, and per-class limits (Critical, Major, Minor).
  * JavaScript automatically sets $Re = Ac + 1$ on input change.
  * If a user manually changes $Re$ to be invalid ($Re \ne Ac + 1$), no client-side error prevents submission.
* **Evidence:**
  * Source: `templates/plan.html` lines 125–130; `static/app.js` lines 495–504.
* **Required Frontend Changes:**
  1. Add client-side validation constraint: If $Re \le Ac$, show instant HTML5 custom validity error: *"Rejection limit Re must be greater than acceptance limit Ac (Re = Ac + 1 for single sampling)"*.
  2. Add informative visual pill indicating single-sampling compliance.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Submitting invalid Ac/Re triggers native browser validation before form post.
  * Valid Ac automatically recalculates Re.

---

### Screen 7: Photo Capture (`templates/capture.html`)

* **Current Behavior:**
  * Allows registering garment units and uploading photos for Front and Back views.
  * Filter controls allow jumping to garments and filtering by Front/Back side.
  * Upload forms use standard `<input type="file">`.
  * No drag-and-drop zone; no client-side thumbnail preview before submitting.
* **Evidence:**
  * Source: `templates/capture.html` lines 220–236.
* **Required Frontend Changes:**
  1. Transform the upload area into a drag-and-drop target with visual dashed border and active drag-hover highlight.
  2. When a file is chosen, display an instant client-side thumbnail preview and file size pill before upload submission.
  3. Retain native camera trigger (`capture="environment"`) for mobile devices.
* **Backend Dependency:** None. Standard multipart form submission preserved.
* **Acceptance Criteria:**
  * Dragging an image over the upload box highlights the drop zone.
  * Selecting a file renders a local preview image in the card before submission.

---

### Screen 8: Review Queue (`templates/review_queue.html`)

* **Current Behavior:**
  * Displays table of views awaiting review, categorized by priority (Critical routing, Manual, Review).
  * Has "Continue Review" button pointing to first unreviewed image.
  * Table lacks column sorting capabilities.
* **Evidence:**
  * Source: `templates/review_queue.html` lines 36–84.
* **Required Frontend Changes:**
  1. Add `th[data-sort]` attributes to Garment Code, Side, Status, and Priority.
  2. Provide clear visual cues for empty queue with one-click navigation to Decision Center.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Table rows can be sorted by priority or garment code.

---

### Screen 9: Image Review (`templates/review.html`)

* **Current Behavior:**
  * Full pan/zoom image inspection viewer with overlaid defect proposal bounding boxes.
  * Attention map toggle displays synthetic heat overlay.
  * Clicking an image places coordinates into manual defect form.
  * When clicking the image to add a defect, the form (`#manualAddCard`) is below the viewport, requiring the inspector to scroll down.
  * Keyboard shortcuts dialog available (`?` / shortcuts button).
* **Evidence:**
  * Source: `templates/review.html` lines 188–250; `static/app.js` lines 345–358.
* **Required Frontend Changes:**
  1. When an inspector clicks on the image to place a manual defect box, automatically smooth-scroll to `#manualAddCard` and focus the Defect Type dropdown.
  2. Enhance box selection: Clicking a proposal card should visually emphasize the corresponding box on the canvas with an active glow ring.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Clicking the garment image places the marker and scrolls smoothly to the defect specification form.
  * Keyboard shortcuts (`+`, `-`, `0`, `c`, `x`, `]`, `[`) function reliably.

---

### Screen 10: Decision Center (`templates/decision.html`)

* **Current Behavior:**
  * Two-Line Disposition banner displays System Recommendation vs Final Disposition.
  * Displays confirmed defect counts against $Ac/Re$ thresholds.
  * Supervisor override form requires 20-character reason with live counter.
  * Warning note for high-risk overrides is statically rendered based on initial load rather than reacting to user dropdown selection.
* **Evidence:**
  * Source: `templates/decision.html` lines 387–417; `static/app.js` lines 485–493.
* **Required Frontend Changes:**
  1. Add dynamic change listener to `#override-disposition`:
     * If user selects `OVERRIDE_ACCEPT`, display high-risk warning (2nd supervisor required).
     * If user selects `OVERRIDE_REJECT`, display immediate-effectiveness notice.
  2. Disable submit button until character counter reaches $\ge 20$ characters.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Changing override target dynamically updates the compliance banner.
  * Submit button is enabled only when minimum character threshold is satisfied.

---

### Screen 11: Reports (`templates/report.html`)

* **Current Behavior:**
  * Official one-page knitwear inspection certificate sheet.
  * Displays Two-Line Disposition, defect counts table, evidence SHA-256 hashes, and supervisor signatures.
  * Print button triggers `window.print()`; PDF download link targets `/lots/{id}/report.pdf`.
* **Evidence:**
  * Source: `templates/report.html` lines 10–27.
* **Required Frontend Changes:**
  1. Ensure `@media print` styles hide top navigation, breadcrumb, and action buttons cleanly.
  2. Verify all table borders and typography render with sharp contrast on printed paper.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Certificate prints on a single standard A4 sheet without unwanted page breaks.

---

### Screen 12: Audit Log (`templates/audit.html`)

* **Current Behavior:**
  * Append-only event stream (time, actor, action, entity, payload).
  * Payload `<details>` shows JSON strings.
  * Text search filters actions and actors via GET form.
* **Evidence:**
  * Source: `templates/audit.html` lines 97–110.
* **Required Frontend Changes:**
  1. Add syntax-highlighted / pretty-printed formatting to JSON audit payloads within `<pre>` blocks for readability.
  2. Add one-click "Expand All Payloads" / "Collapse All" toggle button for rapid audit inspection.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * JSON payloads are cleanly formatted with 2-space indentation.

---

### Screen 13: Admin Console (`templates/admin.html`)

* **Current Behavior:**
  * Tabs: Users, Models, Health, Clauses.
  * When a temporary password is generated (`?temp=...`), it displays in a green note without a copy button.
  * User creation form validates minimum 15 characters.
* **Evidence:**
  * Source: `templates/admin.html` lines 21–35.
* **Required Frontend Changes:**
  1. Add a 1-click "Copy Password" button next to the generated temporary password with visual "Copied!" tooltip feedback.
  2. In the Clauses tab, make the quality specifications table sortable with `data-table`.
* **Backend Dependency:** None.
* **Acceptance Criteria:**
  * Clicking "Copy" copies the password to clipboard and shows brief success confirmation.

---

## 3. Prioritized Implementation Plan

| Priority | Task | Target Files | Impact |
|---|---|---|---|
| **P0** | Password visibility toggle on Login | `templates/login.html`, `static/app.js`, `static/app.css` | Accessibility & Error Recovery (WCAG AA) |
| **P0** | Actionable Dashboard Top KPIs | `templates/dashboard.html` | Efficiency of Use (Nielsen H7) |
| **P1** | Drag & Drop photo upload + instant preview | `templates/capture.html`, `static/app.js`, `static/app.css` | Factory-floor operational ergonomics |
| **P1** | Table sorting on Lots & Queue | `templates/lots.html`, `templates/review_queue.html`, `static/app.css` | Supervisor & Inspector workflow speed |
| **P1** | Image review click-to-scroll to defect form | `static/app.js`, `templates/review.html` | Minimizes unnecessary scrolling in review |
| **P2** | Dynamic override risk banner & button gating | `templates/decision.html`, `static/app.js` | Error prevention & compliance transparency |
| **P2** | 1-click clipboard copy for Admin temp passwords | `templates/admin.html`, `static/app.js` | Administrator productivity |
| **P2** | Sampling plan client-side Ac/Re invariant validation | `templates/plan.html`, `static/app.js` | Prevents invalid plan form submissions |

---

## 4. Acceptance Sign-Off Criteria

1. All 13 screens verified in browser rendering with zero console errors.
2. 100% preservation of FastAPI routes, business logic, and database state.
3. 57 passing tests in regression suite maintained (`pytest -q`).
4. English and Bengali typography and text alignment preserved without clipping.

