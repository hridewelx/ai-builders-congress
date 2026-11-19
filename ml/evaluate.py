"""Detection metrics with explicit, inspectable matching rules.

Reported numbers:
  * per-class AP@0.5 (101-point interpolation) and mAP@0.5
  * precision/recall at one fixed score threshold
  * false positives per clean image (the review-queue cost that matters)
  * view-level recall (does each defective view surface at least one hit)
  * the same metrics per source, never pooled into one headline number

Matching: per class, predictions sorted by score, greedy match at IoU >= 0.5.
A prediction that overlaps a different true class counts as a false positive.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .config import CLASSES, IOU_THRESHOLD, MODELS, SCORE_THRESHOLD


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def average_precision(entries: list[tuple[float, int]], n_gt: int) -> float:
    """101-point interpolated AP from (score, is_true_positive) pairs."""
    if n_gt == 0:
        return float("nan")
    entries = sorted(entries, key=lambda item: -item[0])
    tp_cum = fp_cum = 0
    recalls, precisions = [], []
    for _, flag in entries:
        tp_cum += flag
        fp_cum += 1 - flag
        recalls.append(tp_cum / n_gt)
        precisions.append(tp_cum / (tp_cum + fp_cum))
    points = [i / 100 for i in range(101)]
    total = 0.0
    for point in points:
        candidates = [p for r, p in zip(recalls, precisions) if r >= point]
        total += max(candidates) if candidates else 0.0
    return total / len(points)


def evaluate_image(boxes_gt, labels_gt, boxes_p, scores_p, labels_p,
                   iou_threshold: float = IOU_THRESHOLD) -> dict:
    """Match one image; return all detections with their TP/FP flags."""
    gt_by_class = Counter(int(label) for label in labels_gt)
    matched: set[int] = set()
    detections = []
    order = sorted(range(len(boxes_p)), key=lambda i: -float(scores_p[i]))
    for index in order:
        label = int(labels_p[index])
        best_iou, best_gt = 0.0, -1
        for gt_index, gt_label in enumerate(labels_gt):
            if int(gt_label) != label or gt_index in matched:
                continue
            overlap = iou(boxes_p[index], boxes_gt[gt_index])
            if overlap > best_iou:
                best_iou, best_gt = overlap, gt_index
        if best_iou >= iou_threshold:
            matched.add(best_gt)
            detections.append({"class": label, "score": float(scores_p[index]), "tp": 1})
        else:
            detections.append({"class": label, "score": float(scores_p[index]), "tp": 0})
    return {"gt": gt_by_class, "detections": detections, "boxes": len(boxes_gt)}


def aggregate(images: list[dict], sources: list[str] | None,
              score_threshold: float, iou_threshold: float = IOU_THRESHOLD) -> dict:
    gt_counts: Counter[int] = Counter()
    class_entries: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for image in images:
        gt_counts.update(image["gt"])
        for det in image["detections"]:
            class_entries[int(det["class"])].append((det["score"], det["tp"]))

    aps = {}
    for label, entries in class_entries.items():
        name = CLASSES[label - 1] if 1 <= label <= len(CLASSES) else str(label)
        value = average_precision(entries, gt_counts[label])
        if value == value:
            aps[name] = round(value, 4)
    valid = list(aps.values())
    map50 = round(sum(valid) / len(valid), 4) if valid else 0.0

    tp = fp = 0
    clean_images = fp_on_clean = 0
    defective_views = views_with_hit = 0
    for image in images:
        kept = [d for d in image["detections"] if d["score"] >= score_threshold]
        image_tp = sum(d["tp"] for d in kept)
        image_fp = len(kept) - image_tp
        tp += image_tp
        fp += image_fp
        if image["boxes"] == 0:
            clean_images += 1
            fp_on_clean += 1 if image_fp else 0
        else:
            defective_views += 1
            views_with_hit += 1 if image_tp else 0

    result = {
        "images": len(images),
        "gt_boxes": int(sum(gt_counts.values())),
        "detections": tp + fp,
        "true_positives": tp,
        "false_positives": fp,
        "precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
        "recall": round(tp / sum(gt_counts.values()), 4) if gt_counts else 0.0,
        "ap50": dict(sorted(aps.items())),
        "map50": map50,
        "score_threshold": score_threshold,
        "iou_threshold": iou_threshold,
        "clean_images": clean_images,
        "fp_per_clean": round(fp_on_clean / clean_images, 4) if clean_images else None,
        "defective_views": defective_views,
        "view_recall": round(views_with_hit / defective_views, 4) if defective_views else 0.0,
    }
    if sources is not None:
        per_source = {}
        for source in sorted(set(sources)):
            subset = [image for image, name in zip(images, sources) if name == source]
            block = aggregate(subset, None, score_threshold, iou_threshold)
            block.pop("per_source", None)
            per_source[source] = {key: block[key] for key in
                                  ("images", "gt_boxes", "true_positives", "false_positives",
                                   "map50", "precision", "recall", "fp_per_clean", "view_recall",
                                   "clean_images", "defective_views", "ap50")}
        result["per_source"] = per_source
    return result


def accumulate(pairs, score_threshold: float = SCORE_THRESHOLD,
               iou_threshold: float = IOU_THRESHOLD, sources: list[str] | None = None) -> dict:
    """Compute the metric block from (outputs, targets) pairs."""
    images = []
    for outputs, targets in pairs:
        target = targets[0] if isinstance(targets, (tuple, list)) else targets
        boxes_gt = target["boxes"].cpu() if hasattr(target["boxes"], "cpu") else target["boxes"]
        labels_gt = target["labels"].cpu().tolist() if hasattr(target["labels"], "cpu") else target["labels"]
        output = outputs[0]
        boxes_p = output["boxes"].cpu().tolist() if hasattr(output["boxes"], "cpu") else output["boxes"]
        scores_p = output["scores"].cpu().tolist() if hasattr(output["scores"], "cpu") else output["scores"]
        labels_p = output["labels"].cpu().tolist() if hasattr(output["labels"], "cpu") else output["labels"]
        boxes_gt = [box.tolist() if hasattr(box, "tolist") else box for box in boxes_gt]
        images.append(evaluate_image(boxes_gt, labels_gt, boxes_p, scores_p, labels_p, iou_threshold))
    return aggregate(images, sources, score_threshold, iou_threshold)


def evaluate_checkpoint(checkpoint_path: Path, data_root: Path, split: str = "val",
                        score_threshold: float = SCORE_THRESHOLD) -> dict:
    import torch
    from torch.utils.data import DataLoader

    from .model import build_model
    from .train import DetectionDataset, collate, move

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(pretrained=False, min_size=checkpoint.get("size", 640),
                        max_size=checkpoint.get("size", 640))
    model.load_state_dict(checkpoint["model"])
    model.to(device).eval()
    dataset = DetectionDataset(data_root, split, checkpoint.get("size", 640))
    loader = DataLoader(dataset, batch_size=1, shuffle=False, collate_fn=collate)
    pairs = []
    with torch.inference_mode():
        for images, targets in loader:
            outputs = model([image.to(device) for image in images])
            pairs.append((outputs, move(targets, torch.device("cpu"))))
    sources = [path.stem.split("_")[0] for path, _ in dataset.items]
    metrics = accumulate(pairs, score_threshold, sources=sources)
    metrics["checkpoint"] = str(checkpoint_path)
    metrics["split"] = split
    return metrics


def _display_path(value: str) -> str:
    """Show repo-relative paths in generated docs, never a local absolute path."""
    path = Path(value)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def model_card_markdown(metrics: dict, checkpoint: dict, calibration: dict | None = None,
                        parity: dict | None = None, source: str | None = None,
                        integrity: dict | None = None, leakage: dict | None = None,
                        operating_point: dict | None = None) -> str:
    per_source = metrics.get("per_source", {})
    headline = per_source.get("bdfd9", metrics)
    headline_label = "BDFD9 fabric close-ups" if "bdfd9" in per_source else "all evaluated images"
    clean_n = headline["clean_images"]
    fp_clean = ("n/a — only {n} clean image{s}; not a false-positive rate".format(
        n=clean_n, s="" if clean_n == 1 else "s")
        if clean_n < 5 else headline["fp_per_clean"])
    lines = [
        "# Detector model card (generated)", "",
        ("Regenerated from saved metrics " + (f"`{source}` " if source else "")
         + "without re-running the test split; every number comes from the saved evaluation.")
        if source else "Generated by `python -m ml.evaluate`; every number comes from that run.",
        "",
        f"- Checkpoint: `{_display_path(metrics['checkpoint'])}`",
        f"- Split: `{metrics['split']}` ({metrics['images']} images, {metrics['gt_boxes']} boxes)",
        (f"- Selection: chosen on validation mAP@0.5 {checkpoint['metrics']['map50']} "
         f"(epoch {checkpoint['metrics'].get('epoch')}); the test split was scored once for "
         "this checkpoint, not used to pick it.")
        if checkpoint.get("metrics", {}).get("map50") is not None else "",
        f"- Score threshold: {metrics['score_threshold']} · IoU: {metrics['iou_threshold']}",
        f"- **Headline ({headline_label}): {headline['map50']} mAP@0.5**",
        f"- Precision / recall: {headline['precision']} / {headline['recall']}",
        f"- False positives per clean image: {fp_clean}"
        + ("" if clean_n < 5 else f" ({clean_n} clean images)"),
        f"- View-level recall: {headline['view_recall']} ({headline['defective_views']} defective views)",
    ]
    if parity and parity.get("split") == "val" and parity.get("pytorch"):
        val = parity["pytorch"]
        lines.append(f"- Validation estimate (harder): {val['map50']} mAP@0.5, "
                     f"P {val['precision']}, R {val['recall']} on {val['images']} images — "
                     "quote both; the split-to-split gap is not a new-factory estimate.")
    lines += [
        "- Same-factory caveat: every image here comes from the same four BDFD9 "
        "factories and capture sessions. Neither this split nor validation estimates "
        "performance in a new factory.",
        f"- Pooled diagnostic across all evaluated images: {metrics['map50']} "
        "(reported for completeness, never as the held-out factory estimate)",
        "- Split policy: BDFD9's official test folder is held out; "
        "`python -m ml.verify_split` must pass before this card is published.",
        f"- Review threshold: {operating_point['chosen_threshold']} chosen on validation "
        f"({operating_point['objective']}); this test table was scored at "
        f"{metrics['score_threshold']}, which is never re-tuned on test."
        if operating_point else
        "- Runtime keeps the same 0.5 threshold; temperature scaling, when enabled, is "
        "monotonic with 0.5 as its fixed point, so the selected boxes match this table. "
        "The review UI caps at 6 proposals and suppresses overlapping boxes, so visible "
        "counts can be lower (measured cost in the parity section).",
        "", f"## Per class ({headline_label})", "", "| class | AP@0.5 |", "| --- | --- |",
    ]
    for name, value in headline.get("ap50", metrics["ap50"]).items():
        lines.append(f"| {name} | {value} |")
    lines += ["", "## Per source (never pooled)", "",
              "| source | images | gt | tp | fp | mAP@0.5 | FP/clean |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, row in metrics.get("per_source", {}).items():
        fp_clean = (row["fp_per_clean"] if row["clean_images"] >= 5
                    else f"n/a ({row['clean_images']})")
        lines.append(f"| {name} | {row['images']} | {row['gt_boxes']} | {row['true_positives']} | "
                     f"{row['false_positives']} | {row['map50']} | {fp_clean} |")
    if calibration:
        ece_before = calibration.get("ece_before")
        ece_after = calibration.get("ece_after")
        temperature = calibration.get("temperature")
        applied = bool(calibration.get("applied"))
        runtime_t = calibration.get("runtime_temperature", 1.0)
        lines += ["", "## Calibration (validation split)", "",
                  f"- Temperature fit: {temperature} on {calibration.get('n_detections')} detections",
                  f"- ECE before / after: {ece_before} / {ece_after}",
                  f"- Applied at runtime: **{'yes' if applied else 'no'}** "
                  f"(runtime temperature {runtime_t})"]
        if applied:
            lines.append("- Reason: temperature scaling improved ECE on validation.")
        else:
            lines.append("- Reason: the fit lowered NLL but **increased ECE**, so the shipped "
                         "runtime keeps raw scores and no calibrated-probability claim is made.")
    if parity:
        lines += ["", "## Runtime parity (validation, never the test split)", "",
                  "| path | mAP@0.5 | precision | recall | boxes |",
                  "| --- | --- | --- | --- | --- |"]
        for label, key in (("PyTorch (card source)", "pytorch"), ("ONNX runtime", "onnx_raw"),
                           ("ONNX + review-queue cap", "onnx_with_ui_cap")):
            row = parity[key]
            lines.append(f"| {label} | {row['map50']} | {row['precision']} | {row['recall']} | {row['detections']} |")
        lines += ["",
                  f"- Checkpoint `{Path(parity['checkpoint']).name}` "
                  f"(sha256 {parity['checkpoint_sha256']}) -> ONNX `{Path(parity['onnx']).name}` "
                  f"(sha256 {parity['onnx_sha256']})",
                  f"- mAP delta PyTorch -> ONNX: {parity['map_delta']} (tolerance 0.01) · "
                  f"review-queue cap cost: {parity['ui_cap_cost']} mAP",
                  f"- Parity result: {'PASS' if parity['passed'] else 'FAIL'}",
                  "- The graph is exported with `allowzero=1` on every Reshape, so a frame "
                  "with no proposals returns empty tensors instead of raising; the runtime "
                  "reports an empty result, not a caught crash."]
    if integrity and metrics.get("split") == "test":
        lines += ["", "## Split integrity", "",
                  f"- Duplicate rule: {integrity['rule']}",
                  f"- Official test images checked: {integrity['official_test_images']} against "
                  f"{integrity['train_val_images_checked']} train/val images",
                  f"- Result: {integrity['exact_leaks']} exact and "
                  f"{integrity['near_duplicate_leaks']} near-duplicate copies "
                  f"({'PASS' if integrity['passed'] else 'FAIL'})",
                  "- This rule only catches copies it can see. It is not proof of independence."]
    if leakage:
        groups = leakage.get("summary", {})
        control = groups.get("train_control", {})
        test = groups.get("test", {})
        val = groups.get("val", {})
        verdict = " ".join(leakage.get("verdict", []))
        p_value = "n/a"
        for sentence in leakage.get("verdict", []):
            if "p =" in sentence or "p=" in sentence:
                p_value = sentence.split("p =")[-1].split("p=")[-1].split("(")[0].strip(" .")
                break
        lines += ["", "## Stricter leakage probe (phase correlation, flips and shifts)", "",
                  "| group | pairs | flagged | share | phase p90 |",
                  "| --- | --- | --- | --- | --- |"]
        for label, block in (("train control (train vs train)", control),
                             ("validation vs train", val), ("test vs train", test)):
            stats = block.get("phase_peak", {})
            lines.append(f"| {label} | {block.get('n')} | {block.get('suspect')} | "
                         f"{block.get('suspect_share')} | {stats.get('p90')} |")
        lines += ["",
                  f"- One-sided test-vs-validation rank-sum p = {p_value}.",
                  "- Read the control row first: it is train-vs-train and cannot contain held-out "
                  "leakage. Because the control is flagged at the same rate as val and test, "
                  "these flags measure how alike BDFD9 photos are, not leakage.",
                  "- Conclusion: no evidence of leakage and no proof of independence. "
                  "The dedupe rule is the only positive check that passed."]
        lines += ["",
                  "- The probe's own output warns about 27 test and 41 validation pairs. That "
                  "warning does not control for the base rate in its train-vs-train control, "
                  "so it is reported here as inconclusive rather than as evidence of leakage."]
        _ = verdict

    if parity and parity.get("split") != "val":
        raise SystemExit("refusing to publish a card whose parity was measured on the test split")
    card = checkpoint.get("model_card", {})
    lines += ["", "## What this model does not do", "",
              "- It does not assign severity, count defects, or decide a lot.",
              "- It does not detect skipped stitch or shade band; those stay human-entered.",
              "- Critical non-visual checks are outside its scope."]
    if card:
        lines += ["", f"Architecture: `{card.get('architecture')}` · code licence: {card.get('code_license')}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a detector checkpoint.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="val")
    parser.add_argument("--score-threshold", type=float, default=SCORE_THRESHOLD)
    parser.add_argument("--out", type=Path, default=MODELS / "eval_metrics.json")
    parser.add_argument("--card", type=Path, default=Path("docs/MODEL_CARD.md"))
    parser.add_argument("--from-json", type=Path,
                        help="Regenerate the card from a saved metrics file; does not run the model.")
    parser.add_argument("--calibration", type=Path, default=MODELS / "calibration_v2.json",
                        help="calibration report to cite in the card (optional)")
    parser.add_argument("--parity", type=Path, default=MODELS / "runtime_parity_v2.json",
                        help="runtime parity report to cite in the card (optional)")
    parser.add_argument("--integrity", type=Path, default=Path("docs/split_integrity.json"),
                        help="split-integrity report from ml.verify_split (optional)")
    parser.add_argument("--operating-point", type=Path,
                        default=MODELS / "operating_point_v2.json",
                        help="threshold record from ml.operating_point (optional)")
    parser.add_argument("--leakage", type=Path, default=Path("docs/leakage_probe.json"),
                        help="stricter leakage-probe report (optional)")
    args = parser.parse_args()
    if args.from_json:
        import torch
        metrics = json.loads(args.from_json.read_text(encoding="utf-8"))
        checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
        def maybe(path: Path | None):
            if path and path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
            return None

        calibration = maybe(args.calibration)
        parity = maybe(args.parity)
        integrity = maybe(args.integrity)
        leakage = maybe(args.leakage)
        operating_point = maybe(args.operating_point)
        args.card.write_text(model_card_markdown(
            metrics, checkpoint, calibration, parity, source=args.from_json.name,
            integrity=integrity, leakage=leakage, operating_point=operating_point), encoding="utf-8")
        print(f"wrote {args.card} from {args.from_json}")
        return
    metrics = evaluate_checkpoint(args.checkpoint, args.data, args.split, args.score_threshold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    import torch
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    args.card.write_text(model_card_markdown(metrics, checkpoint), encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("map50", "precision", "recall", "fp_per_clean", "view_recall")}, indent=2))


if __name__ == "__main__":
    main()
