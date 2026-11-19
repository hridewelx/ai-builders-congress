"""Render the machine-readable card the explainer page reads."""
from __future__ import annotations

from pathlib import Path


def json_card(metrics: dict, checkpoint: dict, calibration: dict | None = None,
              parity: dict | None = None, operating_point: dict | None = None,
              reliability: dict | None = None) -> dict:
    """The same facts as the markdown, in the shape the explainer page reads.

    The page shows two rows: the model behind the seeded demo history, and the
    model that serves new uploads. This object is the second one, which is why
    every field is prefixed `live_`. Writing it here keeps the numbers in one
    place instead of retyping them in the seeder.
    """
    from ..config import CLASSES, MODEL_NAME, MODEL_VERSION

    parity = parity or {}
    per_class = {name: row.get("ap50") for name, row in (metrics.get("per_class") or {}).items()}
    headline = (metrics.get("per_source") or {}).get("bdfd9")
    if headline and not per_class:
        per_class = dict(headline.get("ap50") or {})
    if headline is None:
        headline = {key: metrics.get(key) for key in
                    ("images", "gt_boxes", "map50", "precision", "recall")}
    calibration_note = "none — calibration was fitted and rejected (ECE rose)"
    temperature = 1.0
    if calibration:
        temperature = calibration.get("runtime_temperature", 1.0)
        if calibration.get("applied"):
            calibration_note = (f"temperature {calibration.get('temperature')} applied "
                                f"(ECE {calibration.get('ece_before')} -> {calibration.get('ece_after')})")
        else:
            calibration_note = (f"not applied — temperature {calibration.get('temperature')} raised "
                                f"ECE {calibration.get('ece_before')} -> {calibration.get('ece_after')}; "
                                "scores are raw")
    return {
        "card": "docs/MODEL_CARD.md",
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "classes": list(CLASSES),
        "live_model": MODEL_NAME,
        "live_labels": "supervised: " + ", ".join(CLASSES),
        "live_training": "BDFD9 (CC BY 4.0) train/valid plus staged panels; official test held out",
        "live_domains": "BDFD9 factory fabric close-ups from four Bangladeshi factories, plus staged knit panels",
        "live_device": "CPU, in-process through ONNX Runtime",
        "live_calibration": calibration_note,
        "live_threshold": (operating_point or {}).get("chosen_threshold"),
        # Lead with the BDFD9-only headline, never the pooled diagnostic: the
        # card says the pooled number must not be quoted, so the page cannot
        # quote it either.
        "live_evaluation": {
            "split": metrics.get("split"),
            "images": headline.get("images"),
            "gt_boxes": headline.get("gt_boxes"),
            "map50": headline.get("map50"),
            "precision": headline.get("precision"),
            "recall": headline.get("recall"),
            "per_class_ap50": per_class,
            "source": "bdfd9" if headline else "pooled",
            "pooled_diagnostic": {"map50": metrics.get("map50"), "images": metrics.get("images")},
        },
        "live_reliability": ({"ece": reliability.get("ece"),
                              "detections": reliability.get("detections"),
                              "split": reliability.get("split"),
                              "top_band": next((row for row in reversed(reliability.get("bins", []))
                                                if row.get("count")), None)}
                             if reliability else None),
        "live_parity": {"map50": (parity.get("onnx_raw") or {}).get("map50"),
                        "delta": parity.get("map_delta"), "split": parity.get("split")},
        "artifacts": {"onnx_sha256": parity.get("onnx_sha256"),
                      "checkpoint_sha256": parity.get("checkpoint_sha256"),
                      "checkpoint": Path(parity["checkpoint"]).name if parity.get("checkpoint") else None},
        "runtime_temperature": temperature,
    }
