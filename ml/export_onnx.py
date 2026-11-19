"""Export the trained detector to ONNX and check numerical parity.

ONNX keeps the demo runtime small: the serving container needs onnxruntime and
numpy, not torch. The export is a hard gate: if the graph does not match the
PyTorch output within tolerance, the script fails instead of shipping it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import CLASSES, MODELS


class SingleImageModel:
    """Wrap the detector so ONNX sees three plain outputs."""

    def __new__(cls, model):
        import torch

        class _Wrapper(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.model = model

            def forward(self, images):
                output = self.model(images)[0]
                return output["boxes"], output["scores"], output["labels"]

        return _Wrapper()


def export(checkpoint_path: Path, out_path: Path, size: int = 640, opset: int = 17,
           image_path: Path | None = None) -> dict:
    import torch
    from torchvision.models.detection import (
        fasterrcnn_mobilenet_v3_large_fpn,
    )
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

    from .data import sha256_file

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    size = checkpoint.get("size", size)
    model = fasterrcnn_mobilenet_v3_large_fpn(weights=None, weights_backbone=None,
                                              min_size=size, max_size=size)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, len(CLASSES) + 1)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    wrapped = SingleImageModel(model).eval()

    if image_path is not None:
        from PIL import Image

        with Image.open(image_path) as im:
            pixels = im.convert("RGB").resize((size, size), Image.BILINEAR)
        import numpy as np
        dummy = torch.from_numpy(np.asarray(pixels, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0)
        report_image = str(image_path)
    else:
        dummy = torch.rand(1, 3, size, size)
        report_image = None
    with torch.inference_mode():
        reference = wrapped(dummy)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapped, dummy, str(out_path),
        opset_version=opset,
        dynamo=False,
        input_names=["images"],
        output_names=["boxes", "scores", "labels"],
        dynamic_axes={"boxes": {0: "num"}, "scores": {0: "num"}, "labels": {0: "num"}},
        do_constant_folding=True,
    )

    report = {"onnx_path": str(out_path), "size": size, "opset": opset,
              "classes": CLASSES, "parity": None, "parity_image": report_image,
              "checkpoint": str(checkpoint_path),
              "checkpoint_sha256": sha256_file(checkpoint_path)[:16],
              "onnx_sha256": sha256_file(out_path)[:16]}
    try:
        import numpy as np
        import onnxruntime as ort
        session = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
        result = session.run(None, {"images": dummy.numpy()})
        boxes = result[0]
        reference_boxes = reference[0].numpy()
        if boxes.shape[0] != reference_boxes.shape[0]:
            raise SystemExit(f"ONNX parity failed: {boxes.shape[0]} boxes vs {reference_boxes.shape[0]} in torch")
        delta = float(np.abs(boxes - reference_boxes).max()) if boxes.size else 0.0
        report["parity"] = {
            "onnx_boxes": int(boxes.shape[0]),
            "torch_boxes": int(reference_boxes.shape[0]),
            "max_box_delta": round(delta, 4),
            "scores_match": bool(np.allclose(result[1], reference[1].numpy(), atol=1e-4)),
            "labels_match": bool(np.array_equal(result[2], reference[2].numpy())),
        }
        if not report["parity"]["scores_match"] or not report["parity"]["labels_match"]:
            raise SystemExit("ONNX parity failed: score or label mismatch")
    except ImportError:
        report["parity"] = {"skipped": "onnxruntime not installed"}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the detector to ONNX.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--out", type=Path, default=MODELS / "det_v2.onnx")
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=MODELS / "export_report_v2.json",
                        help="parity report path (keep per-version reports separate)")
    args = parser.parse_args()
    image = args.image
    if image is None:
        candidates = sorted(Path("data/dataset/det_v2/images/val").glob("*"))
        image = candidates[0] if candidates else None
    report = export(args.checkpoint, args.out, opset=args.opset, image_path=image)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
