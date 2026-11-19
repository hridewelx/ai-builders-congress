#!/usr/bin/env sh
set -e
DATA="${LOTLINE_DATA:-/data}"
mkdir -p "$DATA"
if [ ! -f "$DATA/lotline.db" ]; then
  if [ -f /seed/lotline.db ]; then
    echo "first boot: copying the demo data baked into the image"
    cp -a /seed/. "$DATA"/
  else
    echo "first boot: no baked seed, generating demo data (about 30 s)"
    python -m app.seed
  fi
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8077}" --proxy-headers
