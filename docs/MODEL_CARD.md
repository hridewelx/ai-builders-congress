# Detector model card (generated)

Regenerated from saved metrics `eval_test_v2.json` without re-running the test split; every number comes from the saved evaluation.

- Checkpoint: `data/models/det_v2b.pt`
- Split: `test` (64 images, 76 boxes)
- Score threshold: 0.5 · IoU: 0.5
- **Headline (BDFD9 fabric close-ups): 0.9474 mAP@0.5**
- Precision / recall: 0.7761 / 0.8667
- False positives per clean image: n/a — only 1 clean image; not a false-positive rate
- View-level recall: 0.878 (41 defective views)
- Pooled diagnostic across all evaluated images: 0.9561 (reported for completeness, never as the held-out factory estimate)
- Split policy: BDFD9's official test folder is held out; `python -m ml.verify_split` must pass before this card is published.
- Runtime keeps the same 0.5 threshold; temperature scaling, when enabled, is monotonic with 0.5 as its fixed point, so the selected boxes match this table. The review UI caps at 6 proposals and suppresses overlapping boxes, so visible counts can be lower (measured cost in the parity section).

## Per class (BDFD9 fabric close-ups)

| class | AP@0.5 |
| --- | --- |
| dropped_stitch | 0.9822 |
| hole | 0.9738 |
| needle_line | 0.8336 |
| oil_stain | 1.0 |

## Per source (never pooled)

| source | images | gt | tp | fp | mAP@0.5 | FP/clean |
| --- | --- | --- | --- | --- | --- | --- |
| bdfd9 | 42 | 60 | 52 | 15 | 0.9474 | n/a (1) |
| staged | 22 | 16 | 16 | 0 | 1.0 | 0.0 |

## Calibration (validation split)

- Temperature fit: 0.87 on 222 detections
- ECE before / after: 0.1061 / 0.1179
- Applied at runtime: **no** (runtime temperature 1.0)
- Reason: the fit lowered NLL but **increased ECE**, so the shipped runtime keeps raw scores and no calibrated-probability claim is made.

## Runtime parity (validation, never the test split)

| path | mAP@0.5 | precision | recall | boxes |
| --- | --- | --- | --- | --- |
| PyTorch (card source) | 0.7479 | 0.7412 | 0.7326 | 85 |
| ONNX runtime | 0.7475 | 0.7412 | 0.7326 | 85 |
| ONNX + review-queue cap | 0.7326 | 0.7683 | 0.7326 | 82 |

- Checkpoint `det_v2b.pt` (sha256 9b430c4c9786e3ee) -> ONNX `det_v2.onnx` (sha256 11863b97e42817a7)
- mAP delta PyTorch -> ONNX: 0.0004 (tolerance 0.01) · review-queue cap cost: 0.0149 mAP
- Parity result: PASS

## Split integrity

- `ml.verify_split`: 109 official BDFD9 test images compared against 450 train/val images — 0 exact and 0 near-duplicate leaks.
- The official test folder is never trained on, never used for threshold selection or calibration, and is evaluated once per model version.
- The validation split is the honest 'harder' estimate to quote alongside this one.

## What this model does not do

- It does not assign severity, count defects, or decide a lot.
- It does not detect skipped stitch or shade band; those stay human-entered.
- Critical non-visual checks are outside its scope.

Architecture: `fasterrcnn_mobilenet_v3_large_fpn` · code licence: BSD-3-Clause (torchvision)
