#!/usr/bin/env sh
set -e
if [ ! -f "${LOTLINE_DATA:-/data}/lotline.db" ]; then
  echo "first boot: seeding demo data (about 25 s)"
  python -m app.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8077}" --proxy-headers
