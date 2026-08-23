#!/usr/bin/env python3
"""Цена одной фразы в инструкции — на этот раз в транскрипции (P4e, шаг 2).

Берёт эталон и делает из него несколько «разметок», в которых ТЕКСТ ПРОЧИТАН
ПРАВИЛЬНО ДО СИМВОЛА. Отличается только правило записи: приводить ли регистр,
выбрасывать ли знаки препинания. Всё, что видно в таблице, — цена правила,
а не аккуратности чтения.

    python3 tools/convention_cost.py --gt data/totaltext/gt \
        --images data/subset/selection_text.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import load_totaltext  # noqa: E402
from text import NORMALIZERS, corpus_cer, corpus_wer  # noqa: E402

ORDER = ["as_is", "lower", "upper", "no_punct", "lower_no_punct"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--images", type=Path, default=None)
    args = ap.parse_args()

    images = None
    if args.images:
        images = set(json.loads(args.images.read_text(encoding="utf-8"))["files"])
    objs = [o for o in load_totaltext(args.gt, images=images) if o.legible]
    refs = [o.text for o in objs]
    chars = sum(len(s) for s in refs)
    print(f"читаемых объектов {len(refs)}, символов в эталоне {chars}; "
          "во всех вариантах текст прочитан верно до символа")
    print()
    print("| правило транскрипции | CER | WER | затронуто объектов |")
    print("|---|---|---|---|")
    for key in ORDER:
        name, func = NORMALIZERS[key]
        pairs = [(r, func(r)) for r in refs]
        touched = sum(1 for r, h in pairs if r != h)
        c = corpus_cer(pairs)
        w = corpus_wer(pairs)
        print(f"| {name} | {c['cer']:.3f} | {w['wer']:.3f} | "
              f"{touched} из {len(refs)} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
