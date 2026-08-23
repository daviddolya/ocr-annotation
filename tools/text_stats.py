#!/usr/bin/env python3
"""The reference convention: how Total-Text writes its text.

Without --images it runs over the whole test split -- that is how the dataset
convention as such is measured, and that is what needs to be known before
annotating. With --images it narrows to my own subset, which is something to
look at afterwards.

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

ORNT_NAMES = {"c": "curved", "h": "horizontal",
              "m": "slanted", "#": "illegible", "v": "vertical"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--images", type=Path, default=None,
                    help="selection_text.json -- narrow to my own subset")
    args = ap.parse_args()

    images = None
    if args.images:
        images = set(json.loads(args.images.read_text(encoding="utf-8"))["files"])
    objs = load_totaltext(args.gt, images=images)
    if not objs:
        raise SystemExit("no objects found")
    legible = [o for o in objs if o.legible]

    print(f"frames {len(by_image(objs))}, objects {len(objs)}")
    print(f"illegible (transcription \"#\"): {len(objs) - len(legible)} "
          f"({(len(objs) - len(legible)) / len(objs):.0%})")

    orn = Counter(o.ornt for o in objs)
    print()
    print("| text orientation | objects | share |")
    print("|---|---|---|")
    for key, count in orn.most_common():
        print(f"| {ORNT_NAMES.get(key, key or '--')} | {count} | {count / len(objs):.0%} |")

    verts = Counter(o.vertices for o in objs)
    print()
    print("| vertices per polygon | objects |")
    print("|---|---|")
    for n, count in sorted(verts.items()):
        if count >= 10 or n <= 6:
            print(f"| {n} | {count} |")
    print(f"vertices in total {sum(o.vertices for o in objs)}, "
          f"median {statistics.median([o.vertices for o in objs]):.0f}")

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
    print(f"legible transcriptions {len(texts)}, characters {chars}, "
          f"median length {statistics.median([len(s) for s in texts]):.0f}")
    print()
    print("| how it is written | objects | share of legible |")
    print("|---|---|---|")
    print(f"| all UPPERCASE | {upper} | {upper / len(texts):.0%} |")
    print(f"| all lowercase | {lower} | {lower / len(texts):.0%} |")
    print(f"| mixed case | {mixed} | {mixed / len(texts):.0%} |")
    print(f"| digits only | {digits_only} | {digits_only / len(texts):.0%} |")
    print(f"| holds a non-alphanumeric mark | {with_punct} | {with_punct / len(texts):.0%} |")
    print()
    print(f"uppercase letters {upper_chars} of {chars} characters "
          f"({upper_chars / chars:.0%})")
    if punct:
        print("which marks occur at all: "
              + ", ".join(f'"{c}" {n}' for c, n in punct.most_common(8)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
