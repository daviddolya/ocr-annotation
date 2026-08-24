#!/usr/bin/env python3
"""Assembling the README from the metrics and the pair review.

The technique is carried over from A2, A3 and A4 and works the same way: the
numbers are generated from reports/ocr_metrics.json, while my own commentary
survives. Text between the markers <!-- note:key --> and <!-- /note --> is read
out of the existing README and carried into the new one, so a rebuild never
overwrites anything written by hand.

The unit of a section here is a PAIR -- a reference word against my word -- and
both axes are quoted for each: IoU and CER. The whole point is that they stand
side by side.

    .venv/bin/python tools/build_readme.py
"""

import argparse
import json
import re
from pathlib import Path

PLACEHOLDER = "> **What happened here:** _to be filled in_"
NOTE_RE = re.compile(r"<!-- note:(?P<key>[^\s>]+) -->\n(?P<body>.*?)\n<!-- /note -->",
                     re.DOTALL)


def existing_notes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {m.group("key"): m.group("body").strip()
            for m in NOTE_RE.finditer(path.read_text(encoding="utf-8"))}


def load_manifest(path: Path) -> list[dict]:
    return (json.loads(path.read_text(encoding="utf-8"))
            if path.exists() else [])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metrics", type=Path, default=Path("reports/ocr_metrics.json"))
    p.add_argument("--readme", type=Path, default=Path("README.md"))
    p.add_argument("--review", default="reports/review")
    p.add_argument("--repo", default="ocr-annotation-agreement")
    a = p.parse_args()

    m = json.loads(a.metrics.read_text(encoding="utf-8"))
    notes = existing_notes(a.readme)
    review = Path(a.review)
    pairs = load_manifest(review / "pairs_manifest.json")
    splits = load_manifest(review / "split" / "split_manifest.json")

    out = [f"# {a.repo}", "",
           "Annotation agreement on scene text: a polygon around the word plus a",
           "transcription. Every object is annotated twice over in effect, so there",
           f"are two metrics of different natures. {m['frames']} Total-Text frames were",
           "annotated by hand, blind to the ground truth.",
           "Stage A5 of an annotation-quality portfolio.", "",
           "<!-- note:intro -->", notes.get("intro", PLACEHOLDER), "<!-- /note -->", "",
           "## Result", "", "| | |", "|---|---|",
           f"| frames | {m['frames']} |",
           f"| objects, mine / reference | {m['my_objects']} / {m['gt_objects']} |",
           f"| pairs matched | {m['matched']} |",
           f"| **mask IoU over pairs** | **{m['iou_mean']:.3f}** |",
           f"| **CER** | **{m['cer']:.3f}** |",
           f"| WER | {m['wer']:.3f} |",
           f"| exact matches | {m['exact_matches']} of {m['text_pairs']} |",
           f"| agreement on legible / illegible | {m['legibility_agreement']:.3f} |",
           f"| Cohen's kappa on legibility | {m['legibility_kappa']:.3f} |", "",
           f"The matching threshold is mask IoU {m['iou_threshold']}. Mean IoU is computed",
           "only over matched pairs, which is why the unmatched counts have to stand",
           f"next to it: {m['unmatched_gt']} reference objects and {m['unmatched_mine']} of mine. "
           "A word drawn completely",
           "off target never enters a pair and never hurts the mean -- it lands there.", ""]

    out += ["## Geometry or text", "",
            "The central question of the stage. The two axes measure different things",
            "and cannot be averaged into one number: a contour is fixed by a rule about",
            "boundaries, a transcription by a rule about case and punctuation.", ""]
    if m.get("iou_by_orientation"):
        out += ["| orientation of the reference text | pairs | mean IoU |", "|---|---|---|"]
        for name, v in sorted(m["iou_by_orientation"].items(), key=lambda kv: kv[1]["iou"]):
            out.append(f"| {name} | {v['pairs']} | {v['iou']:.3f} |")
        out.append("")
    if (review / "iou_by_orientation.png").exists():
        out += [f"![IoU by orientation]({a.review}/iou_by_orientation.png)", ""]
    if (review / "geometry_vs_text.png").exists():
        out += ["One point per pair: geometry along the horizontal axis, text along the",
                "vertical. Disagreements that pile up against one axis are a different",
                "problem with a different cure.", "",
                f"![geometry vs text]({a.review}/geometry_vs_text.png)", ""]

    out += ["## How much of the error is convention", "",
            f"CER as measured is **{m['cer']:.3f}**. The same computation after folding both",
            f"sides to lowercase gives **{m['cer_case_insensitive']:.3f}**. The gap is exactly the part of",
            "the error explained by the writing rule rather than by reading: "
            f"**{m['case_share']:.0%}**.", "",
            "CER is micro-averaged (edits divided by all "
            f"{m['ref_chars']} reference characters);",
            f"macro-averaging, the mean over objects, would give {m['cer_macro']:.3f}. "
            "The gap between",
            "the two widens as words get shorter, so a report says which one it quotes.", ""]

    out += ["## Legible or not", "",
            "A separate axis that neither IoU nor CER can see: an object I called",
            "illegible and the reference read simply drops out of the CER computation",
            "and silently improves it.", "",
            "| reference \\ mine | legible | illegible |", "|---|---|---|",
            f"| legible | {m['legibility_matrix'][0][0]} | {m['legibility_matrix'][0][1]} |",
            f"| illegible | {m['legibility_matrix'][1][0]} | {m['legibility_matrix'][1][1]} |",
            "",
            f"Raw agreement {m['legibility_agreement']:.3f} against a kappa of "
            f"{m['legibility_kappa']:.3f}. The kappa stands next to it",
            "because with a rare class the raw share is high all by itself.", ""]

    if pairs:
        out += ["## The worst pairs", "",
                "Blue is the reference, orange is mine. Both axes are quoted for each.", ""]
        for item in pairs:
            key = f"{Path(item['image']).stem}_{item['gt_id']}"
            cer_text = "--" if item["cer"] is None else f"{item['cer']:.3f}"
            axis = "geometry" if item["source"] == "geometry" else "text"
            out += [f"### {item['image']} · reference #{item['gt_id']} · {axis}", "",
                    f"IoU {item['iou']:.3f} · CER {cer_text} · "
                    f"\"{item['gt_text']}\" against \"{item['my_text']}\"", "",
                    f"![{key}]({a.review}/{item['file']})", "",
                    f"<!-- note:{key} -->", notes.get(key, PLACEHOLDER),
                    "<!-- /note -->", ""]

    if splits:
        worst = max(s["iou"] for s in splits)
        out += ["## Split pairs", "",
                f"{len(splits)} objects that both sides found and read identically, and",
                "that still formed no pair: the contours disagreed enough to fall under",
                f"the matching threshold of {m['iou_threshold']}. All of them land between",
                f"{min(s['iou'] for s in splits):.3f} and {worst:.3f} -- just short of it.", "",
                "This category is invisible in the tables above. It hides inside the",
                "unmatched counts, where nothing distinguishes it from a word one side",
                "never annotated at all, even though the two mean opposite things: one is",
                "a miss, the other is a boundary convention. The name is borrowed from",
                "stage A2, where the same thing happened to polygons.", ""]
        for item in splits:
            key = f"split_{Path(item['image']).stem}_{item['gt_id']}"
            out += [f"### {item['image']} · \"{item['gt_text']}\"", "",
                    f"IoU {item['iou']:.3f} · vertices "
                    f"{item['gt_vertices']}/{item['my_vertices']} · read identically", "",
                    f"![{key}]({a.review}/split/{item['file']})", "",
                    f"<!-- note:{key} -->", notes.get(key, PLACEHOLDER),
                    "<!-- /note -->", ""]

    out += ["## Reproduce", "",
            "Python 3.10+ with numpy and Pillow.", "", "```bash",
            "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
            "",
            "# the five self-test cases with answers known in advance,",
            "# including the one where CER comes out at 1.667",
            ".venv/bin/python common/text.py --selftest",
            "",
            "# the Total-Text ground truth, test split: 300 files, 257 KB",
            ".venv/bin/python tools/fetch_totaltext.py --out data/totaltext/gt",
            "",
            "# sanity-check the export before computing anything",
            ".venv/bin/python tools/check_export.py \\",
            "    --mine annotation/my_labels --selection data/subset/selection_text.json",
            "",
            "# the numbers in this README",
            ".venv/bin/python annotation/ocr_agreement.py \\",
            "    --gt data/totaltext/gt --mine annotation/my_labels \\",
            "    --selection data/subset/selection_text.json \\",
            "    --out reports/ocr_metrics.json",
            "",
            "# the pictures above, then this README",
            ".venv/bin/python tools/render_text.py \\",
            "    --gt data/totaltext/gt --mine annotation/my_labels \\",
            "    --images data/subset/frames \\",
            "    --selection data/subset/selection_text.json --out reports/review",
            ".venv/bin/python tools/build_readme.py",
            "```", "",
            "The 10 frames and my annotation are committed; the ground truth is 257 KB",
            "and comes down in one command, so every number reproduces from a fresh",
            "clone.", "",
            "## What else is here", "",
            "- Annotation guidelines and the disputed-case decisions — "
            "[annotation/GUIDELINES.md](annotation/GUIDELINES.md)",
            "- Full report — [reports/ocr_report.md](reports/ocr_report.md)",
            "- Code I did not write myself, and what I owe an explanation for — "
            "[DEBT.md](DEBT.md)", "",
            "## The other stages of this portfolio", "",
            "| stage | type | headline numbers |", "|---|---|---|",
            "| P2 | [boxes](https://github.com/daviddolya/detection-annotation-agreement) "
            "| kappa 0.914, mean IoU 0.867 |",
            "| A2 | [polygons and masks](https://github.com/daviddolya/polygon-annotation-agreement) "
            "| mask IoU 0.840, Boundary IoU 0.676 |",
            "| A3 | [tracks on video](https://github.com/daviddolya/tracking-annotation-agreement) "
            "| IDF1 0.896, 2 ID switches |",
            "| A4 | [skeletons](https://github.com/daviddolya/keypoint-annotation-agreement) "
            "| OKS 0.895, flag agreement 0.822 |",
            "| A5 | scene text — **this repository** "
            f"| mask IoU {m['iou_mean']:.3f}, CER {m['cer']:.3f} |", "",
            "`common/polygons.py` is ported from stage A2 with a note on its provenance.",
            "", "The README is rebuilt by `tools/build_readme.py`; the commentary between the",
            "`<!-- note:… -->` and `<!-- /note -->` markers survives a rebuild.", ""]

    a.readme.write_text("\n".join(out), encoding="utf-8")
    kept = sum(1 for v in notes.values() if v != PLACEHOLDER)
    print(f"{a.readme}: pair sections {len(pairs)}, split sections {len(splits)}, "
          f"comments kept {kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
