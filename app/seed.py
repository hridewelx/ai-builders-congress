"""Demo data CLI: `python -m app.seed [--force]`.

Canonical implementation lives in app.services.seed. Kept here because the
documented commands and the deployment start script call `python -m app.seed`.
"""
from __future__ import annotations

import argparse

from app.core import db
from app.services.seed import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Lotline demo database.")
    parser.add_argument("--force", action="store_true", help="delete and rebuild the demo data")
    args = parser.parse_args()
    db.init()
    run(force=args.force)


if __name__ == "__main__":
    main()
