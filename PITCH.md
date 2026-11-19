# Lotline — 180-second pitch

**International AI Builders Congress 2026 · IndustrySphere AI (Quality Vision)**
Deadline: 20 Nov 2026 · Demo day: 26 Dec 2026, Daffodil International University, Ashulia.

Format: screen recording of the live app + voice-over. No slides needed; every
claim is shown on screen. Record at 1440×900, browser zoom 100 %, dark theme.

---

## Script (3:00)

### 0:00–0:15 — The problem, in one sentence

**VO:** "In knitwear, a lot of 480 t-shirts is accepted or rejected on a sample
of eight. Get it wrong and you either ship defects to a buyer or scrap good
product. Today that judgement lives in a paper sheet and a supervisor's memory."

**On screen:** dashboard, six lots, five different outcomes.

### 0:15–0:30 — The product and its invariant

**VO:** "Lotline is the acceptance decision you can defend. And it is built on
one rule that never breaks: **AI proposes, humans confirm, the rule decides.**
The AI is never allowed to approve a lot."

**On screen:** point at the footer strip on every page: *"The AI never approves a
lot."* Then open **How it works**.

### 0:30–0:50 — AI proposes

**VO:** "A photo comes in from the inspection table. An on-device autoencoder
learns what clean knit texture looks like — no defect labels — and flags what
doesn't fit. Here it found a hole. It gives a box and a type guess. It does not
give a count, a verdict, or a way to approve."

**On screen:** `LT-2026-019` → Review → the red box on the hole; toggle the
attention map on and off once.

### 0:50–1:15 — Humans confirm

**VO:** "The inspector is the authority. Confirm the hole, set the zone — that
maps to the buyer's clause — and reject the model's second guess, which is
noise. Severity comes from the buyer's clause list after confirmation, never
from the model. Notice the server refuses to close the view while a proposal is
unanswered."

**On screen:** open *Confirm defect*, pick zone II, save. Reject the second
proposal. Show the amber banner, then close the view.

### 1:15–1:40 — The rule decides

**VO:** "Now the decision. A pure function — no model, no database, no network —
counts only human-confirmed defects, compares them to the entered Ac/Re, and
returns REJECT with one reason code: the critical count reached its rejection
number. Every recompute appends a new row; nothing is ever edited."

**On screen:** Decision → **Recompute now** → `REJECT_LIMIT_REACHED`; scroll the
counts table (critical 1 / Ac 0 / Re 1 = FAIL), the snapshot hash, the history.

### 1:40–2:00 — The failure paths are the product

**VO:** "Anyone can draw a box. The value is what happens when evidence is
missing. No plan — the engine holds; it will not guess. A confirmed defect with
no buyer clause — escalate to a human. Fewer garments than the plan — hold.
Open critical proposal — escalate. Fourteen failure reason codes plus one ACCEPT, one precedence order:
plan, reject, escalate, hold, accept."

**On screen:** flip through `LT-2026-018` (HOLD_PLAN_MISSING), `LT-2026-017`
(ESCALATE_UNMAPPED_CLAUSE), `LT-2026-016` (HOLD_UNITS_MISSING), `LT-2026-015`
(ACCEPT_PLAN_MET).

### 2:00–2:20 — Audit, override, two-person control

**VO:** "Every state change is an append-only audit event. A supervisor can
override an ACCEPT or a REJECT — but an override to ACCEPT needs a second,
different supervisor. The admin cannot override at all. The final disposition
shows as overridden on every screen and in the PDF."

**On screen:** Audit log (scroll), then a decision with an override banner if
present, then `LT-2026-014` report → **Download PDF**.

### 2:20–2:40 — Why this wins here

**VO:** "Bangladesh ships 80-plus percent of its export earnings from garments.
RMG quality inspection is a 4-million-worker workflow still running on paper.
Lotline is Bangla-first, runs on a CPU, keeps evidence in-country, and does not
ask a factory to trust a black box — it asks them to trust a rule they can read."

**On screen:** switch the UI to **বাংলা**; show the same lot, same decision, same
report.

### 2:40–3:00 — Close

**VO:** "Thirty-six deterministic engine tests in a suite of seventy-nine.
The AI proposes. The human confirms. The rule decides. Lotline — quality you can
defend."

**On screen:** `python -m pytest -q` output (36 passed) and the README's
invariant section.

---

## Shot list (record in this order, one browser window)

| # | URL | Action | Length |
|---|---|---|---|
| 1 | `/` | slow scroll of six lot cards | 8 s |
| 2 | `/how` | hold on pipeline strip | 8 s |
| 3 | `/lots/6` | hold on garments + outcome | 6 s |
| 4 | `/review/55` | toggle attention map, confirm zone II, reject 2nd, close view | 40 s |
| 5 | `/lots/6/decision` | Recompute, scroll counts + reasons | 20 s |
| 6 | `/lots/5`, `/lots/4`, `/lots/3`, `/lots/2` | one beat each on the outcome band | 20 s |
| 7 | `/audit` | scroll | 12 s |
| 8 | `/lots/1/report` | Download PDF, open it | 15 s |
| 9 | `/lang/bn` | same lot in Bangla | 15 s |
| 10 | terminal | `pytest -q` | 8 s |

Reset before recording: `python -m app.seed --force` (restores the open critical
proposal on `LT-2026-019`).

---

## Q&A cheat sheet

**"Is the model accurate?"**
Precisely, and on one domain only. The trained detector scores **mAP@0.5 0.95 on
42 held-out BDFD9 test photos** and **0.75 on 68 validation photos**. Every photo
comes from the same four Bangladeshi factories, so neither number is a
new-factory estimate. Only **one** clean image is in that test set, so we do not
quote a false-positive rate. Calibration was fitted on validation and **rejected**
because ECE rose 0.106 → 0.118; runtime scores are raw, not probabilities. The
deployed demo runs the unsupervised numpy baseline unless the ONNX artifact is
shipped, and `/readyz` says which one is scoring. A human confirms every box
before the engine sees it, so no accuracy number can approve a lot.

**"What stops the AI approving a bad lot?"**
Architecture. The engine cannot import a model; a test parses its AST to prove
it. Proposals are not evidence; only human-confirmed defects are counted. The
only ACCEPT code requires a complete sample with every view reviewed and no
reject number reached.

**"Where is the AQL table?"**
Deliberately absent. We do not reconstruct ISO 2859-1. The plan is entered from
a licensed standard or the buyer's order and stored with a source reference; the
demo plan is labelled an invented placeholder. `Re = Ac + 1` is enforced.

**"Why will a factory use it?"**
It replaces a paper sheet with a defensible record: photo, box, confirmation,
count, rule, hash, signature. Bangla-first, CPU-only, works on the phone the
inspector already carries.

**"Business model?"**
Per-factory subscription priced per inspection line, plus buyer-side audit seats;
the buyer pays for the audit trail, the factory pays for the speed. Pilot target:
three knitwear units in Gazipur/Narayanganj, one buyer clause pack each.

**"Data sovereignty?"**
On-prem or in-country hosting, no third-party vision API, no worker biometrics,
evidence retained in the customer's jurisdiction, exportable audit CSV.

---

## One-page summary (paste into the submission form)

**Lotline — auditable knitwear lot acceptance.**
AI proposes defects, an inspector confirms them, a deterministic engine makes the
call. The AI can never approve a lot: the engine is a pure function that only
sees human-confirmed counts and the entered sampling plan.

**Problem.** A 480-piece lot is judged on an 8-piece sample. The decision is high
value, low evidence, and usually undocumented. Buyers cannot audit it; factories
cannot defend it.

**Product.** Phone capture → on-device vision proposals → one-tap human review
with buyer clause mapping → deterministic ACCEPT/REJECT/HOLD/ESCALATE with a
canonical reason code → one-page PDF with snapshot hash and signatures →
append-only audit log. Bangla and English. CPU only.

**Differentiators.** (1) The AI is structurally incapable of approving a lot.
(2) Fifteen reason codes and a fixed precedence make every outcome explainable.
(3) Two-person override control with append-only history. (4) Honest model card:
uncalibrated, staged-data evaluation, no fabricated AQL table. (5) Bangla-first
for the 4M-worker RMG inspection workforce.

**Traction evidence in the build.** Six seeded lots covering four distinct
outcomes (ACCEPT, REJECT, HOLD, ESCALATE) and six reason codes; 70 staged photos;
32 baseline model proposals; 30 reviewed predictions (4 confirmed, 26 rejected);
180+ audit events; 36 deterministic engine tests passing in 40 ms; working PDF.

**Market.** Bangladesh RMG: 4,000+ factories, 4M+ workers, ~80 % of export
earnings. Adjacent: Sri Lanka, Vietnam, India, Turkey knitwear. Buyer-side audit
seats are a second revenue line.

**Ask.** Pilot with three knitwear units and one buyer clause pack; calibrate the
detector on their labelled holdout and publish the model card.
