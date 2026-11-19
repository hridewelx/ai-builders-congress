# Deploying the Lotline demo

The demo is a single process: FastAPI + SQLite + an in-process model. It needs
~300 MB RAM (numpy baseline) or ~450 MB with the ONNX detector loaded, and a
writable data directory. No GPU, no external API.

**What actually ships.** `data/` is git-ignored, so the ONNX artifact is *not*
in the Render build context. A deployed instance therefore runs the numpy
baseline and reports "staged knit panels only (unsupervised baseline)" in the
PDF and on `/readyz`. That is honest, not a bug. To run the trained detector on
a host, ship `det_v2.onnx` (76 MB) with the build and set `LOTLINE_DETECTOR=onnx`
(see `requirements.txt`, which already pins onnxruntime).

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
