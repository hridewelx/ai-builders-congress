"""How much a score means: reliability bins on validation, never on test.

The detector's output is a ranking. Before anyone shows it as a confidence, they
should see what each score band actually delivered. This script answers that with
the only honest denominator available: of the boxes in a band, how many matched a
labelled defect of the same class at IoU >= 0.5.

Bins are 0.05 wide from 0.50 to 1.00. The number at the end is ECE — the average
gap between the score and the measured hit rate, weighted by how many boxes sit in
each band. A small ECE would not make a score a probability; a large one is a
reason to keep calling it a score.

    python -m ml.reliability --split val
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import CLASSES, IOU_THRESHOLD, MODELS, SCORE_THRESHOLD
from .evaluate import iou

BIN_START = 0.50
BIN_WIDTH = 0.05


def bin_index(score: float) -> int:
    """Band number for a score, with edge cases on the edge.

    Floating point puts 0.55 at 1.0000000000000009 bands above 0.50, so integer
    division or a bare int() shifts every band boundary by one. Rounding the
    quotient first keeps 0.55 in the 0.55–0.60 band and 0.60 in the next one.
    """
    steps = int(round((1.0 - BIN_START) / BIN_WIDTH))  # ten bands from 0.50 to 1.00
    index = int(round((float(score) - BIN_START) / BIN_WIDTH))
    return max(0, min(steps - 1, index))


def summarise(records: list[dict], min_count: int = 1, _per_class: bool = True) -> dict:
    """Group scored matches into bands and compute ECE. Pure: no model, no files."""
    bands: dict[int, dict] = {}
    for record in records:
        index = bin_index(float(record["score"]))
        band = bands.setdefault(index, {"count": 0, "hits": 0, "score_sum": 0.0})
        band["count"] += 1
        band["hits"] += 1 if record["matched"] else 0
        band["score_sum"] += float(record["score"])

    total = sum(band["count"] for band in bands.values())
    ece = 0.0
    table = []
    for index in sorted(bands):
        band = bands[index]
        mean_score = band["score_sum"] / band["count"]
        precision = band["hits"] / band["count"]
        ece += (band["count"] / total) * abs(precision - mean_score) if total else 0.0
        table.append({
            "bin": f"{BIN_START + index * BIN_WIDTH:.2f}-{BIN_START + (index + 1) * BIN_WIDTH:.2f}",
            "count": band["count"],
            "mean_score": round(mean_score, 4),
            "measured_precision": round(precision, 4),
            "gap": round(precision - mean_score, 4),
            "reliable_example": band["count"] >= min_count,
        })
    per_class: dict[str, dict] = {}
    for label in (sorted({int(record["label"]) for record in records}) if _per_class else []):
        subset = [record for record in records if int(record["label"]) == label]
        block = summarise(subset, min_count=min_count, _per_class=False)
        bins = block["bins"]
        worst = max(bins, key=lambda row: abs(row["gap"])) if bins else None
        per_class[CLASSES[label - 1] if 1 <= label <= len(CLASSES) else f"label_{label}"] = {
            "detections": block["detections"], "ece": block["ece"],
            "worst_band": worst["bin"] if worst else None,
            "worst_gap": worst["gap"] if worst else None,
        }
    return {"detections": total, "bins": table, "ece": round(ece, 4),
            "per_class": per_class,
            "note": ("Measured on validation detections at one IoU. This is the gap between "
                     "score and hit rate, not a calibration claim: a band that matches its "
                     "score is an observation, not a guarantee on another factory.")}


def matches_for_image(boxes_gt, labels_gt, boxes_p, scores_p, labels_p,
                      iou_threshold: float = IOU_THRESHOLD) -> list[dict]:
    """Greedy match at one IoU, keeping a hit/miss label for every prediction."""
    order = sorted(range(len(scores_p)), key=lambda i: -float(scores_p[i]))
    used = set()
    out = []
    for i in order:
        best, best_iou = -1, 0.0
        for j, gt_box in enumerate(boxes_gt):
            if j in used or int(labels_gt[j]) != int(labels_p[i]):
                continue
            value = iou(boxes_p[i], gt_box)
            if value > best_iou:
                best, best_iou = j, value
        matched = best >= 0 and best_iou >= iou_threshold
        if matched:
            used.add(best)
        out.append({"score": float(scores_p[i]), "label": int(labels_p[i]), "matched": matched})
    return out


def collect(checkpoint_path: Path, data_root: Path, split: str = "val") -> dict:
    import torch
    from torch.utils.data import DataLoader

    from .model import build_model
    from .train import DetectionDataset, collate, move

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(pretrained=False, min_size=checkpoint.get("size", 640),
                        max_size=checkpoint.get("size", 640))
    model.load_state_dict(checkpoint["model"])
    model.to(device).eval()
    dataset = DetectionDataset(data_root, split, checkpoint.get("size", 640))
    loader = DataLoader(dataset, batch_size=1, shuffle=False, collate_fn=collate)
    records: list[dict] = []
    with torch.inference_mode():
        for images, targets in loader:
            outputs = model([image.to(device) for image in images])
            target = move(targets, torch.device("cpu"))[0]
            output = outputs[0]
            records += matches_for_image(
                target["boxes"].tolist(), target["labels"].tolist(),
                output["boxes"].tolist(), output["scores"].tolist(), output["labels"].tolist())
    return {"records": records, "images": len(dataset)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reliability bins for the detector's scores.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="val", choices=["val"])
    parser.add_argument("--threshold", type=float, default=SCORE_THRESHOLD)
    parser.add_argument("--out", type=Path, default=MODELS / "reliability_v2.json")
    args = parser.parse_args(argv)
    collected = collect(args.checkpoint, args.data, args.split)
    kept = [record for record in collected["records"] if record["score"] >= args.threshold]
    report = summarise(kept)
    report.update({"split": args.split, "images": collected["images"],
                   "score_threshold": args.threshold, "iou": IOU_THRESHOLD,
                   "checkpoint": str(args.checkpoint)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("detections", "ece", "split", "images")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
