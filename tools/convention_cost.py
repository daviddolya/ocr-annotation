#!/usr/bin/env python3
"""The price of one sentence in the guidelines -- this time in transcription.

Takes the ground truth and derives several "annotations" from it in which THE
TEXT IS READ CORRECTLY DOWN TO THE CHARACTER. Only the writing rule differs:
whether case is normalised, whether punctuation is dropped. Everything the
table shows is the price of a rule, not of careless reading.

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
    print(f"legible objects {len(refs)}, reference characters {chars}; "
          "in every variant the text is read correctly down to the character")
    print()
    print("| transcription rule | CER | WER | objects touched |")
    print("|---|---|---|---|")
    for key in ORDER:
        name, func = NORMALIZERS[key]
        pairs = [(r, func(r)) for r in refs]
        touched = sum(1 for r, h in pairs if r != h)
        c = corpus_cer(pairs)
        w = corpus_wer(pairs)
        print(f"| {name} | {c['cer']:.3f} | {w['wer']:.3f} | "
              f"{touched} of {len(refs)} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
