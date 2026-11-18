# ml/ — model workstream (owner: Hridoy, GPU)

Only this folder and `app/services/vision.py` are GPU work. Everything else must
run on a CPU-only laptop, and the demo must keep working with **no model files
present** (the current numpy autoencoder is the fallback).

The frozen interface every other stream depends on:

```python
detect(image: np.ndarray) -> {
    "proposals": [{"type": str, "score": float, "box": [x1, y1, x2, y2], "raw_error": float}],
    "heat_png": bytes, "model": str, "threshold": float, "calibrated": bool,
    "quality": {...}, "error": str | None,
}
```

## Planned files (T1.1–T1.7)

| File | Purpose | Acceptance |
|---|---|---|
| `dataset.py` | GPU training set assembly on top of `scripts/build_dataset.py` | deterministic split, no seed leakage |
| `train.py` | convolutional patch autoencoder + defect-type head, mixed precision | reproducible from a config file, checkpoint saved |
| `evaluate.py` | per-class precision/recall, FP views, IoU, synthetic vs real split | numbers produced by the script only |
| `calibrate.py` | temperature/Platt scaling, reliability diagram, ECE | `calibrated: True` only when ECE < 0.1 |
| `export_onnx.py` | fp32 ONNX export + parity test | max abs diff < 1e-3, CPU < 0.8 s/photo |

Artifacts land in `data/models/` (git-ignored). Commit the ONNX file, the model
card and the metrics — never a hand-written number.

## Non-negotiables

- No fabricated accuracy, no "ISO compliant" claim, no invented AQL table.
- Scores are not probabilities unless `calibrate.py` has run and ECE is reported.
- The model never outputs a count, a severity or a decision. It only proposes.
