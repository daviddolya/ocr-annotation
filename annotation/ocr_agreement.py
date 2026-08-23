#!/usr/bin/env python3
"""Text-annotation agreement: geometry and text measured apart.

The main script of the stage. A four-stage pipeline whose point is that
stages 2 and 3 measure DIFFERENT things and do not collapse into one number.

  1. WHO IS COMPARED WITH WHOM. Within a frame my contours are matched to the
     reference ones greedily by descending mask IoU, threshold 0.5. The
     matching code is ported from A2 (common/polygons.py, match_polys).
     The bias that follows has to be named in the report: mean IoU is computed
     ONLY over matched pairs, so a word drawn completely off target never
     enters a pair and never hurts the metric -- it lands in the "unmatched"
     row instead. That is why both numbers are always quoted together.

  2. GEOMETRY. Mask IoU over pairs, broken down by the orientation of the
     reference text: curved, horizontal, slanted. The breakdown is not
     decoration -- on straight text a polygon barely differs from a box, and
     an overall mean IoU without it explains nothing.

  3. TEXT. CER and WER over pairs where both sides judged the object legible.
     Alongside them, the same CER after folding BOTH sides to lowercase: the
     gap between the two numbers is exactly the part of the error explained by
     the writing convention rather than by reading.

  4. LEGIBILITY. Agreement on "legible / illegible" as its own metric, with
     Cohen's kappa. Neither IoU nor CER sees this axis: an object I called
     illegible and the reference read simply drops out of the CER computation
     and silently improves it.

    python3 annotation/ocr_agreement.py --gt data/totaltext/gt \
        --mine annotation/my_labels --selection data/subset/selection_text.json \
        --out reports/ocr_metrics.json
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from icdar import by_image, load_cvat_icdar, load_totaltext  # noqa: E402
from polygons import Poly, match_polys, rasterize  # noqa: E402
from text import corpus_cer, corpus_wer, cer as pair_cer  # noqa: E402

ORNT_NAMES = {"h": "horizontal", "m": "slanted",
              "c": "curved", "#": "illegible", "v": "vertical"}
MAX_SIDE = 1600


def frame_masks(groups: list[list], ):
    """Rasterises every object of a frame inside one shared local box.

    The box is shared and scaled down: full photo resolution is not needed
    here, and on three-thousand-pixel frames the masks would eat memory.
    """
    rings = [o.ring for g in groups for o in g]
    if not rings:
        return [[] for _ in groups]
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    scale = min(1.0, MAX_SIDE / max(w, h, 1))
    width = max(2, int(w * scale) + 2)
    height = max(2, int(h * scale) + 2)
    out = []
    for g in groups:
        masks = []
        for o in g:
            flat = [c for p in o.ring
                    for c in ((p[0] - x0) * scale, (p[1] - y0) * scale)]
            masks.append(rasterize(Poly(cls=o.text, parts=[flat]), width, height))
        out.append(masks)
    return out


def kappa_2x2(matrix: list[list[int]]) -> float:
    total = sum(sum(r) for r in matrix)
    if not total:
        return 0.0
    observed = (matrix[0][0] + matrix[1][1]) / total
    rows = [sum(r) / total for r in matrix]
    cols = [(matrix[0][j] + matrix[1][j]) / total for j in range(2)]
    expected = sum(rows[i] * cols[i] for i in range(2))
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--mine", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/ocr_metrics.json"))
    ap.add_argument("--iou-threshold", type=float, default=0.5)
    args = ap.parse_args()

    images = set(json.loads(args.selection.read_text(encoding="utf-8"))["files"])
    gt = load_totaltext(args.gt, images=images)
    mine = load_cvat_icdar(args.mine, images=images)
    g_by, m_by = by_image(gt), by_image(mine)

    pairs = []
    lost_gt, lost_mine = [], []
    for image in sorted(images):
        gs, ms = g_by.get(image, []), m_by.get(image, [])
        if not gs or not ms:
            lost_gt.extend(gs)
            lost_mine.extend(ms)
            continue
        masks_gt, masks_mine = frame_masks([gs, ms])
        matched, extra, missing = match_polys(
            [Poly(o.text, [o.flat()]) for o in ms],
            [Poly(o.text, [o.flat()]) for o in gs],
            masks_mine, masks_gt, args.iou_threshold)
        for i, j, score in matched:
            pairs.append((gs[j], ms[i], score))
        lost_mine.extend(ms[i] for i in extra)
        lost_gt.extend(gs[j] for j in missing)

    print(f"frames {len(images)}; reference objects {len(gt)}, mine {len(mine)}")
    print(f"matched by mask IoU, threshold {args.iou_threshold}: "
          f"pairs {len(pairs)}, reference unmatched {len(lost_gt)}, "
          f"mine unmatched {len(lost_mine)}")
    if not pairs:
        raise SystemExit("no pairs at all: check the export with tools/check_export.py")

    # --- geometry
    ious = [s for _, _, s in pairs]
    by_ornt = defaultdict(list)
    for g, _, s in pairs:
        by_ornt[g.ornt].append(s)
    print()
    print(f"mask IoU over pairs: mean {statistics.mean(ious):.3f}, "
          f"median {statistics.median(ious):.3f}, minimum {min(ious):.3f}")
    print("| orientation of the reference text | pairs | mean IoU |")
    print("|---|---|---|")
    for key in ("h", "m", "c", "#"):
        v = by_ornt.get(key, [])
        if v:
            print(f"| {ORNT_NAMES[key]} | {len(v)} | {statistics.mean(v):.3f} |")

    # --- text
    both = [(g.text, m.text) for g, m, _ in pairs if g.legible and m.legible]
    c = corpus_cer(both)
    w = corpus_wer(both)
    lowered = corpus_cer([(r.lower(), h.lower()) for r, h in both])
    print()
    print(f"pairs where both sides read the text: {len(both)} "
          f"({c['ref_chars']} reference characters)")
    print(f"CER {c['cer']:.3f} (micro) | {c['cer_macro']:.3f} (macro) | "
          f"WER {w['wer']:.3f} | exact matches {c['exact']} of {len(both)}")
    print(f"CER with both sides folded to lowercase: {lowered['cer']:.3f}")
    share = (c["cer"] - lowered["cer"]) / c["cer"] if c["cer"] > 0 else 0.0
    print(f"  so the case convention accounts for {share:.0%} of all reading error")

    # --- legibility
    matrix = [[0, 0], [0, 0]]
    for g, m, _ in pairs:
        matrix[0 if g.legible else 1][0 if m.legible else 1] += 1
    total = sum(sum(r) for r in matrix)
    agree = (matrix[0][0] + matrix[1][1]) / total
    k = kappa_2x2(matrix)
    print()
    print(f"agreement on legible / illegible: {agree:.3f}, Cohen's kappa {k:.3f}")
    print("| reference \\ mine | legible | illegible |")
    print("|---|---|---|")
    print(f"| legible | {matrix[0][0]} | {matrix[0][1]} |")
    print(f"| illegible | {matrix[1][0]} | {matrix[1][1]} |")

    worst_geom = sorted(pairs, key=lambda t: t[2])[:5]
    worst_text = sorted(
        [(g, m, pair_cer(g.text, m.text)) for g, m, _ in pairs
         if g.legible and m.legible], key=lambda t: -t[2])[:5]
    print()
    print("worst by geometry:")
    for g, m, s in worst_geom:
        print(f"  {g.image} ref#{g.ident}: IoU {s:.3f}, vertices {g.vertices}/{m.vertices}, "
              f"\"{g.text}\" vs \"{m.text}\"")
    print("worst by text:")
    for g, m, value in worst_text:
        print(f"  {g.image} ref#{g.ident}: CER {value:.3f}, \"{g.text}\" vs \"{m.text}\"")

    doc = {
        "frames": len(images),
        "gt_objects": len(gt), "my_objects": len(mine),
        "matched": len(pairs),
        "unmatched_gt": len(lost_gt), "unmatched_mine": len(lost_mine),
        "iou_threshold": args.iou_threshold,
        "iou_mean": statistics.mean(ious), "iou_median": statistics.median(ious),
        "iou_by_orientation": {ORNT_NAMES.get(k2, k2): {
            "pairs": len(v), "iou": statistics.mean(v)} for k2, v in by_ornt.items()},
        "text_pairs": len(both), "ref_chars": c["ref_chars"],
        "cer": c["cer"], "cer_macro": c["cer_macro"], "wer": w["wer"],
        "cer_case_insensitive": lowered["cer"], "case_share": share,
        "exact_matches": c["exact"],
        "legibility_agreement": agree, "legibility_kappa": k,
        "legibility_matrix": matrix,
        "worst_geometry": [{"image": g.image, "gt_id": g.ident, "iou": s,
                            "gt_text": g.text, "my_text": m.text,
                            "gt_vertices": g.vertices, "my_vertices": m.vertices}
                           for g, m, s in worst_geom],
        "worst_text": [{"image": g.image, "gt_id": g.ident, "cer": v,
                        "gt_text": g.text, "my_text": m.text}
                       for g, m, v in worst_text],
        "pairs": [{"image": g.image, "gt_id": g.ident, "my_id": m.ident,
                   "iou": s, "ornt": g.ornt, "gt_text": g.text, "my_text": m.text,
                   "cer": (pair_cer(g.text, m.text)
                           if g.legible and m.legible else None)}
                  for g, m, s in pairs],
        "unmatched_gt_list": [{"image": o.image, "id": o.ident, "text": o.text,
                               "ornt": o.ornt} for o in lost_gt],
        "unmatched_mine_list": [{"image": o.image, "id": o.ident, "text": o.text}
                                for o in lost_mine],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"metrics: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
