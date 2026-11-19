"""Compare PyTorch evaluation with the exported ONNX runtime.

The model card is generated from PyTorch. The app runs ONNX and applies
temperature scaling plus a review-queue cap. This script checks that the two
paths select the same boxes at the 0.5 threshold and reports the cost of the
UI cap separately.

Usage:
    python -m ml.verify_runtime --checkpoint data/models/det_v2.pt \
        --onnx data/models/det_v2.onnx --data data/dataset/det_v2 --split test
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import aggregate, evaluate_checkpoint, evaluate_image


def _temperature(score: float, temperature: float) -> float:
    import math
    p = min(1 - 1e-6, max(1e-6, score))
    logit = math.log(p / (1 - p)) / temperature
    return 1 / (1 + math.exp(-logit))


def _overlaps(a, b, threshold: float = 0.3) -> bool:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return union > 0 and inter / union > threshold


def run_onnx(onnx_path: Path, data_root: Path, split: str, calibration: Path | None,
             threshold: float, top_k: int | None = None) -> dict:
    import onnxruntime as ort

    from .train import DetectionDataset

    dataset = DetectionDataset(data_root, split, 640)
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    temperature = 1.0
    if calibration and calibration.exists():
        payload = json.loads(calibration.read_text(encoding="utf-8"))
        # Runtime applies runtime_temperature: 1.0 when calibration did not improve ECE.
        temperature = float(payload.get("runtime_temperature", payload.get("temperature", 1.0)))

    images = []
    for tensor, target in dataset:
        boxes, scores, labels = session.run(None, {input_name: tensor[None].numpy()})[:3]
        # Keep the whole score tail: AP is computed before the score threshold,
        # exactly as evaluate_checkpoint does. Filtering here would truncate the
        # precision/recall curve and make the parity comparison meaningless.
        kept = [(box.tolist(), _temperature(float(score), temperature), int(label))
                for box, score, label in zip(boxes, scores.reshape(-1), labels.reshape(-1))]
        kept.sort(key=lambda item: -item[1])
        if top_k is not None:
            capped = []
            for box, score, label in kept:
                if len(capped) >= top_k:
                    break
                if any(_overlaps(box, other[0]) for other in capped):
                    continue
                capped.append((box, score, label))
            kept = capped
        images.append(evaluate_image(
            target["boxes"].tolist(), target["labels"].tolist(),
            [item[0] for item in kept], [item[1] for item in kept],
            [item[2] for item in kept], iou_threshold=0.5))
    sources = [path.stem.split("_")[0] for path, _ in dataset.items]
    return aggregate(images, sources, threshold, 0.5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ONNX runtime parity with PyTorch.")
    parser.add_argument("--checkpoint", type=Path, default=Path("data/models/det_v2b.pt"))
    parser.add_argument("--onnx", type=Path, default=Path("data/models/det_v2.onnx"))
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="test")
    parser.add_argument("--calibration", type=Path, default=Path("data/models/calibration_v2.json"))
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--out", type=Path, default=Path("data/models/runtime_parity_v2.json"),
                        help="write the parity report as JSON (used by the model card)")
    args = parser.parse_args()

    reference = evaluate_checkpoint(args.checkpoint, args.data, args.split, args.threshold)
    raw = run_onnx(args.onnx, args.data, args.split, args.calibration, args.threshold)
    capped = run_onnx(args.onnx, args.data, args.split, args.calibration, args.threshold, top_k=6)

    def block(name, value):
        print(f"{name:16s} mAP {value['map50']:.4f}  P {value['precision']:.4f}  "
              f"R {value['recall']:.4f}  boxes {value['detections']}")

    block("pytorch", reference)
    block("onnx", raw)
    block("onnx + ui cap", capped)
    delta = abs(reference["map50"] - raw["map50"])
    passed = delta <= 0.01
    print(f"mAP delta pytorch -> onnx: {delta:.4f}")
    if args.out:
        import hashlib

        def digest(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

        report = {
            "checkpoint": str(args.checkpoint),
            "checkpoint_sha256": digest(args.checkpoint),
            "onnx": str(args.onnx),
            "onnx_sha256": digest(args.onnx),
            "calibration": str(args.calibration),
            "split": args.split,
            "score_threshold": args.threshold,
            "pytorch": reference,
            "onnx_raw": raw,
            "onnx_with_ui_cap": capped,
            "map_delta": round(delta, 4),
            "ui_cap_cost": round(raw["map50"] - capped["map50"], 4),
            "passed": passed,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    if not passed:
        print("FAIL: ONNX parity drift above 0.01 mAP")
        return 1
    print("PASS: ONNX selects the same boxes within tolerance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
