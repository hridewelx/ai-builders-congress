# ml/ — model workstream

Only this folder and `app/services/vision.py` / `app/services/detector.py` are
model work. Everything else must run on a CPU-only laptop, and the demo must
keep working with **no model files present** (the numpy autoencoder is the
fallback).

The frozen interface every other stream depends on:

```python
detect(image: np.ndarray) -> {
    "proposals": [{"type": str, "score": float, "box": [x1, y1, x2, y2], "raw_error": float}],
    "heat_png": bytes, "model": str, "threshold": float, "calibrated": bool,
    "quality": {...}, "note": str,
}
```

## What is built

| File | Purpose | Status |
|---|---|---|
| `data.py` | BDFD9 + staged set -> one canonical YOLO set; SHA-256/dHash dedupe; grouped split | done |
| `model.py` | torchvision Faster R-CNN + MobileNetV3-Large FPN (BSD-3-Clause) | done |
| `train.py` | GPU training, AMP, cosine LR, per-epoch validation | done |
| `evaluate.py` | per-class AP@0.5, P/R, FP per clean view, view recall, per-source block | done |
| `calibrate.py` | single-temperature scaling, ECE before/after | done |
| `export_onnx.py` | fp32 ONNX export + parity check against PyTorch | done |
| `infer.py` | CLI: boxes on image files, optional annotated PNG | done |

`app/services/detector.py` selects the backend. `LOTLINE_DETECTOR=onnx` enables
the trained model; anything else (the default) keeps the numpy baseline.

## Reproduce

```bash
PY=C:/Users/Hridoy_/AppData/Local/Python/pythoncore-3.14-64/python.exe

# 1. data (BDFD9 zip from data.mendeley.com/datasets/z49cc7zvfc/1, CC BY 4.0)
$PY -m ml.data build \
  --source staged=data/dataset/v1 --licence generated \
  --source bdfd9=data/raw/bdfd9/BDFD9 --licence "CC BY 4.0" \
  --out data/dataset/det_v1

# 2. train (GPU; use --workers 0 on Windows)
$PY -m ml.train --data data/dataset/det_v1 --epochs 6 --batch 4 --workers 0

# 3. measure, calibrate, export
$PY -m ml.evaluate --score-threshold 0.5 --card docs/MODEL_CARD.md
$PY -m ml.calibrate
$PY -m ml.export_onnx
```

Artifacts land in `data/models/` (git-ignored). Commit the model card and the
metrics, never a hand-written number.

## Result of the 18 Nov 2026 run

Dataset 514 images / 676 boxes (412 train, 102 val), classes `hole`,
`oil_stain`, `needle_line`, `dropped_stitch`. Validation at score 0.5:

| mAP@0.5 | Precision | Recall | View recall | FP / clean view |
|---|---|---|---|---|
| 0.867 | 0.823 | 0.817 | 0.88 | 0.00 (2 clean images only) |

Per class AP@0.5: oil_stain 0.99, dropped_stitch 0.93, hole 0.78, needle_line 0.76.

Read the caveats in `docs/MODEL_CARD.md`. The validation split is small and the
two clean images are not enough to claim a false-positive rate; BDFD9 also
shares fabric/session context between splits, so these numbers are optimistic
for a new factory.

## ONNX runtime note

`torch.onnx` cannot reshape a zero-row ROI tensor, so ORT raises when the
detector finds nothing. `app/services/detector.py` treats exactly that failure
as "no proposals", which is the correct answer for a clean view. Any other ORT
failure falls back to the numpy baseline and records that in `note`.

## Non-negotiables

- No fabricated accuracy, no "ISO compliant" claim, no invented AQL table.
- Scores are not probabilities unless `calibrate.py` has run and ECE is reported.
- The model never outputs a count, a severity or a decision. It only proposes.
