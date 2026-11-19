"""Assemble a canonical YOLO detection dataset from public and synthetic sources.

Responsibilities:
  * read YOLO folders (images/ + labels/ pairs) and Lotline's annotation JSONL
  * map each source's class names onto the four v1 detector classes
  * de-duplicate by SHA-256 and by perceptual hash; never absorb test into train
  * preserve each source's train/valid/test; split only unassigned images by group
  * write train/val/test folders, a data.yaml and a manifest with licence metadata

Usage:
    python -m ml.data prepare --source data/raw/bdfd9/BDFD9 --name bdfd9 --licence "CC BY 4.0"
    python -m ml.data prepare --source data/dataset/v1 --name staged
"""
from __future__ import annotations

from ..config import CLASS_TO_ID, CLASSES, SEED, SOURCE_CLASS_MAP, VAL_FRACTION
from .cli import main
from .dedupe import dedupe, dedupe_preserving_test
from .prepare import prepare
from .readers import _norm, discover_names, map_class, read_jsonl, read_yolo
from .records import IMAGE_EXTS, Record, dhash, hamming, pixel_mae, sha256_file
from .splitting import export, split_records

__all__ = [
    "Record", "IMAGE_EXTS", "sha256_file", "dhash", "hamming", "pixel_mae",
    "read_yolo", "read_jsonl", "discover_names", "map_class", "dedupe",
    "dedupe_preserving_test", "split_records", "export", "prepare",
    "CLASSES", "CLASS_TO_ID", "SOURCE_CLASS_MAP", "SEED", "VAL_FRACTION",
]
