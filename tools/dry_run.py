#!/usr/bin/env python3
"""Репетиция конвейера до разметки: подставная «своя» разметка (P4e, шаг 5).

Час разметки, а потом выясняется, что расчёт падает или отрисовка рисует
не то, — плохой порядок. Скрипт берёт эталон и портит его известным
образом, изображая правдоподобного разметчика:

  * дрожь руки — вершины сдвинуты на несколько пикселей;
  * часть криволинейных объектов обведена четырьмя точками, а не контуром;
  * часть транскрипций записана нижним регистром;
  * два читаемых объекта помечены нечитаемыми и один наоборот;
  * один объект пропущен, один лишний размечен.

Числа, которые получатся, к твоей работе отношения не имеют. Смысл один:
убедиться, что конвейер работает и картинки открываются.

    .venv/bin/python tools/dry_run.py --gt data/totaltext/gt \
        --selection data/subset/selection_text.json --out reports/dry_run
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import TextObject, load_totaltext, save_icdar  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/dry_run"))
    ap.add_argument("--jitter", type=float, default=3.0, help="px")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    images = set(json.loads(args.selection.read_text(encoding="utf-8"))["files"])
    gt = load_totaltext(args.gt, images=images)
    rnd = random.Random(args.seed)

    mine: list[TextObject] = []
    flipped = 0
    for n, o in enumerate(gt):
        if n == 4:                                   # один объект пропущен
            continue
        ring = o.ring
        if o.ornt == "c" and rnd.random() < 0.4:     # обвёл рамкой вместо контура
            ring = o.bbox_ring()
        ring = [(x + rnd.gauss(0, args.jitter), y + rnd.gauss(0, args.jitter))
                for x, y in ring]
        text = o.text
        if o.legible and rnd.random() < 0.35:        # записал нижним регистром
            text = text.lower()
        if o.legible and flipped < 2 and rnd.random() < 0.1:
            text = "#"                               # счёл нечитаемым
            flipped += 1
        elif not o.legible and rnd.random() < 0.15:
            text = "TEXT"                            # наоборот, вычитал
        mine.append(TextObject(image=o.image, ring=ring, text=text,
                               ident=1000 + n))

    extra = gt[0]                                    # один лишний
    mine.append(TextObject(image=extra.image, ident=9001, text="EXTRA",
                           ring=[(x + 400, y + 200) for x, y in extra.ring]))

    args.out.mkdir(parents=True, exist_ok=True)
    frames = save_icdar(mine, args.out)
    print("ЭТО ПОДСТАВНАЯ РАЗМЕТКА, А НЕ ТВОЯ. Числа по ней ничего не значат.")
    print(f"эталонных объектов {len(gt)}, подставных {len(mine)}, кадров {frames}")
    print(f"{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
