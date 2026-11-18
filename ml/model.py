"""Detector model definition.

License-clean baseline: torchvision Faster R-CNN with a MobileNetV3-Large FPN
backbone (BSD-3-Clause code, ImageNet weights released by PyTorch). It is not
the RF-DETR default in the design note; RF-DETR is kept as the upgrade path
because its training stack could not be verified on this Python/torch build.
Any swap must keep the same dataset contract and the same output shape.
"""
from __future__ import annotations

from .config import CLASSES


def build_model(pretrained: bool = True, min_size: int = 640, max_size: int = 640):
    """Return a detection model with len(CLASSES) + 1 output classes."""
    from torchvision.models.detection import (
        FasterRCNN_MobileNet_V3_Large_FPN_Weights,
        fasterrcnn_mobilenet_v3_large_fpn,
    )
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

    weights = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT if pretrained else None
    model = fasterrcnn_mobilenet_v3_large_fpn(
        weights=weights,
        weights_backbone=None,
        min_size=min_size,
        max_size=max_size,
    )
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, len(CLASSES) + 1)
    return model


def describe() -> dict:
    """Model card facts that the training script records verbatim."""
    return {
        "architecture": "fasterrcnn_mobilenet_v3_large_fpn",
        "code_license": "BSD-3-Clause (torchvision)",
        "weights": "COCO-pretrained torchvision weights",
        "classes": CLASSES,
        "severity_head": None,
        "outputs": "boxes, scores, labels",
        "note": "Detector proposes boxes only. Severity and the lot outcome are human/engine decisions.",
    }
