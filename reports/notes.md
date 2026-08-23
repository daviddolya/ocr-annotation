# Working notes

## Step 1 -- CER and WER

Prediction: CER for "PARKING" against "parking" will be about 1.0
Outcome: exactly 1.0000. All five control cases matched.

Why: CER counts edits character by character, and "P" -> "p" is the same
substitution as "P" -> "X". Seven letters, seven substitutions, a reference of
seven. The metric has no notion of "the same letter": to it, case is not
cosmetics but 70% of the characters in the set. The same reasoning gives
1.6667 in the fourth case -- the denominator is the reference, not my string,
so anything written beyond the reference pushes CER past one.

## Step 2 -- the transcription convention

How the reference writes text (300 frames, 2547 objects): 332 illegible (13%);
of the 2215 legible ones, 65% entirely uppercase, 9% lowercase, 20% mixed, 6%
digits only. Uppercase letters: 8498 of 12,108 characters (70%). Punctuation
appears on 55 objects (2%), almost entirely apostrophes, hyphens and periods.

The price of each rule under flawless reading, my 10 frames (50 legible
objects, 260 characters):

| rule | CER | WER | touched |
|---|---|---|---|
| as the reference does | 0.000 | 0.000 | 0 of 50 |
| everything to lowercase | 0.719 | 0.880 | 44 of 50 |
| everything to UPPERCASE | 0.227 | 0.260 | 13 of 50 |
| punctuation dropped | 0.000 | 0.000 | 0 of 50 |

Over the whole set the same: 0.702, 0.245, 0.005.

Conclusion: case is 140 times more expensive than punctuation. The stage
benchmark is CER below 0.1 on legible text, and a single writing rule misses
it by a factor of seven without a single reading error. So the metric measures
the agreement of conventions no less than the agreement of hands, which is why
a convention is declared when a batch is handed in.

The decisions are recorded in `annotation/GUIDELINES.md`, version 1, before
annotating.

### The four decisions taken on 2026-08-23, before annotating

1. **Case -- fold everything to UPPERCASE.** A deliberate divergence from the
   reference at a cost of 0.227 CER on my frames. Reason: case is the largest
   source of disagreement between hands, an unambiguous rule removes the whole
   class of dispute and can be checked automatically. The report quotes CER
   twice, as measured and case-insensitive, and the gap shows what the
   convention costs.
2. **Punctuation -- as it appears, typographic marks folded to straight.**
   Costs 0.005 over the set and 0.000 on my frames; written down for the next
   batch.
3. **The legibility threshold -- I can name every character while looking at
   that character alone.** Guessing from context or from the brand does not
   count. Stricter, so there will be more "#".
4. **The frame border -- always transcribe what is visible, no "#", nothing
   invented.** A "less than half the word" threshold was rejected: it requires
   estimating the length of a word that cannot be seen.

## Step 3 -- the price of geometry

A box instead of a contour, reference, 2543 objects: horizontal text 0.885,
slanted 0.678, curved 0.502, illegible 0.722. The same on my 10 frames:
horizontal 0.872 (14 objects), slanted 0.518 (7), curved 0.497 (28), illegible
0.745 (18), everything together 0.644.

The vertex budget (289 reference objects with 8+ vertices; keeping n points of
the contour):

| vertices | mean IoU | median | share with IoU < 0.8 |
|---|---|---|---|
| 4 | 0.461 | 0.477 | 100% |
| 6 | 0.726 | 0.728 | 68% |
| 8 | 0.904 | 0.958 | 20% |
| 10 | 0.975 | 1.000 | 2% |

**Decision: eight vertices on a curved word, four on a straight one. A word
counts as curved if any arc is visible.**

Why eight. Between four and eight IoU doubles (0.461 -> 0.904) for four
clicks; between eight and ten it gains 0.07 for two more. Six would have given
0.726 -- above the matching threshold of 0.5, but with 68% of objects still
below 0.8, meaning the batch would be handed in on the edge.

Work recomputed: 28 curved objects at eight vertices plus 39 others at four --
about 380 vertices against 366 in the reference. The decision lands roughly
inside the reference budget rather than doubling it. The "any visible arc"
criterion is fuzzy and may pull some of the seven slanted objects into the
eight-vertex group, which would push it closer to 410.

Separately: 28 curved objects out of 67 is 42%, more than in the dataset at
large (38%). Frame selection required curved text to be present, so the bias
is expected, and the report has to name it: the mean IoU of this stage cannot
be compared directly with other people's Total-Text numbers.

## Step 4 -- the export

`check_export.py` before computing anything:

```
frames 10, objects 79, vertices in total 448
transcriptions: filled 78, marked illegible 1, empty 0
vertices per object: 4 on 40, 5 on 4, 6 on 4, 7 on 4, 8 on 27
case: all UPPERCASE 70, all lowercase 0, the rest 8
the frame set matches the selection manifest (10)
```

Both conventions held: uppercase everywhere except eight objects (digits and
mixed), and 27 objects got eight vertices under rule 5. The work came to 448
vertices against the planned 380-410 -- the step 3 estimate was about 12% low.

## Step 5 -- agreement

```
frames 10; reference objects 67, mine 79
matching threshold mask IoU 0.5: pairs 43, reference unmatched 24, mine unmatched 36
mask IoU over pairs: mean 0.784, median 0.820, minimum 0.516
  horizontal 11 pairs 0.814 | slanted 6 -- 0.831
  curved 24 -- 0.769 | illegible 2 -- 0.654
pairs where both sides read the text: 41 (229 reference characters)
CER 0.223 (micro) | 0.188 (macro) | WER 0.268 | exact 30 of 41
CER with both sides folded to lowercase: 0.013 -> 94% of the error is convention
agreement on legible / illegible 0.953, Cohen's kappa 0.000
```

The rehearsal on the stand-in annotation ran before the real one
(`tools/dry_run.py`) and the pipeline held: there too the entire reading error
turned out to be a case error, 100% of it.

## Step 6.2 -- systematic disagreements

**1. Case gives 94% of all reading error.** CER 0.223, the same CER
case-insensitive 0.013. All 41 text pairs are affected. Conclusion: fixed not
by a guideline but by declaring the convention on handover -- the rule was
adopted before annotating, its price was estimated in advance at 0.227 on
these very frames, and the estimate matched (0.223). The annotation stays as
it is.

**2. Small text on a stamp -- 15 objects from one element.** In img574 there
is a red AWESOME! stamp with SPREAD SOME AWESOME running in small type around
it. The reference marks the whole stamp as one "#"; I annotated 15 separate
words. That is 15 of my 36 unmatched objects -- 42% of everything unmatched on
my side, from a single object. Conclusion: both sides are right, and this is a
fork in the task rather than an error. A word detector needs words, sign
intake needs one object. Fixed by a guideline, but the rule depends on the
client and is asked before the batch rather than chosen by the annotator.

**3. The legibility threshold: 15 reference "#" unmatched against one of
mine.** Agreement on legibility 0.953 with a kappa of 0.000 -- I marked
practically everything legible, so I reported nothing on that axis. The
reference writes small text off; I read it out. Conclusion: fixed by a
guideline. The threshold "I can name every character" turned out to be about
eyesight rather than size: at enough magnification almost anything reads. It
needs to be tied to type size.

**4. My contour is systematically 14% tighter than the reference's.** Median
area ratio 0.863; my contour is smaller in 40 pairs of 43. The reference draws
with a margin around the glyphs while rule 5 says to follow the glyph boundary
-- and I followed it. On small objects (under 3000 px²) the mean IoU is 0.729
against 0.831 on large ones: a constant margin eats a larger share of a small
word. Which leads to the next item.

**5. Seven split pairs -- same word, no pair formed.** THE (IoU 0.411), PEAK
(0.435), TM (0.419), More (0.478), Than (0.444), Just (0.455), TAYLOR (0.487).
Both sides read them identically, and all seven land in 0.41-0.49, right under
the 0.5 threshold. Same category as a split pair on A2. Conclusion: fixed by a
guideline -- declare the offset from the glyphs; no re-annotation is needed,
because the divergence is constant and one sentence removes it. Images in
`reports/review/split/`.

**6. Partially legible words -- a hole in version 1.** Five objects written as
ISL##D, #####, ######, ###, `# 10 00 # ##`: "#" used per character, while
version 1 defined it only as a marker for a whole object. Conclusion: the rule
gets written down (see the revisions), but no transcription is rewritten after
the fact.
