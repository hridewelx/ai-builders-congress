"""Run the trained detector on image files and print review-ready JSON.

This is the offline check used before any UI wiring: it reads one image, prints
boxes in original pixel coordinates, and can draw them for a visual sanity pass.

    python -m ml.infer --image path/to/photo.jpg
    python -m ml.infer --dir data/samples --out /tmp/detections.json --save-dir /tmp/annotated
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import CLASSES, MODELS, SCORE_THRESHOLD

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load(checkpoint_path: Path):
    import torch

    from .model import build_model

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = build_model(pretrained=False, min_size=checkpoint.get("size", 640),
                        max_size=checkpoint.get("size", 640))
    model.load_state_dict(checkpoint["model"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    return model, device, checkpoint


def predict(model, device, image_path: Path, size: int = 640) -> dict:
    import torch
    from PIL import Image

    with Image.open(image_path) as im:
        original = im.convert("RGB")
        width, height = original.size
        resized = original.resize((size, size), Image.BILINEAR)
    array = torch.ByteTensor(list(resized.tobytes())).view(size, size, 3).permute(2, 0, 1).float() / 255.0
    with torch.inference_mode():
        output = model([array.to(device)])[0]
    scale_x, scale_y = width / size, height / size
    detections = []
    for box, score, label in zip(output["boxes"].tolist(), output["scores"].tolist(),
                                 output["labels"].tolist()):
        if score < SCORE_THRESHOLD:
            continue
        detections.append({
            "type": CLASSES[label - 1] if 1 <= label <= len(CLASSES) else str(label),
            "score": round(score, 4),
            "box": [round(box[0] * scale_x, 1), round(box[1] * scale_y, 1),
                    round(box[2] * scale_x, 1), round(box[3] * scale_y, 1)],
        })
    return {"image": str(image_path), "width": width, "height": height, "detections": detections}


def draw(image_path: Path, detections: list[dict], out_path: Path) -> None:
    from PIL import Image, ImageDraw

    with Image.open(image_path) as im:
        image = im.convert("RGB")
    draw_ctx = ImageDraw.Draw(image)
    for item in detections:
        box = item["box"]
        draw_ctx.rectangle(box, outline=(255, 80, 80), width=3)
        draw_ctx.text((box[0] + 4, max(0, box[1] - 12)),
                      f"{item['type']} {item['score']:.2f}", fill=(255, 80, 80))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the detector on images.")
    parser.add_argument("--checkpoint", type=Path, default=MODELS / "det_v2b.pt")
    parser.add_argument("--image", type=Path, nargs="*", default=[])
    parser.add_argument("--dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--save-dir", type=Path, default=None)
    args = parser.parse_args()

    paths = list(args.image)
    if args.dir:
        paths += sorted(p for p in args.dir.rglob("*") if p.suffix.lower() in IMAGE_EXTS)
    if not paths:
        raise SystemExit("pass --image or --dir")

    model, device, checkpoint = load(args.checkpoint)
    results = [predict(model, device, path, checkpoint.get("size", 640)) for path in paths]
    for item in results:
        print(f"{Path(item['image']).name}: {len(item['detections'])} detections")
        for det in item["detections"]:
            print(f"  {det['type']:<14} {det['score']:.3f} {det['box']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    if args.save_dir:
        for item in results:
            draw(Path(item["image"]), item["detections"], args.save_dir / f"{Path(item['image']).stem}.png")
        print(f"annotated images -> {args.save_dir}")


if __name__ == "__main__":
    main()
