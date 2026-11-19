"""Score calibration for the detector.

A detector's raw score is not a probability that the box is correct. This
script fits one temperature on validation detections and reports the expected
calibration error before and after, so the review UI can label a number as a
score rather than a confidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import MODELS
from .evaluate import evaluate_image


def collect_scores(checkpoint_path: Path, data_root: Path, split: str = "val") -> list[tuple[float, int]]:
    """Return (score, is_true_positive) for every prediction on the split."""
    import torch
    from torch.utils.data import DataLoader

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
    scores: list[tuple[float, int]] = []
    with torch.inference_mode():
        for images, targets in loader:
            outputs = model([image.to(device) for image in images])
            target = targets[0]
            result = evaluate_image(
                target["boxes"].tolist(), target["labels"].tolist(),
                outputs[0]["boxes"].cpu().tolist(), outputs[0]["scores"].cpu().tolist(),
                outputs[0]["labels"].cpu().tolist(), iou_threshold=0.5)
            for det in result["detections"]:
                scores.append((det["score"], det["tp"]))
    return scores


def _logit(score: float, eps: float = 1e-6) -> float:
    import math
    value = min(1 - eps, max(eps, score))
    return math.log(value / (1 - value))


def _nll(scores: list[tuple[float, int]], temperature: float) -> float:
    import math
    total = 0.0
    for score, target in scores:
        logit = _logit(score) / temperature
        probability = 1 / (1 + math.exp(-logit))
        probability = min(1 - 1e-9, max(1e-9, probability))
        total -= math.log(probability if target else 1 - probability)
    return total / max(1, len(scores))


def expected_calibration_error(items: list[tuple[float, int]], bins: int = 10) -> tuple[float, list[dict]]:
    buckets = [[] for _ in range(bins)]
    for score, target in items:
        index = min(bins - 1, int(score * bins))
        buckets[index].append((score, target))
    total = len(items)
    ece = 0.0
    rows = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        confidence = sum(score for score, _ in bucket) / len(bucket)
        accuracy = sum(target for _, target in bucket) / len(bucket)
        weight = len(bucket) / total
        ece += weight * abs(accuracy - confidence)
        rows.append({"bin": f"{index / bins:.1f}-{(index + 1) / bins:.1f}", "n": len(bucket),
                     "mean_score": round(confidence, 4), "empirical_precision": round(accuracy, 4)})
    return ece, rows


def fit_temperature(scores: list[tuple[float, int]]) -> float:
    best_t, best_nll = 1.0, float("inf")
    step = 0.01
    temperature = 0.25
    while temperature <= 10.0:
        value = _nll(scores, temperature)
        if value < best_nll:
            best_t, best_nll = temperature, value
        temperature += step
    return round(best_t, 3)


def apply_temperature(items: list[tuple[float, int]], temperature: float) -> list[tuple[float, int]]:
    calibrated = []
    for score, target in items:
        logit = _logit(score) / temperature
        calibrated.append((1 / (1 + 2.718281828459045 ** (-logit)), target))
    return calibrated


def calibrate(checkpoint_path: Path, data_root: Path, split: str = "val") -> dict:
    scores = collect_scores(checkpoint_path, data_root, split)
    if not scores:
        raise SystemExit("no detections to calibrate; lower the export score threshold")
    ece_before, bins_before = expected_calibration_error(scores)
    temperature = fit_temperature(scores)
    ece_after, bins_after = expected_calibration_error(apply_temperature(scores, temperature))
    applied = ece_after < ece_before
    return {
        "method": "single temperature scaling on logit(score)",
        "temperature": temperature,
        "runtime_temperature": temperature if applied else 1.0,
        "applied": applied,
        "n_detections": len(scores),
        "base_rate": round(sum(tp for _, tp in scores) / len(scores), 4),
        "ece_before": round(ece_before, 4),
        "ece_after": round(ece_after, 4),
        "bins_before": bins_before,
        "bins_after": bins_after,
        "note": ("Temperature improves ECE on this split; applied at runtime."
                 if applied else
                 "Temperature fit NLL but did not improve ECE; runtime keeps raw scores.")
                + " Applies to this split's distribution only; recalibrate after any retrain or domain change.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate detector scores.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="val")
    parser.add_argument("--out", type=Path, default=MODELS / "calibration_v2.json")
    args = parser.parse_args()
    report = calibrate(args.checkpoint, args.data, args.split)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("temperature", "ece_before", "ece_after", "n_detections")}, indent=2))


if __name__ == "__main__":
    main()
