#!/usr/bin/env python3
"""Отрисовка расхождений по тексту (P4e, оснастка к шагу 6).

«IoU 0.50, CER 1.00» не говорит ничего, пока не видно, что именно
разошлось: контур обведён рамкой, слово разбито надвое или прочитано
верно, но записано иначе. Три вещи, каждая отвечает на свой вопрос.

    пары        вырезка вокруг слова с обоими контурами. Синий — эталон,
                оранжевый — твой. Подпись: обе транскрипции, IoU и CER
    ориентации  столбики среднего IoU по ориентации эталонного текста
    оси         точечная диаграмма: IoU по горизонтали, CER по вертикали,
                точка на пару. Сразу видно, что даёт расхождения —
                геометрия, текст или обе оси сразу

    .venv/bin/python tools/render_text.py --metrics reports/ocr_metrics.json \
        --images data/subset/frames --gt data/totaltext/gt --mine annotation/my_labels \
        --out reports/review
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import by_image, load_cvat_icdar, load_totaltext  # noqa: E402

REF_COLOR = (60, 130, 246)
MY_COLOR = (249, 115, 22)
BAD = (220, 38, 38)
OK = (34, 160, 90)

FONT_CANDIDATES = [
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def load_font(size: int) -> tuple[object, bool]:
    """Возвращает (шрифт, поддерживает ли кириллицу)."""
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size), True
            except OSError:
                continue
    return ImageFont.load_default(), False


def render_pair(image_path: Path, ref, mine, iou, cer, out: Path, font,
                cyrillic: bool, target: int = 560) -> None:
    img = Image.open(image_path).convert("RGB")
    xs = [p[0] for p in ref.ring + mine.ring]
    ys = [p[1] for p in ref.ring + mine.ring]
    pad = 0.25 * max(max(xs) - min(xs), max(ys) - min(ys), 30)
    x0 = max(0, min(xs) - pad)
    y0 = max(0, min(ys) - pad)
    x1 = min(img.width, max(xs) + pad)
    y1 = min(img.height, max(ys) + pad)
    crop = img.crop((int(x0), int(y0), int(x1), int(y1)))
    scale = target / max(crop.width, crop.height, 1)
    crop = crop.resize((max(1, int(crop.width * scale)),
                        max(1, int(crop.height * scale))))

    head = 46
    canvas = Image.new("RGB", (crop.width, crop.height + head), (255, 255, 255))
    canvas.paste(crop, (0, head))
    d = ImageDraw.Draw(canvas)
    for obj, color in ((ref, REF_COLOR), (mine, MY_COLOR)):
        pts = [((x - x0) * scale, (y - y0) * scale + head) for x, y in obj.ring]
        if len(pts) >= 3:
            d.polygon(pts, outline=color)
            d.line(pts + [pts[0]], fill=color, width=3)
        for px, py in pts:
            d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color)
    cer_text = "—" if cer is None else f"{cer:.2f}"
    line1 = f"IoU {iou:.3f}   CER {cer_text}   вершин {ref.vertices}/{mine.vertices}" \
        if cyrillic else f"IoU {iou:.3f}  CER {cer_text}"
    d.text((6, 5), line1, fill=(20, 20, 20), font=font)
    d.text((6, 25), f"«{ref.text}»", fill=REF_COLOR, font=font)
    w = d.textlength(f"«{ref.text}»", font=font)
    d.text((16 + w, 25), f"«{mine.text}»", fill=MY_COLOR, font=font)
    canvas.save(out, quality=92)


def render_orientation(metrics: dict, out: Path, font, cyrillic: bool) -> None:
    rows = [(k, v["pairs"], v["iou"])
            for k, v in metrics["iou_by_orientation"].items() if v["pairs"]]
    rows.sort(key=lambda r: r[2])
    w, row_h, left = 620, 30, 190
    img = Image.new("RGB", (w, row_h * len(rows) + 46), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "средний mask IoU по ориентации текста" if cyrillic
           else "mean mask IoU by text orientation", fill=(20, 20, 20), font=font)
    bar_w = w - left - 96
    for k, (name, pairs, iou) in enumerate(rows):
        y = 42 + k * row_h
        d.text((10, y + 5), name if cyrillic else name[:12], fill=(40, 40, 40), font=font)
        d.rectangle([left, y + 5, left + bar_w, y + 21], fill=(235, 235, 235))
        d.rectangle([left, y + 5, left + bar_w * iou, y + 21],
                    fill=OK if iou >= 0.75 else BAD)
        d.text((left + bar_w + 8, y + 5), f"{iou:.3f}  n={pairs}",
               fill=(60, 60, 60), font=font)
    img.save(out)


def render_axes(metrics: dict, out: Path, font, cyrillic: bool) -> None:
    """Точечная диаграмма: геометрия против текста."""
    pts = [(p["iou"], p["cer"]) for p in metrics["pairs"] if p["cer"] is not None]
    size, pad, top = 460, 62, 52
    img = Image.new("RGB", (size + pad + 24, size + top + 44), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 8), "геометрия против текста" if cyrillic
           else "geometry vs text", fill=(20, 20, 20), font=font)
    d.text((6, 28), "CER", fill=(60, 60, 60), font=font)
    d.rectangle([pad, top, pad + size, top + size], outline=(200, 200, 200))
    cer_max = max([c for _, c in pts] + [1.0])
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = pad + size * frac
        d.line([x, top, x, top + size], fill=(240, 240, 240))
        d.text((x - 10, top + size + 6), f"{frac:.2f}", fill=(90, 90, 90), font=font)
        y = top + size - size * frac
        d.line([pad, y, pad + size, y], fill=(240, 240, 240))
        d.text((6, y - 8), f"{frac * cer_max:.2f}", fill=(90, 90, 90), font=font)
    d.text((pad + size // 2 - 20, top + size + 24), "IoU", fill=(60, 60, 60), font=font)
    for iou, cer in pts:
        x = pad + size * max(0.0, min(1.0, iou))
        y = top + size - size * (cer / cer_max if cer_max else 0)
        good = iou >= 0.75 and cer <= 0.1
        d.ellipse([x - 4, y - 4, x + 4, y + 4],
                  fill=OK if good else BAD, outline=(255, 255, 255))
    img.save(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--metrics", type=Path, default=Path("reports/ocr_metrics.json"))
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--mine", type=Path, required=True)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--worst", type=int, default=4,
                    help="сколько худших взять по каждой оси")
    args = ap.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    gt = {(o.image, o.ident): o for o in load_totaltext(args.gt)}
    mine = {(o.image, o.ident): o for o in load_cvat_icdar(args.mine)}

    args.out.mkdir(parents=True, exist_ok=True)
    font, cyrillic = load_font(16)
    if not cyrillic:
        print("TrueType-шрифт не найден: подписи будут латиницей")

    chosen, seen = [], set()
    for source, key in (("geometry", "worst_geometry"), ("text", "worst_text")):
        for item in metrics[key][:args.worst]:
            ident = (item["image"], item["gt_id"])
            if ident in seen:
                continue
            seen.add(ident)
            chosen.append((source, item))

    made = []
    for k, (source, item) in enumerate(chosen, 1):
        ref = gt.get((item["image"], item["gt_id"]))
        pair = next((p for p in metrics["pairs"]
                     if p["image"] == item["image"] and p["gt_id"] == item["gt_id"]), None)
        if ref is None or pair is None:
            continue
        my = mine.get((item["image"], pair["my_id"]))
        if my is None:
            continue
        name = f"{k:02d}_{source}_{Path(item['image']).stem}_{item['gt_id']}.jpg"
        render_pair(args.images / item["image"], ref, my, pair["iou"], pair["cer"],
                    args.out / name, font, cyrillic)
        made.append({"file": name, "source": source, "image": item["image"],
                     "gt_id": item["gt_id"], "iou": pair["iou"], "cer": pair["cer"],
                     "gt_text": ref.text, "my_text": my.text})

    render_orientation(metrics, args.out / "iou_by_orientation.png", font, cyrillic)
    render_axes(metrics, args.out / "geometry_vs_text.png", font, cyrillic)
    (args.out / "pairs_manifest.json").write_text(
        json.dumps(made, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"пар отрисовано {len(made)}, плюс iou_by_orientation.png "
          "и geometry_vs_text.png")
    print(f"каталог: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
