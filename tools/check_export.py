#!/usr/bin/env python3
"""Checking the export by the numbers before computing anything.

Four things break silently and produce not an error but a wrong number:

  1. THE TRANSCRIPTIONS DID NOT COME OUT. The attribute is not named `text`,
     or the chosen format does not carry text at all. The files hold bare
     coordinates with no quoted string. Symptom downstream: CER equals one
     on every object.
  2. THE POLYGONS TURNED OUT TO BE BOXES. Every object with four vertices on
     curved text is not an annotation but a bounding box, and IoU will hit a
     ceiling near 0.5 no matter how careful the hand was.
  3. THE WRONG SET OF FRAMES. The export came from a different task.
  4. EMPTY TRANSCRIPTIONS. An empty string and an "illegible" marker are
     different things: the first means "forgot to type it", the second is a
     decision that was made.

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
                    help="directory holding gt_<image>.txt from the export")
    ap.add_argument("--selection", type=Path, default=None)
    args = ap.parse_args()

    objs = load_cvat_icdar(args.mine)
    problems = 0

    if not objs:
        print("ZERO OBJECTS. Either the task was never moved to completed, or the")
        print("wrong format was chosen: it has to be ICDAR Text Localization 1.0.")
        return 1

    grouped = by_image(objs)
    print(f"frames {len(grouped)}, objects {len(objs)}, "
          f"vertices in total {sum(o.vertices for o in objs)}")

    empty = [o for o in objs if o.text == ""]
    illegible = [o for o in objs if o.text in ILLEGIBLE]
    legible = [o for o in objs if o.legible]
    print(f"transcriptions: filled {len(legible)}, "
          f"marked illegible {len(illegible)}, empty {len(empty)}")
    if not legible:
        problems += 1
        print("NOT A SINGLE TRANSCRIPTION. The attribute is not named `text`, or the")
        print("export format does not carry text. There is nothing to compute.")
    elif empty:
        problems += 1
        print(f"{len(empty)} objects with an empty transcription. An empty string means")
        print("\"forgot to type it\"; a deliberate \"cannot be read\" is written as \"#\".")

    verts = Counter(o.vertices for o in objs)
    four = verts.get(4, 0)
    print("vertices per object: " + ", ".join(
        f"{n} on {c}" for n, c in sorted(verts.items())))
    if four == len(objs):
        problems += 1
        print("EVERY OBJECT HAS EXACTLY FOUR VERTICES. These look like boxes rather")
        print("than contours: on curved text that caps IoU at around 0.5.")
    elif four > 0.8 * len(objs):
        print(f"four-vertex objects {four} of {len(objs)} -- rather many for a set")
        print("where over a third of the text is curved. Worth a look by eye.")

    up = sum(1 for o in legible if o.text.isupper())
    low = sum(1 for o in legible if o.text.islower())
    print(f"case: all UPPERCASE {up}, all lowercase {low}, "
          f"the rest {len(legible) - up - low}")
    if legible and low == len(legible):
        print("everything is lowercase -- is that a deliberate guideline decision?")
        print("If not, retyping now is cheaper: the rule costs about CER 0.7.")

    if args.selection:
        want = set(json.loads(args.selection.read_text(encoding="utf-8"))["files"])
        have = set(grouped)
        missing = sorted(want - have)
        extra = sorted(have - want)
        if missing:
            problems += 1
            print(f"NO ANNOTATION on {len(missing)} selected frames: "
                  f"{', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''}")
        if extra:
            print(f"frames outside the selection: {len(extra)}")
        if not missing and not extra:
            print(f"the frame set matches the selection manifest ({len(want)})")

    print()
    print("check passed, safe to compute" if problems == 0
          else f"problems: {problems}. Fix first, compute after.")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
