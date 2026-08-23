#!/usr/bin/env python3
"""Отрисовка split pairs: обе стороны разметили то же слово, пара не сложилась.

Такие объекты не попадают ни в `pairs`, ни в картинки шага 6.1 — они лежат
в обоих списках «без пары», и по таблице их не отличить от настоящего
пропуска. Скрипт находит их по совпадению транскрипции внутри кадра,
считает IoU и рисует тем же `render_pair`, что и худшие пары.

    .venv/bin/python tools/render_split.py --metrics reports/ocr_metrics.json \
        --gt data/totaltext/gt --mine annotation/my_labels \
        --images data/subset/frames --out reports/review/split
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from icdar import by_image, load_cvat_icdar, load_totaltext  # noqa: E402
from polygons import Poly, mask_iou, rasterize  # noqa: E402
from render_text import load_font, render_pair  # noqa: E402


def poly_iou(a, b, width: int, height: int) -> float:
    def mask(obj):
        flat = [c for p in obj.ring for c in p]
        return rasterize(Poly(cls="", parts=[flat]), width, height)
    return mask_iou(mask(a), mask(b))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--metrics", type=Path, required=True)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--mine", type=Path, required=True)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    gt = by_image(load_totaltext(args.gt))
    mine = by_image(load_cvat_icdar(args.mine))
    args.out.mkdir(parents=True, exist_ok=True)
    font, cyrillic = load_font(15)

    free_gt = {(u["image"], u["id"]) for u in metrics["unmatched_gt_list"]}
    free_my = {(u["image"], u["id"]) for u in metrics["unmatched_mine_list"]}

    found = []
    for image, refs in gt.items():
        mine_objs = mine.get(image, [])
        taken = set()
        for i, r in enumerate(refs, 1):
            if (image, i) not in free_gt or (r.text or "") == "#":
                continue
            for j, m in enumerate(mine_objs, 1):
                if (image, j) not in free_my or j in taken:
                    continue
                if (m.text or "").upper() != (r.text or "").upper():
                    continue
                taken.add(j)
                found.append((image, i, j, r, m))
                break

    print(f"split pairs найдено: {len(found)}")
    for n, (image, i, j, r, m) in enumerate(sorted(found), 1):
        path = args.images / image
        from PIL import Image
        with Image.open(path) as im:
            iou = poly_iou(r, m, im.width, im.height)
        out = args.out / f"{n:02d}_{Path(image).stem}_{r.text}.jpg"
        render_pair(path, r, m, iou, None, out, font, cyrillic)
        print(f"  {image} «{r.text}»: IoU {iou:.3f}, вершин {r.vertices}/{m.vertices}")
    print(f"каталог: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
