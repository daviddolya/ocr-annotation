#!/usr/bin/env python3
"""Rehearsing the pipeline before annotating: a stand-in "my" annotation.

Spending an hour annotating and only then discovering that the computation
crashes or the renderer draws the wrong thing is a bad order of work. This
script takes the ground truth and damages it in known ways, impersonating a
plausible annotator:

  * a shaky hand -- vertices displaced by a few pixels;
  * some curved objects outlined with four points instead of a contour;
  * some transcriptions typed in lowercase;
  * two legible objects marked illegible and one the other way round;
  * one object skipped, one spurious object added.

The numbers that come out have nothing to do with my own work. The point is
only to confirm that the pipeline runs and the images open.

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
        if n == 4:                                   # one object skipped
            continue
        ring = o.ring
        if o.ornt == "c" and rnd.random() < 0.4:     # boxed instead of outlined
            ring = o.bbox_ring()
        ring = [(x + rnd.gauss(0, args.jitter), y + rnd.gauss(0, args.jitter))
                for x, y in ring]
        text = o.text
        if o.legible and rnd.random() < 0.35:        # typed in lowercase
            text = text.lower()
        if o.legible and flipped < 2 and rnd.random() < 0.1:
            text = "#"                               # judged illegible
            flipped += 1
        elif not o.legible and rnd.random() < 0.15:
            text = "TEXT"                            # the other way: read it out
        mine.append(TextObject(image=o.image, ring=ring, text=text,
                               ident=1000 + n))

    extra = gt[0]                                    # one spurious object
    mine.append(TextObject(image=extra.image, ident=9001, text="EXTRA",
                           ring=[(x + 400, y + 200) for x, y in extra.ring]))

    args.out.mkdir(parents=True, exist_ok=True)
    frames = save_icdar(mine, args.out)
    print("THIS IS A STAND-IN ANNOTATION, NOT MINE. Its numbers mean nothing.")
    print(f"reference objects {len(gt)}, stand-in {len(mine)}, frames {frames}")
    print(f"{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
