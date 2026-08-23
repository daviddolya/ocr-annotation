#!/usr/bin/env python3
"""Проверка экспорта числом до того, как считать метрики (P4e, шаг 4).

Четыре вещи ломаются молча и дают не ошибку, а неправильное число:

  1. ТРАНСКРИПЦИИ НЕ УЕХАЛИ. Атрибут назван не `text`, либо выбран формат,
     который текст не переносит. В файле останутся координаты без кавычек.
     Симптом на выходе: CER равен единице у всех объектов.
  2. ПОЛИГОНЫ ОКАЗАЛИСЬ ПРЯМОУГОЛЬНИКАМИ. Все объекты с четырьмя вершинами
     на криволинейном тексте — это не разметка, а описанные рамки, и IoU
     упрётся в потолок около 0.5 независимо от старания.
  3. НЕ ТОТ СОСТАВ КАДРОВ. Экспорт уехал не с той задачи.
  4. ПУСТЫЕ ТРАНСКРИПЦИИ. Пустая строка и пометка «нечитаемо» — разные
     вещи: первое значит «забыл набрать», второе — принятое решение.

    python3 tools/check_export.py --mine annotation/my_labels \
        --selection data/subset/selection_text.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import ILLEGIBLE, by_image, load_cvat_icdar  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mine", type=Path, required=True,
                    help="каталог с gt_<image>.txt из экспорта")
    ap.add_argument("--selection", type=Path, default=None)
    args = ap.parse_args()

    objs = load_cvat_icdar(args.mine)
    problems = 0

    if not objs:
        print("ОБЪЕКТОВ НОЛЬ. Либо задача не переведена в completed, либо формат")
        print("выбран не тот: нужен именно ICDAR Text Localization 1.0.")
        return 1

    grouped = by_image(objs)
    print(f"кадров {len(grouped)}, объектов {len(objs)}, "
          f"вершин всего {sum(o.vertices for o in objs)}")

    empty = [o for o in objs if o.text == ""]
    illegible = [o for o in objs if o.text in ILLEGIBLE]
    legible = [o for o in objs if o.legible]
    print(f"транскрипции: заполнено {len(legible)}, "
          f"помечено нечитаемым {len(illegible)}, пусто {len(empty)}")
    if not legible:
        problems += 1
        print("НИ ОДНОЙ ТРАНСКРИПЦИИ. Атрибут называется не `text`, либо формат")
        print("экспорта текст не переносит. Считать нечего.")
    elif empty:
        problems += 1
        print(f"{len(empty)} объектов с пустой транскрипцией. Пустая строка — это")
        print("«забыл набрать»; осознанное «не читается» пишется как «#».")

    verts = Counter(o.vertices for o in objs)
    four = verts.get(4, 0)
    print(f"вершин на объект: " + ", ".join(
        f"{n} у {c}" for n, c in sorted(verts.items())))
    if four == len(objs):
        problems += 1
        print("У ВСЕХ ОБЪЕКТОВ РОВНО ЧЕТЫРЕ ВЕРШИНЫ. Похоже, размечены рамки,")
        print("а не контуры: на криволинейном тексте это потолок IoU около 0.5.")
    elif four > 0.8 * len(objs):
        print(f"четырёхвершинных {four} из {len(objs)} — многовато для набора,")
        print("где больше трети текста криволинейный. Стоит посмотреть глазами.")

    up = sum(1 for o in legible if o.text.isupper())
    low = sum(1 for o in legible if o.text.islower())
    print(f"регистр: ВЕРХНИЙ целиком {up}, нижний целиком {low}, "
          f"остальные {len(legible) - up - low}")
    if legible and low == len(legible):
        print("всё в нижнем регистре — это осознанное решение инструкции или нет?")
        print("Если нет, дешевле переписать сейчас: цена правила — CER около 0.7.")

    if args.selection:
        want = set(json.loads(args.selection.read_text(encoding="utf-8"))["files"])
        have = set(grouped)
        missing = sorted(want - have)
        extra = sorted(have - want)
        if missing:
            problems += 1
            print(f"НЕТ РАЗМЕТКИ на {len(missing)} кадрах отбора: "
                  f"{', '.join(missing[:5])}{' …' if len(missing) > 5 else ''}")
        if extra:
            print(f"лишние кадры вне отбора: {len(extra)}")
        if not missing and not extra:
            print(f"состав кадров совпадает с манифестом отбора ({len(want)})")

    print()
    print("проверка пройдена, можно считать" if problems == 0
          else f"проблем: {problems}. Сначала чинить, потом считать.")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
