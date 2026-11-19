"""Torch dataset and training loop for the Lotline detector.

Usage:
    python -m ml.train --data data/dataset/det_v1 --epochs 5 --batch 4

The script refuses to run without a GPU unless --device cpu is passed, because
CPU training of a detector is not a realistic plan. Every run writes a
checkpoint and a metrics file; nothing is hand-written.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from PIL import Image

from .config import CLASSES, IMG_SIZE, MODELS, SEED
from .model import build_model, describe

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DetectionDataset:
    """Minimal YOLO dataset: RGB image, boxes in pixels, labels 1..N."""

    def __init__(self, root: Path, split: str, size: int = IMG_SIZE, augment: bool = False):
        import torch

        self.torch = torch
        self.size = size
        self.augment = augment
        self.items: list[tuple[Path, Path]] = []
        images = root / "images" / split
        for path in sorted(images.iterdir()):
            if path.suffix.lower() in IMAGE_EXTS:
                self.items.append((path, root / "labels" / split / f"{path.stem}.txt"))
        if not self.items:
            raise SystemExit(f"no images in {images}")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int):
        torch = self.torch
        image_path, label_path = self.items[index]
        with Image.open(image_path) as im:
            image = im.convert("RGB")
            width, height = image.size
        box_rows: list[list[float]] = []
        labels: list[int] = []
        if label_path.exists():
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                cls, cx, cy, bw, bh = int(parts[0]), *(float(v) for v in parts[1:])
                x1 = max(0.0, (cx - bw / 2) * width)
                y1 = max(0.0, (cy - bh / 2) * height)
                x2 = min(float(width), (cx + bw / 2) * width)
                y2 = min(float(height), (cy + bh / 2) * height)
                if x2 - x1 < 2 or y2 - y1 < 2:
                    continue
                box_rows.append([x1, y1, x2, y2])
                labels.append(cls + 1)

        scale_x = self.size / width
        scale_y = self.size / height
        image = image.resize((self.size, self.size), Image.BILINEAR)
        box_rows = [[b[0] * scale_x, b[1] * scale_y, b[2] * scale_x, b[3] * scale_y] for b in box_rows]

        if self.augment:
            image, box_rows = self._augment(image, box_rows, width, height, scale_x, scale_y)

        arr = torch.ByteTensor(list(image.tobytes())).view(self.size, self.size, 3)
        tensor = arr.permute(2, 0, 1).float().div(255.0)
        target = {
            "boxes": torch.tensor(box_rows, dtype=torch.float32).reshape(-1, 4),
            "labels": torch.tensor(labels, dtype=torch.int64),
            "image_id": torch.tensor([index]),
        }
        return tensor, target

    def _augment(self, image, boxes, width, height, scale_x, scale_y):
        """Photometric jitter plus a horizontal flip; boxes follow the flip."""
        import random as _random

        from PIL import ImageEnhance

        if _random.random() < 0.5:
            image = ImageEnhance.Brightness(image).enhance(_random.uniform(0.8, 1.2))
            image = ImageEnhance.Contrast(image).enhance(_random.uniform(0.8, 1.2))
            image = ImageEnhance.Color(image).enhance(_random.uniform(0.85, 1.15))
        if _random.random() < 0.5:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
            flipped = []
            for x1, y1, x2, y2 in boxes:
                flipped.append([self.size - x2, y1, self.size - x1, y2])
            boxes = flipped
        return image, boxes


def collate(batch):
    return tuple(zip(*batch))


def move(targets, device):
    import torch
    out = []
    for target in targets:
        out.append({k: v.to(device) if torch.is_tensor(v) else v for k, v in target.items()})
    return out


def train(args) -> dict:
    import torch
    from torch.utils.data import DataLoader

    device = torch.device(args.device)
    if device.type != "cuda" and not args.allow_cpu:
        raise SystemExit("refusing to train a detector on CPU; pass --allow-cpu to override")
    random.seed(SEED)
    torch.manual_seed(SEED)

    root = Path(args.data)
    train_ds = DetectionDataset(root, "train", args.size, augment=True)
    val_ds = DetectionDataset(root, "val", args.size, augment=False)
    print(f"train {len(train_ds)} images · val {len(val_ds)} images · device {device}")

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                              collate_fn=collate, num_workers=args.workers, pin_memory=device.type == "cuda")
    val_loader = DataLoader(val_ds, batch_size=1, shuffle=False,
                            collate_fn=collate, num_workers=0)

    model = build_model(pretrained=not args.no_pretrained, min_size=args.size, max_size=args.size)
    if getattr(args, "init", None):
        initial = torch.load(args.init, map_location="cpu", weights_only=False)
        if initial.get("size", args.size) != args.size:
            raise SystemExit(f"checkpoint size {initial.get('size')} does not match --size {args.size}")
        model.load_state_dict(initial["model"])
        print(f"initialized from {args.init}")
    model.to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    history = []
    best_map = -1.0
    MODELS.mkdir(parents=True, exist_ok=True)
    checkpoint = Path(args.out) if getattr(args, "out", None) else MODELS / "det_v1.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        started = time.time()
        for step, (images, targets) in enumerate(train_loader, 1):
            images = [image.to(device) for image in images]
            targets = move(targets, device)
            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                loss_dict = model(images, targets)
                loss = sum(value for value in loss_dict.values())
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(params, 5.0)
            scaler.step(optimizer)
            scaler.update()
            running += float(loss.detach())
            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step}/{len(train_loader)} loss {running / step:.3f}")
        scheduler.step()
        sources = [path.stem.split('_')[0] for path, _ in val_ds.items]
        metrics = evaluate_split(model, val_loader, device, args.score_threshold, sources)
        metrics.update({"epoch": epoch, "train_loss": running / max(1, len(train_loader)),
                        "seconds": round(time.time() - started, 1)})
        history.append(metrics)
        fp_clean = (f"{metrics['fp_per_clean']:.2f}" if metrics["fp_per_clean"] is not None
                    else "n/a (no clean images)")
        print(f"epoch {epoch}: val mAP@0.5 {metrics['map50']:.3f} · "
              f"recall {metrics['recall']:.3f} · FP/clean {fp_clean}")
        if metrics["map50"] > best_map:
            best_map = metrics["map50"]
            torch.save({"model": model.state_dict(), "classes": CLASSES, "size": args.size,
                        "metrics": metrics, "model_card": describe()}, checkpoint)
            print(f"saved best checkpoint -> {checkpoint}")

    report = {"model_card": describe(), "args": vars(args), "epochs": history, "best_map50": best_map}
    metrics_path = Path(args.metrics) if getattr(args, "metrics", None) else MODELS / "train_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def evaluate_split(model, loader, device, score_threshold: float,
                   sources: list[str] | None = None) -> dict:
    """Detection metrics on one split; see ml.evaluate for the matching rules."""
    from .evaluate import accumulate

    model.eval()
    pairs = []
    import torch
    with torch.inference_mode():
        for images, targets in loader:
            outputs = model([image.to(device) for image in images])
            pairs.append((outputs, targets))
    return accumulate(pairs, score_threshold=score_threshold, sources=sources)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Lotline detector.")
    parser.add_argument("--data", default="data/dataset/det_v1")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--size", type=int, default=IMG_SIZE)
    parser.add_argument("--lr", type=float, default=0.004)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", default="cuda" if _cuda() else "cpu")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--no-pretrained", action="store_true")
    parser.add_argument("--score-threshold", type=float, default=0.35)
    parser.add_argument("--log-every", type=int, default=20)
    parser.add_argument("--out", default=str(MODELS / "det_v1.pt"),
                        help="checkpoint path (default keeps det_v1.pt)")
    parser.add_argument("--metrics", default=str(MODELS / "train_metrics.json"),
                        help="training history path")
    parser.add_argument("--init", default=None,
                        help="optional checkpoint to fine-tune from")
    args = parser.parse_args()
    report = train(args)
    print(json.dumps({"best_map50": report["best_map50"]}, indent=2))


def _cuda() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


if __name__ == "__main__":
    main()
