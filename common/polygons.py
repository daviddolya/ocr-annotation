#!/usr/bin/env python3
"""Растеризация полигонов и метрики масок.

ПРОИСХОЖДЕНИЕ: перенесено из polygon-annotation-agreement/common/polygons.py
(этап A2, P4b) — код написан там и здесь не переписывался. Импортировать
через границу репозиториев нельзя, копия с указанием источника честнее
молчаливого переписывания (правило зонтика P4_annotation_portfolio).

Что взято: Poly, rasterize, mask_iou, dice, boundary_band, boundary_iou,
boundary_distance, match_polys — всё, что не зависит от формата данных.
Что НЕ взято: load_coco_polygons и список классов COCO. Здесь другой
формат и другой предмет: объект — не «человек» или «машина», а слово,
и читается он из Total-Text или из экспорта ICDAR (см. icdar.py).

Растеризация делается через PIL, эрозия — MinFilter, так что scipy не нужен.
"""

import numpy as np
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class Poly:
    """Один объект: подпись и один или несколько контуров.

    Контур — плоский список [x1, y1, x2, y2, ...] в абсолютных пикселях.
    Поле cls в A2 держало класс объекта; здесь в него кладётся транскрипция,
    чтобы сопоставление и разбор работали тем же кодом.
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
    """Контуры -> булева маска. Несколько частей объединяются в одну маску."""
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
    """Dice = 2·IoU/(1+IoU). Считается напрямую, чтобы не тащить деление дважды."""
    inter = np.count_nonzero(a & b)
    total = np.count_nonzero(a) + np.count_nonzero(b)
    return 2 * inter / total if total else 0.0


def boundary_band(mask: np.ndarray, distance: int) -> np.ndarray:
    """Полоса шириной distance внутри границы маски: mask минус эрозия.

    Эрозия — MinFilter квадратом (2·distance+1). Для оценки границы этого
    достаточно; круглый элемент дал бы отличие в единицы пикселей.
    """
    if distance < 1:
        return mask
    size = 2 * distance + 1
    img = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
    eroded = np.array(img.filter(ImageFilter.MinFilter(size)), dtype=np.uint8) > 0
    return mask & ~eroded


def boundary_iou(a: np.ndarray, b: np.ndarray, distance: int) -> float:
    """Boundary IoU (arXiv:2103.16562): IoU, посчитанный только в полосе границы.

    В отличие от mask IoU одинаково строг к крупным и мелким объектам:
    сдвиг контура на несколько пикселей роняет его и там, и там.
    """
    return mask_iou(boundary_band(a, distance), boundary_band(b, distance))


def boundary_distance(width: int, height: int, ratio: float = 0.02) -> int:
    """Ширина полосы границы — доля диагонали кадра, как в статье."""
    return max(1, round(ratio * (width ** 2 + height ** 2) ** 0.5))



def match_polys(mine: list[Poly], ref: list[Poly], masks_mine: list[np.ndarray],
                masks_ref: list[np.ndarray], iou_threshold: float):
    """Жадное сопоставление по убыванию mask IoU, БЕЗ учёта класса.

    Тот же принцип, что в agreement.py для боксов: если требовать совпадения
    метки, ошибка класса распадётся на пропуск и лишний объект сразу,
    и согласие по классам считать будет не на чем.
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
