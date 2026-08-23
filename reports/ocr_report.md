# Scene-text annotation agreement: polygons and transcriptions

Stage A5 of an annotation-quality portfolio. The annotation was done by hand
in CVAT, blind to the ground truth -- it was not opened until the batch was
handed in -- and compared against Total-Text (test split).

## 1. What was annotated

10 Total-Text frames, 67 reference objects, 79 of mine. Each object has two
sides: a polygon around the word and a transcription in the `text` attribute.
Exported from CVAT in the ICDAR Text Localization 1.0 format and checked by
`check_export.py` before anything was computed: 448 vertices, 78 filled
transcriptions, one marked illegible, none empty, and a frame set matching the
selection manifest.

Frames were selected on three conditions: 5-9 objects per frame, curved text
necessarily present, no more than half of it illegible. Curved objects make up
28 of the 67 in the set (42%) against 38% in the dataset at large -- a
deliberate bias, and one that means the mean IoU in this report cannot be
compared directly with other Total-Text numbers.

**The thresholds, stated explicitly.** Matching is greedy by descending mask
IoU with a threshold of 0.5. CER is micro-averaged: total edits over total
reference length, rather than a mean of per-object values (the macro figure is
quoted alongside for comparison).

## 2. Method

Three metrics of different natures, and none of them substitutes for the rest.

**Geometry -- mask IoU.** Contours are rasterised into masks and the
intersection is divided by the union. A text polygon is non-convex and often
curved; that kind of intersection is not computed analytically.

**Text -- CER and WER.** Levenshtein distance normalised by the length of the
reference string. The denominator is the reference on purpose: normalising by
my own string would give a metric I could improve by writing more characters.
That also gives the property people mistake for a bug -- CER is not capped at
one. WER takes the word as the unit of edit; on a word-level dataset it
collapses into the share of objects transcribed non-identically, and it earns
its place by separating "an error in every word" from "one word read entirely
wrong".

**Legibility -- raw agreement and Cohen's kappa.** Neither IoU nor CER sees
this axis: an object I called illegible and the reference read simply drops
out of the CER computation and silently improves it. The kappa stands next to
the raw share because with a rare class the raw share is high all by itself.

**Why mean IoU is computed over pairs only -- and what therefore stands next
to it.** A word drawn completely off target does not clear the 0.5 threshold,
forms no pair, and never damages the mean: the worst cases leave the
numerator. So the unmatched count is quoted next to the mean IoU every time,
never in a footnote. In this report: 43 pairs, 24 reference objects unmatched,
36 of mine -- fewer than two thirds of the reference is covered by pairs, and
the mean IoU of 0.784 has to be read together with that.

## 3. Result

```
frames 10; reference objects 67, mine 79
matching threshold mask IoU 0.5: pairs 43, reference unmatched 24, mine unmatched 36

mask IoU over pairs: mean 0.784, median 0.820, minimum 0.516
```

| orientation of the reference text | pairs | mean IoU |
|---|---|---|
| horizontal | 11 | 0.814 |
| slanted | 6 | 0.831 |
| curved | 24 | 0.769 |
| illegible | 2 | 0.654 |

```
pairs where both sides read the text: 41 (229 reference characters)
CER 0.223 (micro) | 0.188 (macro) | WER 0.268 | exact matches 30 of 41
CER with both sides folded to lowercase: 0.013
agreement on legible / illegible: 0.953, Cohen's kappa 0.000
```

| legibility, reference \ mine | legible | illegible |
|---|---|---|
| legible | 41 | 0 |
| illegible | 2 | 0 |

## 4. Systematic disagreements

**Case accounts for 94% of all reading error.** CER 0.223 against 0.013 once
both sides are folded to the same case. All 41 text pairs are affected. The
rule "fold everything to UPPERCASE" was adopted before annotating, and its
price was measured in advance on these very frames -- 0.227 -- and matched the
outcome. This is fixed not by a guideline but by declaring the convention when
the batch is handed in. The annotation was not rewritten.

**Small text on a stamp -- 15 objects from one element.** In img574 the words
SPREAD SOME AWESOME run in small type around the AWESOME! stamp. The reference
marks the whole stamp as one "#" object; I annotated 15 words. That is 42% of
everything unmatched on my side, out of one spot in one frame. Both sides are
right: a word detector needs words, sign intake needs one object. Fixed by a
guideline, but the rule is set by the client before the batch (revision 9).

**The legibility threshold -- 15 reference "#" objects unmatched against one
of mine.** Agreement 0.953 with a kappa of 0.000: formally almost everything
matched, in practice I reported nothing on that axis. The threshold "I can
name every character" turned out to be a threshold of magnification rather
than a property of the image. Fixed by a guideline: the decision is made at
ordinary viewing scale (revision 8).

**The contour is 14% tighter than the reference, and seven pairs failed
because of it.** Median area ratio 0.863; my contour is smaller in 40 pairs of
43. On objects under 3000 px² the mean IoU is 0.729 against 0.831 on large
ones: a constant margin on the reference side eats a larger share of a small
word. Seven pairs read identically -- THE 0.411, PEAK 0.435, TM 0.419, More
0.478, Than 0.444, Just 0.455, TAYLOR 0.487 -- landed just short of the 0.5
threshold and went into "unmatched" on both sides. Same category as a split
pair on A2. Fixed by a guideline: the offset is declared on handover
(revision 7).

**Partially legible words -- a hole in version 1 of the guidelines.** Five
objects were written per character (ISL##D, #####, ###) while version 1
defined "#" only as a marker for a whole object. The rule existed in the hand
and not on paper; it was added as revision 6, and no transcription was
rewritten after the fact.

## 5. Geometry or text

**The direct answer: geometry and the definition of an object produced more
disagreement than reading did.** The numbers behind that: out of 67 reference
objects and 79 of mine, 43 formed pairs -- 60 objects were left unpaired.
Meanwhile the reading error, stripped of convention, comes to CER 0.013, about
three wrong characters in 229. The two metrics are of different natures and
are compared by their contribution to rework rather than by their values: 60
unmatched objects is an editor's pass over each one, three characters is
proofreading a single line.

**How much of the reading error is convention: 94%.** CER 0.223 falls to 0.013
once both sides are folded to the same case. That is the strongest number of
the stage, because it separates "the annotator reads badly" from "the
annotator reads correctly and writes by another rule". On intake those are two
entirely different decisions -- in the second case the batch is not rejected,
it is converted by a script.

**The price of every rule was computed before annotating, not after.** Folding
to lowercase -- CER 0.702 over the whole set, to uppercase 0.245 (0.227 on
these frames); dropped punctuation -- 0.005, which makes case 140 times more
expensive than punctuation. A box instead of a contour -- IoU 0.885 on
horizontal text against 0.502 on curved. Four vertices instead of eight on a
curved word -- 0.461 against 0.904. Hence a ready answer to the question of
what two annotators agree on by themselves and where they diverge for certain:
they agree on punctuation, they diverge on case and on vertex count, and each
of those is removed by a single line of instruction.

**The portfolio conclusion: three annotation types, three different
conventions, one finding.**

| stage | question | what the reference does | price |
|---|---|---|---|
| A3, tracks | an object past the frame border | MOT17 carries the box beyond it | 72 of 77 misses |
| A4, skeletons | a point past the frame border | COCO places none at all, `v=0` | 0 of 40,255 points outside |
| A5, text | how case is written | Total-Text passes it through as on the sign | 94% of reading error |

The same question in form -- what to do at the edge of where a rule applies --
has three different answers across three datasets, and none of them is more
correct than the others. The finding, resting on three independent
measurements rather than one observation: **an agreement metric measures the
agreement of conventions no less than the agreement of hands.** Which is why a
convention is declared when a batch is handed in rather than assumed, and why
intake begins with "by what rule was this annotated" rather than with a number.

## 6. What changed in the guidelines

Version 1 (`annotation/GUIDELINES.md`) was written before annotating and has
not been edited: the history of the rules is an artefact in itself. Four rules
were added after the analysis, on 2026-08-23.

| revision | subject | what triggered it |
|---|---|---|
| 6 | per-character "#" in a partially legible word | 5 objects, no rule in v1 |
| 7 | contour hugs the glyphs, offset is declared | contour 14% tighter, 7 split pairs |
| 8 | legibility decided at ordinary viewing scale | 1 "#" against 18, kappa 0.000 |
| 9 | granularity of small text is a client question | 15 objects from one stamp |

## Limitations

**229 reference characters is not much.** CER here is an order of magnitude
rather than a measurement to the second decimal: one long word read wrong
moves it noticeably. What does hold at this size is the gap between CER and
case-insensitive CER: that is about a rule, and a rule either applies to the
whole set or does not.

**The legibility kappa is noisy.** There are about two dozen legible and two
dozen illegible objects, and a kappa of zero here means "I marked almost
nothing illegible" rather than measured independence.

**Orientation comes from the reference, not from my annotation.** The IoU
breakdown by orientation reads as "how I did on text the reference considers
curved"; on my side no such attribute exists at all.

**10 frames.** The size was chosen so that the metric would hold while the
work fit into an evening: 67 reference objects, 448 vertices placed by hand,
260 characters of transcription.

## Neighbouring stages

- [A2, polygons](https://github.com/daviddolya/polygon-annotation-agreement) — mask IoU, Dice, Boundary IoU; `common/polygons.py` is ported from there
- [A3, tracks](https://github.com/daviddolya/tracking-annotation-agreement) — IDF1, ID switches, the frame-border convention
- [A4, skeletons](https://github.com/daviddolya/keypoint-annotation) — OKS, PCK, visibility-flag agreement
- [P2, boxes](https://github.com/daviddolya/detection-annotation-quality) — kappa 0.914, mean IoU 0.867 over 100 frames
