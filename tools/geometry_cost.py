#!/usr/bin/env python3
"""The price of geometry: what a lazy contour costs.

Two measurements on the ground truth, both about the same thing -- the cost of
deciding to "outline it roughly", taken at exactly the same level of care.

  1. A BOX INSTEAD OF A POLYGON. Every reference contour is replaced by its
     bounding box and IoU is computed. The breakdown by text orientation shows
     where a polygon is needed at all.
  2. THE VERTEX BUDGET. Only n vertices are kept from the reference contour,
     spaced evenly around the ring -- that is what an annotator who clicked
     fewer points looks like.

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

ORNT_NAMES = {"h": "horizontal", "m": "slanted",
              "c": "curved", "#": "illegible", "v": "vertical"}
BUDGETS = (4, 6, 8, 10)
MAX_SIDE = 1400  # local box: anything larger is wasted and costs memory


def ring_iou(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    """IoU of two contours inside a shared local box -- no image needed."""
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
    """Keep n vertices, spaced evenly around the ring."""
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
    print(f"objects with four or more vertices: {len(objs)}")

    groups = defaultdict(list)
    for o in objs:
        groups[o.ornt].append(ring_iou(o.ring, o.bbox_ring()))
    print()
    print("A BOX INSTEAD OF A POLYGON")
    print("| text orientation | objects | mean IoU | median |")
    print("|---|---|---|---|")
    for key in ("h", "m", "c", "#"):
        v = groups.get(key, [])
        if v:
            print(f"| {ORNT_NAMES[key]} | {len(v)} | {statistics.mean(v):.3f} | "
                  f"{statistics.median(v):.3f} |")
    allv = [x for v in groups.values() for x in v]
    print(f"| everything | {len(allv)} | {statistics.mean(allv):.3f} | "
          f"{statistics.median(allv):.3f} |")

    many = [o for o in objs if o.vertices >= args.min_vertices_for_budget]
    print()
    print("THE VERTEX BUDGET: keeping n points of the reference contour")
    print(f"(computed over {len(many)} objects whose reference contour has "
          f"{args.min_vertices_for_budget}+ vertices)")
    if len(many) < 30:
        print(f"WARNING: only {len(many)} objects -- on a sample that small the table")
        print("below means nothing. Curvature and vertex counts are a property of the")
        print("DATASET, not of my subset: run this command without --images.")
    if not many:
        print("no such objects in this set -- table skipped")
        return 0
    print("| vertices kept | mean IoU | median | share of objects with IoU < 0.8 |")
    print("|---|---|---|---|")
    for n in BUDGETS:
        v = [ring_iou(o.ring, subsample(o.ring, n)) for o in many]
        low = sum(1 for x in v if x < 0.8) / len(v)
        print(f"| {n} | {statistics.mean(v):.3f} | {statistics.median(v):.3f} | "
              f"{low:.0%} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
