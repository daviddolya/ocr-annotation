#!/usr/bin/env python3
"""Transcription metrics: CER and WER.

WHAT THIS MEASURES. Levenshtein distance between two strings is the smallest
number of edits -- insert a character, delete one, substitute one for another
-- that turns one string into the other. CER normalises that count by the
length of the GROUND TRUTH:

    CER = edits(reference, mine) / len(reference)

The denominator is the reference, and that is not a detail. Normalising by my
own string would give a metric I could improve by writing more characters;
with the reference there is no such loophole. It also produces the property
that alarms people on first contact: CER IS NOT CAPPED AT ONE. If the
reference is "ABC" and I wrote "ABCDEFGH", that is five edits over a reference
of three, so CER = 1.667. Not a bug in the arithmetic -- an honest answer:
I wrote more than was there.

WER is the same thing with the word as the unit of edit. On a word-level
dataset such as Total-Text an object holds exactly one word, so WER collapses
into "share of objects transcribed non-identically". It still earns its place:
CER 0.1 can mean "one error in every word" or "one word in ten read entirely
wrong", and WER tells those apart.

MICRO VS MACRO AVERAGING. Corpus CER is the sum of edits divided by the total
reference length (micro), not the mean of per-object CERs (macro). Otherwise a
one-character object with one error weighs as much as a long sign read
perfectly. Both are returned, and the report states which one it quotes.

No dependencies.
"""

import argparse
import unicodedata


def levenshtein(a, b) -> int:
    """Smallest number of edits. Works on a string of characters and on a list
    of words alike -- all that matters is that the elements compare."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1,          # delete
                           cur[j - 1] + 1,       # insert
                           prev[j - 1] + (ca != cb)))  # substitute
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    """CER of a single pair. An empty reference is handled apart: there is
    nothing to divide by, and any non-empty hypothesis is pure invention."""
    if not ref:
        return 0.0 if not hyp else float("inf")
    return levenshtein(ref, hyp) / len(ref)


def wer(ref: str, hyp: str) -> float:
    r, h = ref.split(), hyp.split()
    if not r:
        return 0.0 if not h else float("inf")
    return levenshtein(r, h) / len(r)


def corpus_cer(pairs: list[tuple[str, str]]) -> dict:
    """Micro and macro averaging over pairs of (reference, mine)."""
    edits = sum(levenshtein(r, h) for r, h in pairs)
    chars = sum(len(r) for r, _ in pairs)
    per_pair = [cer(r, h) for r, h in pairs if r]
    return {
        "cer": edits / chars if chars else 0.0,
        "cer_macro": sum(per_pair) / len(per_pair) if per_pair else 0.0,
        "edits": edits,
        "ref_chars": chars,
        "pairs": len(pairs),
        "exact": sum(1 for r, h in pairs if r == h),
    }


def corpus_wer(pairs: list[tuple[str, str]]) -> dict:
    edits = sum(levenshtein(r.split(), h.split()) for r, h in pairs)
    words = sum(len(r.split()) for r, _ in pairs)
    return {"wer": edits / words if words else 0.0,
            "edits": edits, "ref_words": words}


# --- normalisations: each one stands for a single guideline decision -------

def as_is(s: str) -> str:
    return s


def lower(s: str) -> str:
    return s.lower()


def upper(s: str) -> str:
    return s.upper()


def no_punct(s: str) -> str:
    """Drop everything that is neither a letter nor a digit."""
    return "".join(c for c in s if c.isalnum())


def no_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def lower_no_punct(s: str) -> str:
    return no_punct(s.lower())


NORMALIZERS = {
    "as_is": ("transcribe the way the reference does", as_is),
    "lower": ("force everything to lowercase", lower),
    "upper": ("force everything to UPPERCASE", upper),
    "no_punct": ("drop punctuation", no_punct),
    "lower_no_punct": ("lowercase, punctuation dropped", lower_no_punct),
}


# --- control cases ---------------------------------------------------------

CASES = [
    ("identical to the reference", "PARKING", "PARKING", 0.0),
    ("one letter wrong", "PARKING", "PARKINH", 1 / 7),
    ("read correctly, written lowercase", "PARKING", "parking", 1.0),
    ("wrote more than was there", "ABC", "ABCDEFGH", 5 / 3),
    ("not transcribed at all", "PARKING", "", 1.0),
]


def _selftest() -> int:
    print("| case | reference | mine | CER | WER |")
    print("|---|---|---|---|---|")
    ok = True
    for name, ref, hyp, expect in CASES:
        got = cer(ref, hyp)
        print(f"| {name} | `{ref}` | `{hyp or '--'}` | {got:.4f} | {wer(ref, hyp):.4f} |")
        if abs(got - expect) > 1e-9:
            print(f"  FAILED: expected {expect:.4f}")
            ok = False

    print()
    print("The third case is worth rereading: every letter was read correctly,")
    print("and CER is exactly 1.000 -- the same as if the word had never been read.")
    print("To the metric, case is not cosmetic detail. It is seven edits out of seven.")
    print()
    print("The fourth: CER above one is not a failure, it is the reference sitting")
    print("in the denominator.")
    print()

    # micro against macro on three objects
    pairs = [("EXIT", "EXIT"), ("A", "B"), ("RESTAURANT", "RESTAURANT")]
    m = corpus_cer(pairs)
    print("| a set of three objects | value |")
    print("|---|---|")
    print(f"| edits in total | {m['edits']} |")
    print(f"| reference characters | {m['ref_chars']} |")
    print(f"| CER micro (edits / all characters) | {m['cer']:.4f} |")
    print(f"| CER macro (mean over objects) | {m['cer_macro']:.4f} |")
    if abs(m["cer"] - 1 / 15) > 1e-9 or abs(m["cer_macro"] - 1 / 3) > 1e-9:
        print("  FAILED: micro should be 1/15, macro 1/3")
        ok = False
    print()
    print("One error, and it sits in the one-character object: micro gives 0.0667,")
    print("macro 0.3333. A factor of five out of nothing, which is why a report")
    print("says which of the two it quotes.")
    print()
    print("all control cases match" if ok else "there are discrepancies")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
