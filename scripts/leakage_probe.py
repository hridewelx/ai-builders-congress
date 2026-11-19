"""Independent near-duplicate probe between train and val/test (PIL + numpy only).

Why this exists
---------------
``ml.data`` already drops any train/val image that matches a test image under the rule
"dHash(8x8) Hamming <= 2 AND 32x32 thumbnail MAE <= 1.5". A verifier that reuses that rule
cannot fail, and the rule only sees re-encoded copies. It misses a flipped photo, a
second shot of the same patch with a shifted frame, or the same photo with an exposure change
(what Roboflow-style augmentation and burst photography produce).

This probe asks a different question: *is the test split closer to train than validation is?*
It measures, for every val and test image, the best match in train with three descriptors
that tolerate flips/rotations, small frame shifts and brightness changes, and compares the
distributions with a control (train images against the rest of train).

    python -m ml.leakage_probe --data data/dataset/det_v2
    python -m ml.leakage_probe --data data/dataset/det_v2 --source bdfd9 --top 30

Outputs
    data/models/leakage_probe.json   summary + per-image rows for val and test
    data/models/leakage_pairs.html   side-by-side thumbnails of the closest pairs; LOOK AT THEM

Limits, stated plainly: knit fabric is self-similar, so some match is expected for any two
photos of the same cloth (that is what the control measures). The descriptors do not handle
scale changes or large crops. The default flag lines (phase peak 0.30, NCC 0.95, dHash 0.10)
were checked only on synthetic textures with planted copies (flip, rotation, 30 px shift with
exposure change, re-encode): on real photos read the train_control row first and move the
lines if the control already sits near them. A clean result means "no evidence the test
split is closer to train than val is", not "no leakage is possible".
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PHASE_SIZE = 64


def dihedral(array: np.ndarray) -> list[np.ndarray]:
    """The 8 flips/rotations of a square array."""
    variants = []
    for k in range(4):
        rotated = np.rot90(array, k)
        variants.append(rotated)
        variants.append(np.fliplr(rotated))
    return variants


def gray(path: Path, size: int) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L").resize((size, size), Image.LANCZOS), dtype=np.float32)


def unit(vectors: np.ndarray) -> np.ndarray:
    """Zero-mean, unit-norm rows, so a dot product is a normalised cross-correlation."""
    vectors = vectors - vectors.mean(axis=-1, keepdims=True)
    norm = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(norm, 1e-6)


def dhash_bits(thumb17: np.ndarray) -> np.ndarray:
    return (thumb17[:, :-1] > thumb17[:, 1:]).ravel()


class Features:
    """Descriptors of one image."""

    def __init__(self, path: Path):
        self.path = path
        thumb17 = gray(path, 17)
        self.dhash = [dhash_bits(v) for v in dihedral(thumb17)]          # 8 x 272 bits
        self.ncc = unit(np.stack([v.ravel() for v in dihedral(gray(path, 32))]))   # 8 x 1024
        # phase correlation tolerates translation, brightness and contrast; 8 flips/rotations of the query
        window = np.outer(np.hanning(PHASE_SIZE), np.hanning(PHASE_SIZE)).astype(np.float32)
        self.phase = np.stack([np.fft.rfft2((v - v.mean()) * window)
                               for v in dihedral(gray(path, PHASE_SIZE))]).astype(np.complex64)   # 8 x 64 x 33
        # legacy rule inputs (same definitions as ml.data.dhash / pixel_mae)
        legacy = np.asarray(Image.open(path).convert("L").resize((9, 8), Image.LANCZOS), dtype=np.float32)
        self.legacy_bits = (legacy[:, :-1] > legacy[:, 1:]).ravel()
        self.legacy_thumb = gray(path, 32).ravel()


def match(query: Features, pool: list[Features], skip: int | None = None) -> dict:
    """Best train match for one query under each descriptor."""
    dh = np.array([min(np.count_nonzero(q != t.dhash[0]) for q in query.dhash) for t in pool], dtype=np.float32) / 272
    ncc_matrix = np.stack([t.ncc[0] for t in pool])                         # N x 1024
    ncc = (query.ncc @ ncc_matrix.T).max(axis=0)                            # N
    pool_phase = np.stack([t.phase[0] for t in pool])                        # N x 64 x 33
    phase = np.zeros(len(pool), dtype=np.float32)
    for variant in range(8):
        cross = query.phase[variant][None] * np.conj(pool_phase)
        cross /= np.abs(cross) + 1e-6
        peak = np.fft.irfft2(cross, s=(PHASE_SIZE, PHASE_SIZE)).reshape(len(pool), -1).max(axis=1)
        phase = np.maximum(phase, peak)
    legacy_hit = np.array([
        np.count_nonzero(query.legacy_bits != t.legacy_bits) <= 2
        and float(np.abs(query.legacy_thumb - t.legacy_thumb).mean()) <= 1.5 for t in pool])
    if skip is not None:
        dh[skip], ncc[skip], phase[skip], legacy_hit[skip] = 1.0, -1.0, -1.0, False
    best = int(np.argmax(phase))
    return {
        "dhash_frac_min": float(dh.min()), "dhash_best": int(np.argmin(dh)),
        "ncc32_max": float(ncc.max()), "ncc32_best": int(np.argmax(ncc)),
        "phase_peak_max": float(phase[best]), "phase_best": best,
        "legacy_rule_flags": bool(legacy_hit.any()),
    }


def rank_sum_p(a: list[float], b: list[float]) -> float:
    """One-sided Mann-Whitney p that values in ``a`` tend to be larger than in ``b`` (normal approximation)."""
    import math
    values = np.array(list(a) + list(b), dtype=np.float64)
    order = values.argsort(kind="mergesort")
    ranks = np.empty(len(values))
    sorted_values = values[order]
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    n1, n2 = len(a), len(b)
    u = ranks[:n1].sum() - n1 * (n1 + 1) / 2
    mean = n1 * n2 / 2
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u - mean - 0.5) / sd if sd else 0.0
    return 0.5 * math.erfc(z / math.sqrt(2))


def thumb_b64(path: Path, size: int = 200) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((size, size))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode()


def summarise(rows: list[dict], flag_phase: float, flag_ncc: float, flag_dhash: float) -> dict:
    if not rows:
        return {"n": 0}

    def quantiles(key: str) -> dict:
        values = np.array([row[key] for row in rows])
        return {"median": round(float(np.median(values)), 3), "p90": round(float(np.quantile(values, 0.9)), 3),
                "max": round(float(values.max()), 3)}

    suspect = [row for row in rows if row["phase_peak_max"] >= flag_phase
               or row["ncc32_max"] >= flag_ncc or row["dhash_frac_min"] <= flag_dhash]
    return {
        "n": len(rows),
        "phase_peak": quantiles("phase_peak_max"),
        "ncc32": quantiles("ncc32_max"),
        "dhash_frac": quantiles("dhash_frac_min"),
        "suspect": len(suspect),
        "suspect_share": round(len(suspect) / len(rows), 3),
        "legacy_rule_flags": sum(1 for row in rows if row["legacy_rule_flags"]),
    }


def contact_sheet(groups: dict[str, list[dict]], pool: list[Features], top: int) -> str:
    cards = []
    for name, rows in groups.items():
        ranked = sorted(rows, key=lambda r: -r["phase_peak_max"])[:top]
        cards.append(f"<h2>{html.escape(name)}: {len(ranked)} closest pairs by phase-correlation peak</h2><div class=g>")
        for row in ranked:
            train = pool[row["phase_best"]].path
            cards.append(
                "<div class=c>"
                f"<img src='data:image/jpeg;base64,{thumb_b64(Path(row['file']))}'>"
                f"<img src='data:image/jpeg;base64,{thumb_b64(train)}'>"
                f"<p>{html.escape(Path(row['file']).name)} &rarr; {html.escape(train.name)}<br>"
                f"phase peak {row['phase_peak_max']:.3f} · NCC {row['ncc32_max']:.3f} · "
                f"dHash {row['dhash_frac_min']:.3f} · old rule {'FLAGS' if row['legacy_rule_flags'] else 'misses'}</p></div>")
        cards.append("</div>")
    style = ("body{font:14px system-ui;margin:20px;background:#111;color:#eee}.g{display:flex;flex-wrap:wrap;gap:12px}"
             ".c{background:#1b1b1b;padding:8px;border-radius:8px;width:420px}.c img{width:200px;margin-right:6px}"
             "p{margin:6px 0 0;font-size:12px;color:#bbb}")
    return f"<!doctype html><meta charset=utf-8><title>leakage probe</title><style>{style}</style>" + "".join(cards)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe train/val/test for near-duplicates the dHash rule misses.")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--source", default="bdfd9", help="filename prefix to compare ('' = every source)")
    parser.add_argument("--control", type=int, default=120, help="train images used as the control group")
    parser.add_argument("--top", type=int, default=24, help="pairs per group in the HTML sheet")
    parser.add_argument("--flag-phase", type=float, default=0.30,
                        help="phase-correlation peak at or above which a pair is called a near-duplicate")
    parser.add_argument("--flag-ncc", type=float, default=0.95)
    parser.add_argument("--flag-dhash", type=float, default=0.10)
    parser.add_argument("--out", type=Path, default=Path("data/models/leakage_probe.json"))
    parser.add_argument("--html", type=Path, default=Path("data/models/leakage_pairs.html"))
    args = parser.parse_args()

    def files(split: str) -> list[Path]:
        folder = args.data / "images" / split
        return sorted(p for p in folder.glob("*") if p.suffix.lower() in EXTS and p.name.startswith(args.source))

    train_paths = files("train")
    if not train_paths:
        raise SystemExit(f"no train images under {args.data / 'images' / 'train'} for prefix '{args.source}'")
    print(f"train {len(train_paths)} · val {len(files('val'))} · test {len(files('test'))} "
          f"(prefix '{args.source}')", flush=True)
    pool = [Features(path) for path in train_paths]

    groups: dict[str, list[dict]] = {}
    for split in ("val", "test"):
        rows = []
        for path in files(split):
            row = match(Features(path), pool)
            row["file"] = str(path)
            row["best_train"] = str(pool[row["phase_best"]].path)
            rows.append(row)
        groups[split] = rows

    rng = np.random.default_rng(0)
    picks = rng.choice(len(pool), size=min(args.control, len(pool)), replace=False)
    control = []
    for index in picks:
        row = match(pool[index], pool, skip=int(index))
        row["file"] = str(pool[index].path)
        row["best_train"] = str(pool[row["phase_best"]].path)
        control.append(row)
    groups["train_control"] = control

    flag_phase = args.flag_phase
    summary = {name: summarise(rows, flag_phase, args.flag_ncc, args.flag_dhash) for name, rows in groups.items()}
    print(f"near-duplicate = phase peak >= {flag_phase}, or NCC >= {args.flag_ncc}, "
          f"or dHash fraction <= {args.flag_dhash}")
    print("\n{:14s} {:>4s}  {:>26s}  {:>20s}  {:>8s}  {:>9s}".format(
        "group", "n", "phase peak med / p90 / max", "dHash frac med/p90", "near-dup", "old rule"))
    for name, item in summary.items():
        if not item["n"]:
            continue
        print("{:14s} {:4d}  {:>7.3f} /{:>7.3f} /{:>6.3f}  {:>9.3f} /{:>8.3f}  {:>3d}/{:<4d}  {:>4d}/{:<4d}".format(
            name, item["n"], item["phase_peak"]["median"], item["phase_peak"]["p90"], item["phase_peak"]["max"],
            item["dhash_frac"]["median"], item["dhash_frac"]["p90"],
            item["suspect"], item["n"], item["legacy_rule_flags"], item["n"]))

    def is_dup(row: dict) -> bool:
        return (row["phase_peak_max"] >= flag_phase or row["ncc32_max"] >= args.flag_ncc
                or row["dhash_frac_min"] <= args.flag_dhash)

    verdict = []
    missed = {name: [row for row in groups[name] if is_dup(row) and not row["legacy_rule_flags"]]
              for name in ("val", "test")}
    for name in ("test", "val"):
        if missed[name]:
            verdict.append(f"WARNING: {len(missed[name])} {name} image(s) have a near-identical train image under "
                           "flips/shifts/exposure changes that the old dHash rule did not catch. Open the HTML sheet, "
                           "confirm by eye, then drop them from the evaluation split (or from train) and re-score "
                           "before quoting a held-out number.")
    if not missed["test"] and not missed["val"]:
        verdict.append("No near-duplicates beyond what the old rule already handles, at these thresholds.")
    if groups["test"] and groups["val"]:
        p_value = rank_sum_p([r["phase_peak_max"] for r in groups["test"]], [r["phase_peak_max"] for r in groups["val"]])
        verdict.append(f"Test vs validation best-match score: one-sided rank-sum p = {p_value:.3f} "
                       f"(n={len(groups['test'])} vs {len(groups['val'])}; information only, the tail is heavy). "
                       f"Control (train vs rest of train) median {summary['train_control']['phase_peak']['median']:.3f}, "
                       f"p90 {summary['train_control']['phase_peak']['p90']:.3f}: if val and test sit at the control "
                       "level the splits are as redundant as the data itself.")
    verdict.append("Whatever the numbers say, BDFD9's splits come from the same four factories, so none of "
                   "this estimates a new factory.")
    print()
    for line in verdict:
        print("-", line)
    for name in ("test", "val"):
        print(f"\nclosest {name} -> train pairs (phase peak · NCC · dHash fraction · old rule):")
        for row in sorted(groups[name], key=lambda r: -r["phase_peak_max"])[:5]:
            print(f"  {Path(row['file']).name:24s} -> {Path(row['best_train']).name:24s} "
                  f"{row['phase_peak_max']:.3f} · {row['ncc32_max']:.3f} · {row['dhash_frac_min']:.3f} · "
                  f"{'flags' if row['legacy_rule_flags'] else 'misses'}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"source_prefix": args.source, "thresholds": {
        "phase_peak": round(flag_phase, 3), "ncc32": args.flag_ncc, "dhash_frac": args.flag_dhash},
        "summary": summary, "verdict": verdict,
        "rows": {name: groups[name] for name in ("val", "test")}}, indent=2), encoding="utf-8")
    args.html.write_text(contact_sheet(groups, pool, args.top), encoding="utf-8")
    print(f"\nwrote {args.out}\nwrote {args.html}  <- open it and look at the top pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
