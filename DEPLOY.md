# Deploying the Lotline demo

The demo is a single process: FastAPI + SQLite + an in-process model, and a
writable data directory. No GPU, no external API.

Measured memory, real weights, this app (Windows, Python 3.14, onnxruntime 1.32,
one inspector, `/` and `/lots/6` rendered, then one detection):

| backend | RSS | peak |
| --- | --- | --- |
| `numpy` baseline | 119 MB | 180 MB |
| `onnx` after a detection | 284 MB | 308 MB |

Treat 512 MB as the honest floor for the ONNX build: it fits with room for one
or two reviewers, and it is not a place to run two model processes. Linux
numbers are usually a little higher than Windows; measure on the host if in
doubt. The review queue caps at 6 proposals per photo, which is what keeps the
per-request cost bounded.

**What actually ships.** The image only carries weights when you ask for them:
`data/models/det_v2.onnx` is git-ignored and excluded from the build context, so
a plain `docker build` (or Render from the repo) runs the numpy baseline and
says so on `/readyz` and in the PDF. To serve the trained detector, pass
`LOTLINE_MODEL_URL` + `LOTLINE_MODEL_SHA256` at build time (the Dockerfile
verifies both, then sets the detector to `onnx`), or bake the file in yourself.
Never describe the public URL as "the trained detector" unless `/readyz` says
`"detector": "onnx"`.

Judges should be able to click a link. Pick one of these.

---

## Option A — Render (free tier, public URL, ~5 min)

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → select the repo. `render.yaml` is included.
3. Deploy. The first boot seeds the demo (~25 s); `/healthz` turns green.
4. Open the URL, press **Inspector** on the login screen.
5. Verify with the smoke script:

```bash
python scripts/smoke_live.py https://<app>.onrender.com --wait 300
# expected: 0 failures; /readyz reports detector=numpy on a free instance
python scripts/smoke_live.py https://<app>.onrender.com --expect-detector onnx  # only if you ship the model
```

The free instance sleeps after inactivity; the first click takes ~30 s to wake.
For a judging window, upgrade to the cheapest paid instance or keep it warm.

## Option B — Fly.io

```bash
fly launch --no-deploy          # accept the generated fly.toml, pick a region near Dhaka (sin/bom)
fly volumes create lotline_data --size 1
# add to fly.toml:  [mounts] source="lotline_data" destination="/data"
fly deploy
```

## Option C — any VPS / on-prem (recommended for a factory pilot)

```bash
git clone <repo> && cd lotline
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
LOTLINE_DATA=/var/lib/lotline python -m app.seed
LOTLINE_DEMO=1 LOTLINE_DATA=/var/lib/lotline \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8077 --proxy-headers
```

Put Caddy or nginx in front for TLS:

```
lotline.example.com {
    reverse_proxy 127.0.0.1:8077
}
```

## Option D — Docker anywhere

```bash
docker build -t lotline .
docker run -p 8077:8077 -v lotline_data:/data lotline
```

---

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `LOTLINE_DEMO` | `1` | enables the one-click `/demo/{role}` login buttons. **Set to `0` for anything that is not a demo.** |
| `LOTLINE_DATA` | `./data` | directory for `lotline.db` and the image store |
| `LOTLINE_DB` | `$LOTLINE_DATA/lotline.db` | explicit database path |
| `PORT` | `8077` | port for the container start script |
| `LOTLINE_SECURE_COOKIE` | `0` | set to `1` behind HTTPS so the session cookie is `Secure` |

## Before a *real* pilot (not the demo)

1. `LOTLINE_DEMO=0`, real accounts, password rotation, `LOTLINE_SECURE_COOKIE=1`.
2. Replace SQLite with PostgreSQL (`app/core/db.py` schema is already normalised).
3. Move vision to the InferenceWorker/Vision split in `docs/spec/SYSTEM_DESIGN_v1_2.md`.
4. Calibrate the detector on a labelled factory holdout and publish the model card.
5. Back up `/data` (evidence files are content-addressed and hash-checked; losing
   them turns every affected decision into `HOLD_EVIDENCE_INTEGRITY`).

## Demo reset

```bash
python -m app.seed --force      # rebuilds lots, photos, decisions, audit trail
```

or delete `$LOTLINE_DATA/lotline.db` and the `store/` folder and restart.

---

## Handoff: the five-minute deploy (for whoever presses the button)

Everything below is already committed on `main`. No code changes, no database
setup, no environment variables.

**Before you start:** the GitHub repo is private, so your Render account needs
access to `hridewelx/ai-builders-congress` (invite sent from the repo settings).

1. Render → **New → Blueprint** → pick the repo → **Apply**. `render.yaml` sets
   the plan, the health check and `LOTLINE_DATA=/tmp/lotline`; accept it as-is.
2. Wait for the build (~4–6 min: Debian slim + CPU-only wheels, no torch).
3. `/healthz` goes green, then open the URL. The login page has three one-click
   demo buttons (Inspector / Supervisor / Admin, password `QualityFloor2026!`).
4. Verify from any machine with the repo checked out:

```bash
python scripts/smoke_live.py https://<app>.onrender.com --wait 300
# expect: 0 failure(s), 0 warning(s); /readyz reports detector=numpy
```

**Do not change these three things:**

- **No persistent disk.** Free instances reject disks; the image already bakes a
  seed at `/seed` and `start.sh` copies it to `/tmp/lotline` on first boot.
- **No Postgres, no Redis, no extra services.** One process, SQLite, in-process
  model.
- **Do not edit `start.sh` or the Dockerfile command.** It must bind `$PORT`.

**If the build fails**, the log to read is the `pip install` step; then paste the
tail into the team chat rather than "fixing" the Dockerfile on the deadline day.

**Cold start:** a sleeping free instance takes ~30–50 s to answer the first
click. Open the URL once a minute before recording or judging.
