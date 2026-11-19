"""One image record plus the fingerprints used to compare images."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

@dataclass
class Record:
    """One image and its boxes, before the canonical export."""

    path: Path
    boxes: list[tuple[int, float, float, float, float]]  # class id, x1 y1 x2 y2 (pixels)
    source: str
    group: str = ""
    sha256: str = ""
    phash: str = ""
    split: str = ""
    duplicates: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dhash(path: Path, size: int = 8) -> str:
    """Difference hash, used to catch re-encoded copies that SHA-256 misses."""
    with Image.open(path) as image:
        gray = image.convert("L").resize((size + 1, size), Image.LANCZOS)
    pixels = list(gray.tobytes())
    bits = []
    for row in range(size):
        for col in range(size):
            bits.append("1" if pixels[row * (size + 1) + col] > pixels[row * (size + 1) + col + 1] else "0")
    return f"{int(''.join(bits), 2):016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def pixel_mae(a: Path, b: Path, size: int = 32) -> float:
    """Mean absolute difference of two thumbnails, 0-255 scale."""
    import numpy as np
    with Image.open(a) as ia, Image.open(b) as ib:
        ta = np.asarray(ia.convert("L").resize((size, size)), dtype=np.float32)
        tb = np.asarray(ib.convert("L").resize((size, size)), dtype=np.float32)
    return float(np.abs(ta - tb).mean())
