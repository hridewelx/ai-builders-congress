"""Choose the review threshold on validation only, and record why.

The operating point is a product decision, not a training artefact: too low and
reviewers drown in false boxes, too high and real defects never reach them. This
script sweeps the validation detections (never the test split), picks the
threshold with the best recall subject to a precision floor, and writes the
whole table so the choice can be audited later.

Two things make the numbers match what the application actually shows:

* recall is divided by **ground-truth boxes**, not by the detections that
  happened to match, otherwise the lowest threshold always reports 1.0;
* the sweep applies the review queue's cap (top ``REVIEW_CAP`` proposals per
  photo, overlapping boxes suppressed) because that is what reaches a reviewer.

Usage:
    python -m ml.operating_point --precision-floor 0.75
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import MODELS, SCORE_THRESHOLD

REPORT = MODELS / "operating_point_v2.json"
TABLE_THRESHOLDS = (0.35, 0.50, 0.65)
REVIEW_CAP = 6
OVERLAP_IOU = 0.3  # same suppression rule as app/services/detector.py


def _iou(first: list[float], second: list[float]) -> float:
    ix = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    iy = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    inter = ix * iy
    union = (first[2] - first[0]) * (first[3] - first[1]) + \
            (second[2] - second[0]) * (second[3] - second[1]) - inter
    return inter / union if union > 0 else 0.0


def review_queue(detections: list[dict], threshold: float,
                 top_k: int = REVIEW_CAP, overlap: float = OVERLAP_IOU) -> list[dict]:
    """The proposals a reviewer sees: score filter, then cap and overlap suppression."""
    kept: list[dict] = []
    for det in sorted(detections, key=lambda item: -item["score"]):
        if det["score"] < threshold:
            continue
        if len(kept) >= top_k:
            break
        if any(_iou(det["box"], other["box"]) > overlap for other in kept):
            continue
        kept.append(det)
    return kept


def collect(checkpoint_path: Path, data_root: Path, split: str = "val") -> list[dict]:
    """Return one record per image: every detection plus its ground truth."""
    import torch
    from torch.utils.data import DataLoader

    from .model import build_model
    from .train import DetectionDataset, collate

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    size = checkpoint.get("size", 640)
    model = build_model(pretrained=False, min_size=size, max_size=size)
    model.load_state_dict(checkpoint["model"])
    model.to(device).eval()
    dataset = DetectionDataset(data_root, split, size)
    loader = DataLoader(dataset, batch_size=1, shuffle=False, collate_fn=collate)
    records: list[dict] = []
    with torch.inference_mode():
        for images, targets in loader:
            outputs = model([image.to(device) for image in images])
            target, output = targets[0], outputs[0]
            boxes = output["boxes"].cpu().tolist()
            scores = output["scores"].cpu().tolist()
            labels = output["labels"].cpu().tolist()
            records.append({
                "gt_boxes": target["boxes"].tolist(),
                "gt_labels": target["labels"].tolist(),
                "boxes": boxes, "scores": scores, "labels": labels,
                "detections": [{"box": box, "score": score, "label": label}
                               for box, score, label in zip(boxes, scores, labels)],
            })
    return records


def measure(records: list[dict], threshold: float) -> dict:
    """Precision and recall at one threshold, with the review queue's cap applied."""
    from .evaluate import evaluate_image

    truth = sum(len(record["gt_boxes"]) for record in records)
    kept = 0
    true_positives = 0
    for record in records:
        queue = review_queue(record["detections"], threshold)
        if not queue:
            continue
        matched = evaluate_image(record["gt_boxes"], record["gt_labels"],
                                 [item["box"] for item in queue],
                                 [item["score"] for item in queue],
                                 [int(item["label"]) for item in queue])
        kept += len(queue)
        true_positives += sum(det["tp"] for det in matched["detections"])
    return {"threshold": round(threshold, 2), "kept": kept,
            "true_positives": true_positives,
            "precision": round(true_positives / kept, 4) if kept else 0.0,
            "recall": round(true_positives / truth, 4) if truth else 0.0}


def sweep(records: list[dict], floor: float) -> dict:
    if not records:
        raise SystemExit("no validation detections to sweep")
    truth = sum(len(record["gt_boxes"]) for record in records)
    rows = [measure(records, step / 100) for step in range(5, 100, 5)]
    eligible = [row for row in rows if row["precision"] >= floor]
    if eligible:
        chosen = max(eligible, key=lambda row: (row["recall"], row["threshold"]))
        objective = f"maximum recall subject to precision >= {floor}"
    else:  # no threshold clears the floor: best F1, and say so
        chosen = max(rows, key=lambda row: (2 * row["precision"] * row["recall"])
                     / max(1e-9, row["precision"] + row["recall"]))
        objective = f"no threshold reached precision >= {floor}; best F1 used instead"
    return {"chosen_threshold": chosen["threshold"], "chosen": chosen,
            "objective": objective, "precision_floor": floor,
            "review_cap": REVIEW_CAP, "overlap_iou": OVERLAP_IOU,
            "table": [next(row for row in rows if abs(row["threshold"] - t) < 1e-9)
                      for t in TABLE_THRESHOLDS],
            "curve": rows, "gt_boxes": truth, "detections": chosen["kept"],
            "true_positives": chosen["true_positives"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose the review threshold on validation.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="val", choices=["val"],
                        help="validation only: the test split is scored once, elsewhere")
    parser.add_argument("--precision-floor", type=float, default=0.75)
    parser.add_argument("--out", type=Path, default=REPORT)
    args = parser.parse_args()

    records = collect(args.checkpoint, args.data, args.split)
    result = sweep(records, args.precision_floor)
    result.update({"split": args.split, "checkpoint": str(args.checkpoint),
                   "previous_default": SCORE_THRESHOLD,
                   "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("chosen_threshold", "objective", "precision_floor",
                       "gt_boxes", "detections")}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
