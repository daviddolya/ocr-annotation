#!/usr/bin/env python3
"""Цена геометрии: сколько стоит поленившийся контур (P4e, шаг 3).

Два замера на эталоне, оба про одно — во что обходится решение «обвести
попроще», принятое при совершенно одинаковой аккуратности.

  1. ПРЯМОУГОЛЬНИК ВМЕСТО ПОЛИГОНА. Каждый эталонный контур заменяется
     описанным вокруг него прямоугольником, считается IoU. Разбивка по
     ориентации текста показывает, где полигон вообще нужен.
  2. БЮДЖЕТ ВЕРШИН. Из эталонного контура остаётся n вершин, равномерно
     по кольцу — так выглядит разметчик, кликнувший меньше точек.

    python3 tools/geometry_cost.py --gt data/totaltext/gt \
        --images data/subset/selection_text.json
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import load_totaltext  # noqa: E402
from polygons import Poly, mask_iou, rasterize  # noqa: E402

ORNT_NAMES = {"h": "горизонтальный", "m": "наклонный",
              "c": "криволинейный", "#": "нечитаемый", "v": "вертикальный"}
BUDGETS = (4, 6, 8, 10)
MAX_SIDE = 1400  # локальная рамка: больше не нужно, а память экономит


def ring_iou(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    """IoU двух контуров в общей локальной рамке — картинка не нужна."""
    xs = [p[0] for p in a + b]
    ys = [p[1] for p in a + b]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    scale = min(1.0, MAX_SIDE / max(w, h, 1))
    width = max(2, int(w * scale) + 2)
    height = max(2, int(h * scale) + 2)

    def mask(ring):
        flat = [c for p in ring for c in ((p[0] - x0) * scale, (p[1] - y0) * scale)]
        return rasterize(Poly(cls="", parts=[flat]), width, height)

    return mask_iou(mask(a), mask(b))


def subsample(ring: list, n: int) -> list:
    """Оставить n вершин, равномерно по кольцу."""
    if n >= len(ring):
        return list(ring)
    step = len(ring) / n
    return [ring[int(round(i * step)) % len(ring)] for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--images", type=Path, default=None)
    ap.add_argument("--min-vertices-for-budget", type=int, default=8)
    args = ap.parse_args()

    images = None
    if args.images:
        images = set(json.loads(args.images.read_text(encoding="utf-8"))["files"])
    objs = [o for o in load_totaltext(args.gt, images=images) if o.vertices >= 4]
    print(f"объектов с четырьмя и более вершинами: {len(objs)}")

    groups = defaultdict(list)
    for o in objs:
        groups[o.ornt].append(ring_iou(o.ring, o.bbox_ring()))
    print()
    print("ПРЯМОУГОЛЬНИК ВМЕСТО ПОЛИГОНА")
    print("| ориентация текста | объектов | средний IoU | медиана |")
    print("|---|---|---|---|")
    for key in ("h", "m", "c", "#"):
        v = groups.get(key, [])
        if v:
            print(f"| {ORNT_NAMES[key]} | {len(v)} | {statistics.mean(v):.3f} | "
                  f"{statistics.median(v):.3f} |")
    allv = [x for v in groups.values() for x in v]
    print(f"| всё вместе | {len(allv)} | {statistics.mean(allv):.3f} | "
          f"{statistics.median(allv):.3f} |")

    many = [o for o in objs if o.vertices >= args.min_vertices_for_budget]
    print()
    print("БЮДЖЕТ ВЕРШИН: оставляем n точек из эталонного контура")
    print(f"(считается на {len(many)} объектах, у которых в эталоне "
          f"{args.min_vertices_for_budget}+ вершин)")
    if len(many) < 30:
        print(f"ВНИМАНИЕ: объектов всего {len(many)} — на такой выборке таблица ниже")
        print("ничего не значит. Кривизна и число вершин — свойство ДАТАСЕТА,")
        print("а не твоего набора: запусти эту команду без --images.")
    if not many:
        print("таких объектов в наборе нет — таблица пропущена")
        return 0
    print("| вершин оставлено | средний IoU | медиана | доля объектов IoU < 0.8 |")
    print("|---|---|---|---|")
    for n in BUDGETS:
        v = [ring_iou(o.ring, subsample(o.ring, n)) for o in many]
        low = sum(1 for x in v if x < 0.8) / len(v)
        print(f"| {n} | {statistics.mean(v):.3f} | {statistics.median(v):.3f} | "
              f"{low:.0%} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
