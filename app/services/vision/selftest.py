"""Deterministic self-test and the honest staged-image evaluation."""
from __future__ import annotations

import numpy as np

from .detect import detect
from .model import _train_or_load
from .params import HUMAN_CLASSES
from .textures import knit_texture, staged_photo


def selftest() -> tuple[bool, str]:
    """Deterministic self-test: clean stays quiet, a known hole is proposed."""
    model = _train_or_load()
    clean = knit_texture(420, 420, seed=4242)
    r_clean = detect(clean)
    img, truth = staged_photo(seed=99, defects=["hole"])
    r_def = detect(np.array(img))
    hit = False
    if truth:
        tb = truth[0]["box"]
        for p in r_def["proposals"]:
            b = p["box"]
            ix = max(0, min(b[2], tb[2]) - max(b[0], tb[0]))
            iy = max(0, min(b[3], tb[3]) - max(b[1], tb[1]))
            inter = ix * iy
            union = (b[2] - b[0]) * (b[3] - b[1]) + (tb[2] - tb[0]) * (tb[3] - tb[1]) - inter
            if union > 0 and inter / union >= 0.05:
                hit = True
    quiet = len(r_clean["proposals"]) <= 2
    ok = bool(hit and quiet)
    detail = (f"clean_proposals={len(r_clean['proposals'])}; defective_proposals={len(r_def['proposals'])}; "
              f"known_hole_localised={hit}; threshold={model['meta'].get('threshold', 0)}")
    return ok, detail


def evaluate_staged(n: int = 40, seed0: int = 7000) -> dict:
    """Small, honest evaluation on staged images. Reported as staged-only."""
    per_class = {c: {"tp": 0, "gt": 0} for c in HUMAN_CLASSES}
    views = {"with_proposal": 0, "total": 0}
    false_views = 0
    for i in range(n):
        kind = HUMAN_CLASSES[i % 5]
        img, truth = staged_photo(seed=seed0 + i, defects=[kind] if i % 4 != 3 else [])
        r = detect(np.array(img))
        views["total"] += 1
        if r["proposals"]:
            views["with_proposal"] += 1
        if not truth:
            if r["proposals"]:
                false_views += 1
            continue
        per_class[kind]["gt"] += 1
        tb = truth[0]["box"]
        for p in r["proposals"]:
            b = p["box"]
            ix = max(0, min(b[2], tb[2]) - max(b[0], tb[0]))
            iy = max(0, min(b[3], tb[3]) - max(b[1], tb[1]))
            inter = ix * iy
            union = (b[2] - b[0]) * (b[3] - b[1]) + (tb[2] - tb[0]) * (tb[3] - tb[1]) - inter
            if union > 0 and inter / union >= 0.05:
                per_class[kind]["tp"] += 1
                break
    rows = []
    for c in HUMAN_CLASSES:
        gt = per_class[c]["gt"]
        if gt:
            rows.append({"class": c, "recall": round(per_class[c]["tp"] / gt, 2), "n": gt})
    return {"rows": rows, "views": views, "false_positive_views": false_views,
            "note": "staged images only; not factory evidence"}
