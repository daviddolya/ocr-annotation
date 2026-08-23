#!/usr/bin/env python3
"""Selecting frames for text annotation and downloading the images.

A frame is taken if three conditions hold, and each has a reason:

  1. FIVE TO NINE OBJECTS. The dataset holds frames with a single word and
     frames with fifty. The first kind never tests matching; the second is an
     hour of work per frame, and in that kind of clutter the ground truth
     itself annotates only every other object.
  2. CURVED TEXT PRESENT. That is why Total-Text was chosen at all: on
     straight signage a polygon barely differs from a rectangle, and half the
     substance of this stage disappears.
  3. NO MORE THAN HALF ILLEGIBLE. A frame where the reference marked almost
     everything as "#" yields neither transcriptions nor meaningful agreement.

What the frames say and how many objects they hold is NOT printed: the
annotation is done blind. The distribution is available under --stats, which
should be run after annotating.

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
            print(f"  {dest.name}: attempt {attempt} failed ({e})")
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--min-objects", type=int, default=5)
    ap.add_argument("--max-objects", type=int, default=9)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--stats", action="store_true",
                    help="the reference distribution -- look AFTER annotating")
    args = ap.parse_args()

    objs = load_totaltext(args.gt)
    if not objs:
        raise SystemExit(f"no poly_gt_*.txt found in {args.gt}")
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
        raise SystemExit(f"only {len(pool)} candidates, {args.count} requested")

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
        "source": f"Total-Text, test split, mirror {REPO}",
        "task": "a polygon around the word plus a transcription in an attribute",
        "filters": {"objects_per_frame": [args.min_objects, args.max_objects],
                    "needs_curved": True, "illegible_at_most": "half"},
        "seed": args.seed,
        "count": len(picked),
        "files": picked,
    }
    (args.out / "selection_text.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"candidates {len(pool)}, frames selected {len(picked)}, {total / 1e6:.2f} MB")
    print(f"frames: {frames}")
    print(f"manifest: {args.out / 'selection_text.json'}")

    if args.stats:
        items = [o for k in picked for o in grouped[k]]
        legible = [o for o in items if o.legible]
        orn = Counter(o.ornt for o in items)
        print()
        print(f"[stats] objects {len(items)}, legible {len(legible)}, "
              f"{len(items) / len(picked):.1f} per frame")
        print(f"[stats] vertices {sum(o.vertices for o in items)}, "
              f"characters {sum(len(o.text) for o in legible)}")
        print(f"[stats] orientation: curved {orn['c']}, horizontal "
              f"{orn['h']}, slanted {orn['m']}, illegible {orn['#']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
