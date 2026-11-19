"""Choose the review threshold on validation only, and record why.

The operating point is a product decision, not a training artefact: too low and
reviewers drown in false boxes, too high and real defects never reach them. This
script sweeps the validation detections (never the test split), picks the
threshold with the best recall subject to a precision floor, and writes the
whole table so the choice can be audited later.

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


def collect(checkpoint_path: Path, data_root: Path, split: str = "val") -> list[tuple[float, int]]:
    """Return (score, is_true_positive) for every validation detection."""
    import torch
    from torch.utils.data import DataLoader

    from .evaluate import evaluate_image
    from .model import build_model
    from .train import DetectionDataset, collate

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(pretrained=False, min_size=checkpoint.get("size", 640),
                        max_size=checkpoint.get("size", 640))
    model.load_state_dict(checkpoint["model"])
    model.to(device).eval()
    dataset = DetectionDataset(data_root, split, checkpoint.get("size", 640))
    loader = DataLoader(dataset, batch_size=1, shuffle=False, collate_fn=collate)
    pairs: list[tuple[float, int]] = []
    with torch.inference_mode():
        for images, targets in loader:
            outputs = model([image.to(device) for image in images])
            target = targets[0]
            image = evaluate_image(
                target["boxes"].tolist(), target["labels"].tolist(),
                outputs[0]["boxes"].cpu().tolist(), outputs[0]["scores"].cpu().tolist(),
                outputs[0]["labels"].cpu().tolist())
            for det in image["detections"]:
                pairs.append((det["score"], det["tp"]))
    return pairs


def sweep(pairs: list[tuple[float, int]], floor: float) -> dict:
    if not pairs:
        raise SystemExit("no validation detections to sweep")
    gt = sum(1 for _, tp in pairs if tp)
    rows = []
    chosen = None
    for step in range(5, 100, 5):
        threshold = step / 100
        kept = [tp for score, tp in pairs if score >= threshold]
        tp = sum(kept)
        precision = tp / len(kept) if kept else 0.0
        recall = tp / gt if gt else 0.0
        rows.append({"threshold": round(threshold, 2), "kept": len(kept), "true_positives": tp,
                     "precision": round(precision, 4), "recall": round(recall, 4)})
        if precision >= floor and (chosen is None or recall > chosen["recall"]):
            chosen = rows[-1]
    table = [next(r for r in rows if abs(r["threshold"] - t) < 1e-9) for t in TABLE_THRESHOLDS]
    if chosen is None:  # no point clears the floor: fall back to best F1
        best = max(rows, key=lambda r: (2 * r["precision"] * r["recall"])
                   / max(1e-9, r["precision"] + r["recall"]))
        chosen = best
        objective = f"no threshold reached precision >= {floor}; best F1 used instead"
    else:
        objective = f"maximum recall subject to precision >= {floor}"
    return {"chosen_threshold": chosen["threshold"], "chosen": chosen,
            "objective": objective, "precision_floor": floor,
            "table": table, "curve": rows, "detections": len(pairs), "true_positives": gt}


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose the review threshold on validation.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="val", choices=["val"],
                        help="validation only: the test split is scored once, elsewhere")
    parser.add_argument("--precision-floor", type=float, default=0.75)
    parser.add_argument("--out", type=Path, default=REPORT)
    args = parser.parse_args()

    pairs = collect(args.checkpoint, args.data, args.split)
    result = sweep(pairs, args.precision_floor)
    result.update({"split": args.split, "checkpoint": str(args.checkpoint),
                   "previous_default": SCORE_THRESHOLD,
                   "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("chosen_threshold", "objective", "precision_floor", "detections")}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
