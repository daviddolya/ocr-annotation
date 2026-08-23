#!/usr/bin/env python3
"""Отбор кадров под разметку текста и загрузка картинок (P4e, шаг 0).

Кадр берётся, если выполняются три условия, и у каждого есть причина:

  1. ПЯТЬ–ДЕВЯТЬ ОБЪЕКТОВ. В наборе есть кадры с одним словом и кадры
     с полусотней. Первые не проверяют сопоставление, вторые — это час
     работы на кадр, причём эталон в такой каше сам размечает через раз.
  2. ЕСТЬ КРИВОЛИНЕЙНЫЙ ТЕКСТ. Ради него Total-Text и выбран: на прямых
     вывесках полигон почти не отличается от прямоугольника, и половина
     содержания этапа исчезает.
  3. НЕЧИТАЕМЫХ НЕ БОЛЬШЕ ПОЛОВИНЫ. Кадр, где эталон почти всё пометил
     как «#», не даёт ни транскрипций, ни осмысленного согласия.

Что в кадрах написано и сколько там объектов — НЕ печатается: разметка
идёт вслепую. Распределение показывает --stats, и запускать его следует
после разметки.

    python3 select_text.py --gt data/totaltext/gt --out data/subset --count 10
"""

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import by_image, load_totaltext  # noqa: E402

REPO = "yunusserhat/Total-Text-Dataset"
IMAGES = f"https://huggingface.co/datasets/{REPO}/resolve/main/Images/Test/"


def fetch(url: str, dest: Path, attempts: int = 4) -> int:
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                dest.write_bytes(r.read())
            return dest.stat().st_size
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if dest.exists():
                dest.unlink()
            if attempt == attempts:
                raise
            print(f"  {dest.name}: попытка {attempt} сорвалась ({e})")
            time.sleep(2 * attempt)
    raise RuntimeError("недостижимо")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--min-objects", type=int, default=5)
    ap.add_argument("--max-objects", type=int, default=9)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--stats", action="store_true",
                    help="эталонное распределение — смотреть ПОСЛЕ разметки")
    args = ap.parse_args()

    objs = load_totaltext(args.gt)
    if not objs:
        raise SystemExit(f"в {args.gt} не нашлось poly_gt_*.txt")
    grouped = by_image(objs)

    def suitable(items) -> bool:
        n = len(items)
        if not args.min_objects <= n <= args.max_objects:
            return False
        if sum(1 for o in items if not o.legible) > n // 2:
            return False
        return any(o.ornt == "c" for o in items)

    pool = sorted(k for k, v in grouped.items() if suitable(v))
    if len(pool) < args.count:
        raise SystemExit(f"кандидатов всего {len(pool)}, просили {args.count}")

    rnd = random.Random(args.seed)
    shuffled = list(pool)
    rnd.shuffle(shuffled)
    picked = sorted(shuffled[:args.count])

    frames = args.out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    total = 0
    for name in picked:
        dest = frames / name
        total += dest.stat().st_size if dest.exists() else fetch(IMAGES + name, dest)

    manifest = {
        "source": f"Total-Text, тестовая часть, зеркало {REPO}",
        "task": "полигон по границе слова плюс транскрипция в атрибуте",
        "filters": {"objects_per_frame": [args.min_objects, args.max_objects],
                    "needs_curved": True, "illegible_at_most": "половина"},
        "seed": args.seed,
        "count": len(picked),
        "files": picked,
    }
    (args.out / "selection_text.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"кандидатов {len(pool)}, отобрано кадров {len(picked)}, {total / 1e6:.2f} МБ")
    print(f"кадры: {frames}")
    print(f"манифест: {args.out / 'selection_text.json'}")

    if args.stats:
        items = [o for k in picked for o in grouped[k]]
        legible = [o for o in items if o.legible]
        orn = Counter(o.ornt for o in items)
        print()
        print(f"[stats] объектов {len(items)}, читаемых {len(legible)}, "
              f"по {len(items) / len(picked):.1f} на кадр")
        print(f"[stats] вершин {sum(o.vertices for o in items)}, "
              f"символов {sum(len(o.text) for o in legible)}")
        print(f"[stats] ориентации: криволинейных {orn['c']}, горизонтальных "
              f"{orn['h']}, наклонных {orn['m']}, нечитаемых {orn['#']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
