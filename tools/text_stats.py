#!/usr/bin/env python3
"""Конвенция эталона: как Total-Text записывает текст (P4e, шаг 2).

Без --images считает по всей тестовой части — так меряется конвенция
датасета вообще, и это то, что нужно знать до разметки. С --images
ограничивается своим подмножеством: смотреть после разметки.

    python3 tools/text_stats.py --gt data/totaltext/gt
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import by_image, load_totaltext  # noqa: E402

ORNT_NAMES = {"c": "криволинейный", "h": "горизонтальный",
              "m": "наклонный", "#": "нечитаемый", "v": "вертикальный"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--images", type=Path, default=None,
                    help="selection_text.json — ограничить своим набором")
    args = ap.parse_args()

    images = None
    if args.images:
        images = set(json.loads(args.images.read_text(encoding="utf-8"))["files"])
    objs = load_totaltext(args.gt, images=images)
    if not objs:
        raise SystemExit("не нашлось ни одного объекта")
    legible = [o for o in objs if o.legible]

    print(f"кадров {len(by_image(objs))}, объектов {len(objs)}")
    print(f"нечитаемых (транскрипция «#»): {len(objs) - len(legible)} "
          f"({(len(objs) - len(legible)) / len(objs):.0%})")

    orn = Counter(o.ornt for o in objs)
    print()
    print("| ориентация текста | объектов | доля |")
    print("|---|---|---|")
    for key, count in orn.most_common():
        print(f"| {ORNT_NAMES.get(key, key or '—')} | {count} | {count / len(objs):.0%} |")

    verts = Counter(o.vertices for o in objs)
    print()
    print("| вершин у полигона | объектов |")
    print("|---|---|")
    for n, count in sorted(verts.items()):
        if count >= 10 or n <= 6:
            print(f"| {n} | {count} |")
    print(f"вершин всего {sum(o.vertices for o in objs)}, "
          f"медиана {statistics.median([o.vertices for o in objs]):.0f}")

    texts = [o.text for o in legible]
    with_letters = [s for s in texts if any(c.isalpha() for c in s)]
    upper = sum(1 for s in with_letters if s.isupper())
    lower = sum(1 for s in with_letters if s.islower())
    mixed = len(with_letters) - upper - lower
    chars = sum(len(s) for s in texts)
    upper_chars = sum(1 for s in texts for c in s if c.isupper())
    punct = Counter(c for s in texts for c in s if not c.isalnum())
    with_punct = sum(1 for s in texts if any(not c.isalnum() for c in s))
    digits_only = sum(1 for s in texts if s.isdigit())

    print()
    print(f"читаемых транскрипций {len(texts)}, символов {chars}, "
          f"медианная длина {statistics.median([len(s) for s in texts]):.0f}")
    print()
    print("| признак записи | объектов | доля от читаемых |")
    print("|---|---|---|")
    print(f"| ВЕРХНИЙ регистр целиком | {upper} | {upper / len(texts):.0%} |")
    print(f"| нижний регистр целиком | {lower} | {lower / len(texts):.0%} |")
    print(f"| смешанный регистр | {mixed} | {mixed / len(texts):.0%} |")
    print(f"| только цифры | {digits_only} | {digits_only / len(texts):.0%} |")
    print(f"| есть знак, не буква и не цифра | {with_punct} | {with_punct / len(texts):.0%} |")
    print()
    print(f"заглавных букв {upper_chars} из {chars} символов "
          f"({upper_chars / chars:.0%})")
    if punct:
        print("какие знаки вообще встречаются: "
              + ", ".join(f"«{c}» {n}" for c, n in punct.most_common(8)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
