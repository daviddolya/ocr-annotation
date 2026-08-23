#!/usr/bin/env python3
"""Polygon rasterisation and mask metrics.

PROVENANCE: ported from polygon-annotation-agreement/common/polygons.py
(stage A2) -- the code was written there and has not been rewritten here.
Importing across repository boundaries is not an option, and a copy that
names its source is more honest than a silent rewrite.

What was taken: Poly, rasterize, mask_iou, dice, boundary_band, boundary_iou,
boundary_distance, match_polys -- everything that does not depend on the data
format. What was NOT taken: load_coco_polygons and the COCO class list. The
format and the subject differ here: an object is not a "person" or a "car" but
a word, and it is read from Total-Text or from an ICDAR export (see icdar.py).

Rasterisation goes through PIL and erosion through MinFilter, so scipy is not
needed.
"""

import numpy as np
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class Poly:
    """One object: a label and one or more contours.

    A contour is a flat list [x1, y1, x2, y2, ...] in absolute pixels. In A2
    the cls field held the object class; here it holds the transcription, so
    that matching and analysis run on the same code.
    """
    cls: str
    parts: list[list[float]]
    iscrowd: bool = False

    @property
    def vertices(self) -> int:
        return sum(len(p) // 2 for p in self.parts)

    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p[i] for p in self.parts for i in range(0, len(p), 2)]
        ys = [p[i] for p in self.parts for i in range(1, len(p), 2)]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)




def rasterize(poly: Poly, width: int, height: int) -> np.ndarray:
    """Contours -> boolean mask. Several parts merge into a single mask."""
    canvas = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(canvas)
    for part in poly.parts:
        points = [(part[i], part[i + 1]) for i in range(0, len(part) - 1, 2)]
        if len(points) >= 3:
            draw.polygon(points, fill=1)
    return np.array(canvas, dtype=bool)


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.count_nonzero(a & b)
    if inter == 0:
        return 0.0
    union = np.count_nonzero(a | b)
    return inter / union if union else 0.0


def dice(a: np.ndarray, b: np.ndarray) -> float:
    """Dice = 2*IoU/(1+IoU), computed directly to avoid dividing twice."""
    inter = np.count_nonzero(a & b)
    total = np.count_nonzero(a) + np.count_nonzero(b)
    return 2 * inter / total if total else 0.0


def boundary_band(mask: np.ndarray, distance: int) -> np.ndarray:
    """A band of the given width inside the mask boundary: mask minus erosion.

    Erosion is a MinFilter over a square of (2*distance+1). That is accurate
    enough for a boundary estimate; a circular element would differ by a few
    pixels.
    """
    if distance < 1:
        return mask
    size = 2 * distance + 1
    img = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
    eroded = np.array(img.filter(ImageFilter.MinFilter(size)), dtype=np.uint8) > 0
    return mask & ~eroded


def boundary_iou(a: np.ndarray, b: np.ndarray, distance: int) -> float:
    """Boundary IoU (arXiv:2103.16562): IoU computed inside the boundary band.

    Unlike mask IoU it is equally strict on large and small objects: a contour
    shifted by a few pixels drags it down in both cases.
    """
    return mask_iou(boundary_band(a, distance), boundary_band(b, distance))


def boundary_distance(width: int, height: int, ratio: float = 0.02) -> int:
    """Boundary band width as a fraction of the frame diagonal, as in the paper."""
    return max(1, round(ratio * (width ** 2 + height ** 2) ** 0.5))



def match_polys(mine: list[Poly], ref: list[Poly], masks_mine: list[np.ndarray],
                masks_ref: list[np.ndarray], iou_threshold: float):
    """Greedy matching by descending mask IoU, IGNORING the label.

    Same principle as agreement.py for boxes: if a label match were required,
    a class error would immediately split into a miss plus a spurious object,
    and there would be nothing left to measure class agreement on.
    """
    candidates = sorted(
        ((mask_iou(masks_mine[i], masks_ref[j]), i, j)
         for i in range(len(mine)) for j in range(len(ref))),
        key=lambda t: -t[0])
    used_mine: set[int] = set()
    used_ref: set[int] = set()
    pairs = []
    for score, i, j in candidates:
        if score < iou_threshold:
            break
        if i in used_mine or j in used_ref:
            continue
        used_mine.add(i)
        used_ref.add(j)
        pairs.append((i, j, score))
    extra = [i for i in range(len(mine)) if i not in used_mine]
    missing = [j for j in range(len(ref)) if j not in used_ref]
    return pairs, extra, missing
