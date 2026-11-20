# Submission answers — International AI Builders Congress 2026

Paste-ready text for the preliminary form. Replace `<...>` placeholders on the
day; everything else is final and consistent with `docs/MODEL_CARD.md`.

## Basics

- **Project title:** Lotline — AI proposes, humans confirm, the rule decides
- **Team:** Lotline (4 members; ML/data, backend, frontend, product)
- **Category:** Industry / Manufacturing & Quality
- **Demo URL:** `<RENDER_URL>`
- **Video (180 s):** `<YOUTUBE_OR_DRIVE_LINK>`
- **Repository:** decide on the day — public `https://github.com/hridewelx/ai-builders-congress`
  shows the code and the honest model card; private means judges rely on the
  video and the live demo alone.

## One line

Lotline turns a factory's paper AQL sheet into a defensible record: photos, boxes,
human confirmations, a deterministic rule, and a signed PDF — in Bangla, on a CPU.

## Short description (≈120 words)

Garment factories in Bangladesh decide whether a lot ships using random sampling
and a rule table, but the evidence behind that decision is a paper sheet nobody
can audit. Lotline keeps the rule and fixes the evidence. Photos are captured on
the phone an inspector already carries; a server-side model proposes defect boxes;
an inspector confirms or rejects each proposal in Bangla; and a deterministic
engine — one pure function, fifteen reason codes — returns ACCEPT, REJECT, HOLD or
ESCALATE. The AI never approves a lot, and it structurally cannot: the engine has
no access to a model, and a test parses its imports to prove it. Every decision,
override and approval is append-only, hashed, and exported as a PDF that cites the
plan, the counts, the reason codes and the reviewer.

## What is genuinely AI-native

- The model is a **proposer**, not an approver. Its output is an untrusted input to
  a human review step; unconfirmed proposals are never counted as evidence.
- The trained detector is a supervised Faster R-CNN (MobileNetV3-Large FPN) over
  four fabric-defect classes, trained on **BDFD9** (Mendeley, CC BY 4.0, 1,088
  photos from four Bangladeshi knit factories), evaluated on BDFD9's **own
  held-out split**: mAP@0.5 **0.9474** on 42 held-out test photos and **0.7479** on
  68 validation photos.
- The demo also runs an **unsupervised numpy baseline** with no model file at all,
  so the product works on a CPU-only host; `/readyz` reports which backend is live.
- Calibration was fitted on validation and **rejected** because ECE rose
  (0.106 → 0.118). Runtime scores are raw, and the UI says so.

## Responsible AI, stated plainly

- Same four factories in train and test: neither number is a new-factory estimate.
- One clean image in the test split, so no false-positive rate is quoted.
- `needle_line` is an approximate mapping from BDFD9's `Vertical LineMark`; the
  reviewer can change the type.
- Critical non-visual checks (needle, metal) cannot be photographed and are entered
  by a human with a note.
- No claim exceeds `docs/MODEL_CARD.md`; the leakage probe is published as
  **inconclusive**, with its own train-vs-train control at 54 %.

## Judge quick path (60 seconds)

1. `https://<app>.onrender.com` → **Continue as guest** — one click, no signup,
   no OAuth app needed. It opens the staged demo read-only, so a judge can walk
   the whole product and cannot damage the data the next judge sees. (For full
   rights: `/demo/supervisor`.)
2. Open lot **LT-2026-019** → it shows `ESCALATE_CRITICAL_UNREVIEWED`: an
   unreviewed critical proposal blocks a decision.
3. Review one photo, confirm or reject the box, close the view.
4. `/lots/6/decision` → recompute → the reason codes and counts update.
5. `/lots/1/report` → PDF with hashes, plan, counts and signatures.
6. `/lang/bn` → the same screens in Bangla.

## Rubric map

| Criterion | Where it shows |
|---|---|
| Innovation & AI-native design | Proposal/confirmation boundary enforced by the engine's import graph |
| Technical excellence | 186 tests, 36 of them on the engine; ONNX parity 0.7479 vs 0.7475 on validation |
| Business value | Paper sheet → auditable record; no new hardware; Bangla-first |
| Global scalability | Any sampling plan entered from a licensed standard; CPU-only; SQLite → Postgres for a pilot |
| Responsible AI & presentation | Model card, rejected calibration, inconclusive leakage probe, two-person override approval |
