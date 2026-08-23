# Scene-text annotation guidelines

Version 1, written before annotating. Dataset: Total-Text, 10 frames,
annotated blind -- the ground truth is not opened until the batch is handed
in. Revisions made after the disagreement analysis are appended below as a
separate dated section; version 1 stays exactly as it was.

The five rules below are decisions taken, not correct answers. Each one is
declared when the batch is handed in, together with what it costs.

## 1. Case

Every transcription is folded to UPPERCASE. "Exit" is written EXIT,
"McDonald's" becomes MCDONALD'S.

Rationale. Total-Text passes case through rather than normalising it: of 2215
legible objects, 65% are written entirely in capitals, 9% entirely lowercase,
20% mixed. So my rule diverges from the reference deliberately, and the price
of that divergence was measured in advance: 0.227 CER on my ten frames, 0.245
over the whole set. For comparison, lowercase would have cost 0.719 and 0.702
-- folding up is three times cheaper simply because two thirds of the
reference is capitals already.

Why normalise at all. Case is the largest source of disagreement between
hands, not between eyes: two annotators who read a sign identically will still
differ on whether it was set in small caps or full caps. An unambiguous rule
removes that entire class of dispute and can be checked automatically. The
price is a constant bias against this particular ground truth, and that bias
has to be visible in the report rather than hidden.

How to read it in the metric. The report quotes CER twice: as measured, and
with both sides folded to the same case. The gap between them is the share of
error contributed by the convention rather than by reading;
`ocr_agreement.py` computes it and prints it as a percentage. Expect the first
figure to sit around 0.2 even with flawless reading, and that is not a reason
to change the annotation after the fact.

## 2. Punctuation and apostrophes

Transcribed as they appear: the apostrophe in JOE'S, the hyphen in DRIVE-IN,
the period in ST., the ampersand in B&B. Typographic quotes and apostrophes
(' " ") are folded to their straight equivalents.

Rationale. Marks occur on 55 objects out of 2215 (2%) and cost CER 0.005 over
the whole set; on my ten frames there are none at all, so here the rule costs
exactly 0.000. It is written down for the next batch: unstated, it produces
disagreement in a place nobody is watching. Folding typographic marks to
straight ones is a separate decision inside this rule: to the eye ' and ' are
indistinguishable, and to CER they are different characters.

## 3. Illegible text

The contour is always drawn and the transcription written as "#". The object
is never skipped altogether.

The threshold. Legible means I can name every character while looking at that
character alone. Guessing from context, from a logo, or from knowing the brand
does not count: if I "know" what the sign says but cannot make out individual
letters, it gets "#".

Rationale. A skipped object and an object marked illegible are different
things. The first drops out of matching and damages the geometric metric; the
second takes part in it and honestly stays out of CER. A strict threshold
yields more "#" and less material for CER, but it keeps reading apart from
recognition: a word recognised from context is no longer the thing the metric
can check. The reference marks 332 of 2547 objects illegible (13%), so the
decision is routine rather than exceptional.

## 4. Text cut off by the frame border

The contour is never carried past the image boundary -- only the visible part
is outlined. Whatever is visible is transcribed, always: PARKING cropped down
to ARK is written ARK. Nothing invisible is invented and nothing is marked "#"
on account of being cropped.

Rationale. The reference does not carry contours past the border either: of
the 366 vertices in my set, not one falls outside the image. About the
transcription of a cropped word the reference says nothing, so this is my
decision, and I picked the one that does not require eyeballing how much is
missing: any threshold of the form "less than half the word" forces me to
guess the length of a word I cannot see. The price is fragments like ARK in
the data; they are honest, and the rule that produces them is declared.

On these ten frames the rule never fires: no object touches the border. It is
written down in advance because this is the third stage where the frame border
turns out to be a decision of its own, and the answer differs every time. On
A3 the MOT17 reference carried boxes past the border (72 of my 77 misses came
from that); on A4 the COCO reference placed no point beyond the border at all
-- zero out of 40,255. A convention is a property of a dataset, not of
correctness, and it has to be declared each time.

## 5. The contour and the number of vertices

The contour follows the glyph boundary, not the edge of the sign or the plate
the glyphs sit on: the reference annotates the word, not its carrier.

A straight word gets four vertices, a curved one eight. A word counts as
curved if any arc is visible: notice a bend, use eight.

Rationale. A bounding box in place of a contour costs the reference IoU 0.885
on horizontal text and 0.502 on curved -- half of it, at exactly the same
level of care. Curved objects make up 28 of the 67 in my set (42%), so the
rule touches nearly half the batch.

Why eight specifically. Measured on the 289 reference objects whose contour
has 8+ vertices: keeping 4 vertices gives mean IoU 0.461, 6 gives 0.726, 8
gives 0.904, 10 gives 0.975. Four extra clicks double IoU; the next two buy
0.07 and do not pay for themselves. Six vertices would clear the matching
threshold of 0.5, but 68% of objects would stay below 0.8 -- the batch would
be handed in on the edge.

About the criterion. "Any visible arc" is deliberately simple, and its
boundary is fuzzy: another annotator will draw it elsewhere, and some slanted
words will fall on one side or the other. It was chosen because it resolves in
half a second per object; a more precise criterion ("the baseline departs by
more than the height of a letter") asks me to measure by eye the very thing I
am about to outline anyway. Erring in this direction is cheap: extra vertices
on a straight word do not hurt IoU, while too few on a curved one costs 0.4.

The work this rule budgets: about 380 vertices over 67 objects, against 366 in
the reference.

---

# Revisions after the analysis, 2026-08-23

Version 1 above is untouched. Below are four rules added after comparing
against the ground truth on 10 frames. Each says what happened and on how many
objects.

## 6. Partially legible words

If some characters cannot be made out and others can, "#" is written for each
unreadable character, in place: ISL##D means six characters, two of them
unread. The object is not marked wholly illegible in that case.

What happened: five objects in the batch (ISL##D, #####, ######, ###,
`# 10 00 # ##`) were written exactly that way, while version 1 defined "#"
only as a marker for a whole object. The rule existed in the hand but not on
paper.

A caveat for the metric: Total-Text cannot express this -- there "#" is always
the entire object. So on a pair of my ISL##D against the reference's "#", CER
will be high for reasons that have nothing to do with reading. The rule is
declared together with that caveat when the batch is handed in.

## 7. Contour offset from the glyphs

The contour hugs the glyphs, with no margin. Rule 5 said "along the glyph
boundary", and that turned out to be too loose: a "glyph boundary" admits both
hugging and a margin.

What happened: my contour was smaller than the reference's in 40 pairs out of
43, with a median area ratio of 0.863 -- systematically 14% tighter. On small
objects (area under 3000 px²) that produced mean IoU 0.729 against 0.831 on
large ones, and seven pairs read identically on both sides (THE, PEAK, TM,
More, Than, Just, TAYLOR) landed between 0.411 and 0.487, just short of the
matching threshold of 0.5, and never formed pairs at all.

The rule itself does not change -- a tight contour is more useful to a
detector. The wording does: "hugging" is now said out loud, and the offset is
declared when the batch is handed in, because the reference has its own and on
small text the difference is worth the whole threshold.

## 8. The legibility threshold is tied to type size

Added to rule 3: legibility is decided at ordinary viewing scale, without
zooming into a single object for its own sake.

What happened: I marked exactly one object "#" where the reference marked 18
on the same frames. Agreement on legibility came to 0.953 with a Cohen's kappa
of 0.000: formally almost everything matched, in practice I reported nothing
at all on that axis. The threshold "I can name every character" turned out to
be a threshold of eyesight and patience rather than a property of the image:
at enough magnification almost anything reads.

## 9. Granularity of small repeated text

An object is a word, whatever its type size. But when small text forms a
single decorative element -- a ring around a stamp, a pattern of one repeated
phrase -- the granularity rule is asked of the client before the batch and
written into the guidelines before annotating.

What happened: in img574 the words SPREAD SOME AWESOME run in small type
around the AWESOME! stamp. I annotated 15 separate words; the reference
annotated one object with "#" for the whole stamp. That is 15 of my 36
unmatched objects -- 42% of everything unmatched on my side, out of one spot
in one frame.

Both sides are right, and that has to be said plainly: a word detector needs
words, sign intake needs one object. An annotator does not choose a fork like
this, an annotator discovers it -- and then it goes to the client rather than
being settled in silence.
