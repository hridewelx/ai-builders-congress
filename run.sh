#!/usr/bin/env bash
# Lotline demo launcher (macOS / Linux / Git Bash).
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
if [ ! -f data/lotline.db ]; then
  echo "seeding demo data…"
  "$PYTHON" -m app.seed
fi
export LOTLINE_DEMO=1
exec "$PYTHON" -m uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8077}"
