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
from .model_card import write as write_card


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





TEST_SPLIT_LOCK = MODELS / "eval_test_v2.json"


def guard_test_once(out: Path, force: bool, reason: str) -> None:
    """The test split is scored once. A second score needs a stated reason.

    ``ml.pipeline`` refuses a repeat too; this is the same rule at the point where
    the measurement is actually taken, so the CLI cannot sidestep it.
    """
    existing = [path for path in (out, TEST_SPLIT_LOCK) if path.exists()]
    if not existing:
        return
    if not force:
        raise SystemExit(
            f"the test split is already scored ({existing[0]}); re-scoring it needs "
            "--force --reason \"why\"")
    if len(reason.strip()) < 20:
        raise SystemExit("--force needs --reason with a real explanation (20+ characters)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a detector checkpoint.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--split", default="val")
    parser.add_argument("--score-threshold", type=float, default=SCORE_THRESHOLD)
    parser.add_argument("--out", type=Path, default=MODELS / "eval_metrics.json")
    parser.add_argument("--card", type=Path, default=Path("docs/MODEL_CARD.md"))
    parser.add_argument("--card-json", type=Path, default=MODELS / "model_card_trained.json",
                        help="the explainer page reads this; written with the markdown")
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
    parser.add_argument("--reliability", type=Path, default=MODELS / "reliability_v2.json",
                        help="reliability bins from ml.reliability (optional)")
    parser.add_argument("--leakage", type=Path, default=Path("docs/leakage_probe.json"),
                        help="stricter leakage-probe report (optional)")
    parser.add_argument("--force", action="store_true",
                        help="score the test split again even though a result exists")
    parser.add_argument("--reason", default="",
                        help="why the test split is being scored a second time (required with --force)")
    args = parser.parse_args()
    if args.split == "test" and not args.from_json:
        guard_test_once(args.out, args.force, args.reason)
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
        reliability = maybe(args.reliability)
        write_card(args.card, args.card_json, metrics, checkpoint, calibration, parity,
                   operating_point=operating_point, source=args.from_json.name,
                   integrity=integrity, leakage=leakage, reliability=reliability)
        print(f"wrote {args.card} and {args.card_json} from {args.from_json}")
        return
    metrics = evaluate_checkpoint(args.checkpoint, args.data, args.split, args.score_threshold)
    if args.force and args.reason.strip():
        metrics["rescored_reason"] = args.reason.strip()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    import torch
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    write_card(args.card, args.card_json, metrics, checkpoint)
    print(json.dumps({k: metrics[k] for k in ("map50", "precision", "recall", "fp_per_clean", "view_recall")}, indent=2))


if __name__ == "__main__":
    main()
