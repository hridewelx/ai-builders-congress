# Lotline

**AI proposes. Humans confirm. The rule decides.**

Lotline is a working, auditable knitwear **lot-acceptance** system. A photo of a
garment goes in. A vision model on the server proposes defect boxes. An inspector
confirms, corrects or rejects each proposal. A deterministic sampling engine — a
pure function with no model inside it — then returns **ACCEPT · REJECT · HOLD ·
ESCALATE**, with the exact reason code and the exact rule that produced it.

Built for the **International AI Builders Congress 2026 · IndustrySphere AI
(Quality Vision)** challenge, Dhaka.

| Login | Dashboard | Lots |
|---|---|---|
| ![](docs/screens/login.png) | ![](docs/screens/dashboard.png) | ![](docs/screens/lots.png) |

| Lot overview | Human review | Decision |
|---|---|---|
| ![](docs/screens/lot.png) | ![](docs/screens/review.png) | ![](docs/screens/decision.png) |

| Report | Audit | Admin |
|---|---|---|
| ![](docs/screens/report.png) | ![](docs/screens/audit.png) | ![](docs/screens/admin.png) |

| How it works | Bangla |
|---|---|
| ![](docs/screens/how.png) | ![](docs/screens/lot-bn.png) |

---

## The one invariant

> The AI never approves a lot.

This is enforced structurally, not by policy text:

1. `app/domain/engine.py` is a pure function. It imports only `hashlib` and `json`
   (there is a test that parses its AST and fails if anything else appears).
   It cannot call a model, a database or the network.
2. The engine never sees a proposal. It sees **human-confirmed defects**, the
   entered sampling plan, and completeness evidence. A bounding box on its own
   counts for nothing.
3. Every failure path terminates in `HOLD`, `ESCALATE` or `REJECT`. The only
   path to `ACCEPT` is *complete sample + every view reviewed + zero reject
   numbers reached*. `ACCEPT_PLAN_MET` is the only ACCEPT reason code.
4. An unanswered critical proposal escalates; it never quietly disappears.
   Closing a view while a proposal is still open is refused by the server.

| Layer | Who decides | Can it approve a lot? |
|---|---|---|
| Vision model (`app/services/vision.py`) | proposes boxes + a type guess | **no** |
| Inspector | confirms / edits / rejects each box, marks the view | **no** |
| Supervisor | sets the plan, second-reviews rejected criticals, overrides | **only via an audited two-person override** |
| Engine (`app/domain/engine.py`) | counts confirmed defects, compares Ac/Re, returns the outcome | **this is the only decision-maker** |

---

## Run it (2 minutes, no Docker)

The demo has two processes: the **FastAPI backend** (API + deterministic engine)
and the **React + TypeScript + Vite** single-page app. Next.js is deliberately
not used; see `lotline_research_prompt_v3.md` §D1 for the reasoning.

```bash
# terminal 1 — backend
python -m app.seed          # 6 lots, 70 staged photos, ~30 s (first run fits the autoencoder)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8077

# terminal 2 — React SPA (proxies /api and /static to 127.0.0.1:8077)
npm --prefix frontend install
npm --prefix frontend run dev
```

Or with make: `make seed`, `make run`, `make test`, `make data`, `make reset`
(or `run.bat` / `./run.sh` for the backend).

Open <http://127.0.0.1:5173> and press **Inspector**, **Supervisor** or
**Admin** for one-click demo access (no password typing during a pitch).
The seeded password is `QualityFloor2026!`.

The legacy server-rendered pages remain at <http://127.0.0.1:8077> as a
reference implementation; the React app in `frontend/` is the current UI and
talks only to the JSON API under `/api`.

```bash
python -m pytest -q         # 186 tests, ~3 s
python -m ruff check app    # import order, undefined names, dead code
npm --prefix frontend run build   # tsc -b + vite production build
```

`python -m app.seed --force` rebuilds the demo from scratch.

---

## The 90-second demo path

| Step | Screen | What the judge sees |
|---|---|---|
| 1 | Dashboard | six lots, five different outcomes, zero AI approvals |
| 2 | `LT-2026-019` | an open lot: AI proposed a hole, nobody has confirmed it → decision is **ESCALATE_CRITICAL_UNREVIEWED** |
| 3 | Review | the hole is boxed in red (critical routing); confirm it, correct its type/zone, reject the noise proposal |
| 4 | Decision → Recompute | **REJECT_LIMIT_REACHED**, critical count 1 ≥ Re 1, snapshot hash, append-only history |
| 5 | Report | one page PDF: plan source, counts, reason codes, evidence, signatures, honest limits |
| 6 | `LT-2026-014` | AI proposals that humans **rejected** — the AI does not win arguments |
| 7 | `LT-2026-017` | Sakura Apparel clause map is missing an oil-stain zone → **ESCALATE_UNMAPPED_CLAUSE** |
| 8 | `LT-2026-018` | no plan → **HOLD_PLAN_MISSING** (the engine refuses to guess) |
| 9 | Audit | 100+ append-only events: who did what, to which entity, when |
| 10 | বাংলা | the whole UI in Bangla, same logic and screens; PDF labels stay English |

---

## What is real, and what is not

Honesty is part of the product. Every limitation below is also printed in the
UI and in the PDF report.

**Real**
- Two model paths. The seeded demo history uses a genuine unsupervised
  autoencoder (numpy, in-process, CPU, ~0.4 s/photo), trained only on **clean
  synthetic knit patches** and localising defects by reconstruction residual.
  New uploads use a trained Faster R-CNN (MobileNetV3-FPN, ONNX, CPU) supervised
  on **BDFD9 factory fabric plus staged panels**; it proposes boxes and classes
  only.
- The engine, the counting modes, the precedence order, `Re = Ac + 1`
  validation, the append-only decision/override/audit model, Argon2id + CSRF +
  server-side sessions, the PDF report: all production-shaped, not mocked.
- Demo photos are generated procedurally (knit texture + staged defects).
  BDFD9 images are used only for detector training/evaluation, never as buyer,
  worker or inspection records.

**Not real (stated in the UI)**
- The autoencoder's scores are anomaly residuals, not probabilities. For the
  trained detector, temperature scaling was fitted on validation and **rejected**
  because it increased ECE (0.106 → 0.118), so the runtime keeps raw scores and no
  calibrated-probability claim is made.
- The trained detector is a **fabric close-up** detector, not finished-garment
  inspection. BDFD9 covers four Bangladeshi factories and four mapped classes;
  performance on another factory or line is unmeasured.
- Evaluation is on a held-out official BDFD9 test split; see
  `docs/MODEL_CARD.md` for the current numbers. Do not quote them as a
  production guarantee.
- `needle_line` is an **approximate** mapping from BDFD9's `Vertical LineMark`;
  the reviewer can change the type.
- Critical **non-visual** defects (needle, metal) cannot be photographed; a
  supervisor records them separately.
- Sampling randomness is **self-declared**; the software cannot verify a draw.
- The demo plan (`n=8`, critical 0/1, major 1/2, minor 2/3) is an **invented
  placeholder**, labelled `DEMO PLAN — not from any standard`. No ISO 2859-1 /
  ANSI Z1.4 table is reconstructed and no percentage allowance is claimed.
- SQLite + in-process vision replaces the production Postgres / InferenceWorker
  / Vision-container topology, so judges can click through without Docker.
  The schema, the privilege split and the audit model follow the design docs.

---

## Architecture (demo)

```
browser ── React + TypeScript + Vite SPA (React Router · TanStack Query)
              │  /api (JSON) · /static (theme, fonts, photos)
              ▼
         FastAPI (app/main.py)
                     │  Argon2id · server sessions · CSRF · Origin check · role gate
                     ├──▶ app/api/                 (JSON API: auth · lots · capture · review · decisions · admin · system)
                     ├──▶ app/web/routes/          (legacy Jinja reference screens, kept for tests)
                     ├──▶ app/services/review.py ──▶ app/domain/engine.py  (pure, deterministic)
                     │        │                         └─ 15 reason codes, precedence
                     │        ├──▶ app/core/db.py          (SQLite WAL, append-only decisions)
                     │        └──▶ app/services/report.py  (one-page PDF, snapshot hash)
                     ├──▶ app/services/vision.py  (numpy autoencoder, in-process)
                     └──▶ app/core/security.py    (Argon2id · sessions · CSRF · login delay)
```

Production topology from `SYSTEM_DESIGN_v1_2.md` §11 — Proxy → API →
InferenceWorker (no table privileges) → Vision container (no database) →
PostgreSQL, each on its own network — is documented in `docs/` and summarised
on the **How it works** screen. This build collapses it into one process for a
2-minute judge demo.

### Decision precedence

```
plan (missing/invalid) → REJECT → ESCALATE → other HOLD → ACCEPT
```

15 canonical reason codes, e.g. `HOLD_PLAN_MISSING`, `HOLD_PLAN_INVALID`,
`REJECT_CRITICAL_NONVISUAL_FAILED`, `REJECT_LIMIT_REACHED`,
`ESCALATE_CRITICAL_UNREVIEWED`, `ESCALATE_UNMAPPED_CLAUSE`,
`ESCALATE_CRITICAL_REJECTION_UNCONFIRMED`, `ESCALATE_SECOND_OPINION_REQUESTED`,
`HOLD_UNITS_MISSING`, `HOLD_VIEWS_PENDING`, `HOLD_CRITICAL_NONVISUAL_PENDING`,
`HOLD_VIEW_STATE_INCONSISTENT`, `HOLD_EVIDENCE_INTEGRITY`,
`HOLD_COMPUTE_ERROR`, `ACCEPT_PLAN_MET`.

### Counting modes

- `highest_class_only` — a garment with several defects counts **once**, in its
  highest class.
- `every_class` — a garment counts once in **every** class it has.

The mode is part of the plan, printed on the report, and stored with the
decision, because it changes the count.

### Overrides (DL-02)

- Only a **Supervisor** can override, and only an `ACCEPT` or `REJECT`.
- `OVERRIDE_ACCEPT` needs a **second, different Supervisor** to approve.
- `Admin` cannot override. The Admin is for accounts, model activation, audit.
- Overrides never edit the decision row. They append an `override` row and the
  final disposition becomes `ACCEPT (overridden)` — visible on every screen and
  in the PDF.

---

## Security & responsible AI

- Argon2id password hashing; 15+ character policy with context-word rejection.
- Server-side sessions (30 min idle / 8 h absolute), HttpOnly + SameSite=Lax,
  CSRF double-submit on every POST, Origin check.
- Progressive login delay (0 → 30 s → doubling, capped 15 min) per account+IP.
- Single role per user, enforced server-side on every route (Admin is blocked
  from images, review and report).
- Every state change writes an `audit_event`; decisions, overrides and model
  activations are append-only. Evidence files are SHA-256 hashed and re-checked
  before a decision may count them (`HOLD_EVIDENCE_INTEGRITY`).
- The AI is **assistive by construction**: no autonomy, no auto-approve, no
  confidence threshold that can substitute for a human confirmation.
- Data minimisation: no worker names, no faces, no buyer identities beyond a
  demo label; Bangla + English UI for the people who actually do the work.
- Data sovereignty: the production design keeps evidence and decisions in the
  customer's jurisdiction; the demo runs entirely local, no third-party API.

---

## Repository map

```
app/
  main.py                 application factory: error handlers, middleware, routers
  config.py               paths, upload limits, demo flag — every setting in one place
  domain/engine.py        pure decision engine + 15 reason codes + precedence
  core/db.py              SQLite schema (organization … model_activation), audit helper
  core/security.py        Argon2id, sessions, CSRF, login delay, password policy
  services/review.py      evidence assembly, decision rows, overrides, timeline
  services/vision.py      unsupervised knit-defect detector (numpy) + self-test
  services/report.py      one-page FPDF report (ASCII-safe fallback; DejaVu in Docker)
  services/seed.py        demo data generator (idempotent, --force to rebuild)
  api/                    JSON API used by the React SPA (auth, lots, review, decisions, admin, system)
  web/pages.py            template environment + shared context (legacy screens)
  web/deps.py             sessions, role gates, CSRF, write permissions
  web/routes/             legacy Jinja routes: auth · dashboard · lots · capture · review · decisions · reports · admin · system
  i18n.py                 English + Bangla strings
frontend/                 React 19 + TypeScript + Vite SPA
  src/pages/              login · dashboard · lots · new lot · lot · plan · capture · review · decision · report · audit · admin · how
  src/components/         app shell, lot tabs, proposal/reason lists, shared UI primitives
  src/lib/                typed fetch client, Bangla/Dhaka formatters, session + i18n provider
  src/styles.css          React-only layout helpers; the product theme stays in static/app.css
scripts/build_dataset.py  build or download the staged dataset, verify every hash
ml/                       GPU workstream (owner: Hridoy) — dataset, train, evaluate, export
static/                   design system CSS + fonts + brand assets
templates/                legacy Jinja screens (reference + test fixtures)
tests/                    135 deterministic engine, API, rendering and security tests
docs/spec/                the original 13.6k-line specification set this build implements
tools/                    specification cross-document audit (legacy, kept for provenance)
```

Old import paths (`app.engine`, `app.service`, `app.db`, …) still work through
thin re-export shims, so branches written before the restructure keep running.

### Data

`data/` is generated, never committed:

```bash
python scripts/build_dataset.py            # staged dataset + manifest with SHA-256 per file
python scripts/build_dataset.py --verify   # integrity check
python -m app.seed --force                 # demo database, evidence images, model card
```

Directories created at runtime: `data/lotline.db`, `data/store/` (content-addressed
evidence), `data/models/` (detector + model card), `data/dataset/v1/` (staged set).
See `docs/DATA.md` for provenance, splits and the honest limits of the data.

---

## Production path

1. Swap SQLite for PostgreSQL 18 using the schema in `app/core/db.py` (already
   normalised, FKs and CHECK constraints in place).
2. Split vision into the InferenceWorker/Vision containers per the documented
   privilege split; the model interface is already a pure function of bytes.
3. Replace staged photos with the phone capture flow (EXIF strip, SHA-256,
   retake guidance) — the upload pipeline already does the first two.
4. Calibrate on a factory-labelled holdout set and publish a model card with
   per-class precision/recall before making any accuracy claim.
5. Add buyer clause packs as versioned data, not code, so each buyer's manual is
   reviewable and attributable.

---

*Demo build for the International AI Builders Congress 2026. The UI uses staged
garment images; the trained detector is additionally trained and evaluated on
BDFD9 factory fabric (CC BY 4.0). No buyer, worker or inspection records are
used. Engine `lotline-engine-1.2.0`.*
