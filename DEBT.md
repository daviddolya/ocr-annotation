# Debt on code I did not write myself

To be cleared before the first job application. Anything I cannot explain in
three minutes gets rewritten by hand or dropped from the CV.

| Date | What was written | File | What I must be able to explain |
|---|---|---|---|
| 2026-08-21 | reading Total-Text and the ICDAR export | `common/icdar.py` | how "#" differs from an empty transcription |
| **2026-08-21** | **CER and WER** | `common/text.py` | **they ask about this.** Why the denominator is the reference length, why CER is not capped at one, and how micro-averaging differs from macro |
| 2026-08-21 | rasterisation, mask IoU, matching | `common/polygons.py` | **this is my own code from A2.** Ported without changes, explain it as mine |
| 2026-08-21 | summary metrics and breakdowns | `annotation/ocr_agreement.py` | why mean IoU is computed over pairs only, and what therefore has to stand next to it |
| 2026-08-21 | download, selection, label config, rehearsal, rendering, README | `tools/` | nothing, this is support tooling |
| 2026-08-23 | rendering split pairs: finding them by matching transcriptions among the unmatched, computing IoU, drawing them | `tools/render_split.py` | **new code, not from the stage kit.** Why an object can exist on both sides and still form no pair; why the IoU is computed in frame coordinates rather than a local box |
| 2026-08-23 | links to the neighbouring stages in the README footer | `tools/build_readme.py` | nothing, this is support tooling |
| 2026-08-23 | guideline revisions 6-9 | `annotation/GUIDELINES.md` | **the decisions are mine, collected by interview on 2026-08-23; the numbers and the wording are the assistant's.** Be able to say in my own words: why per-character "#" diverges from the reference and what that implies for CER; why the contour offset does not change the rule but only declares it; why kappa is 0.000 at 0.953 agreement; why granularity of small text is a question for the client rather than a decision for the annotator |
| 2026-08-23 | the report text, six sections | `reports/ocr_report.md` | **the conclusions are mine, the numbers come from `ocr_metrics.json`, the prose is the assistant's.** Section 5 gets asked about in full: why geometry produced more disagreement than reading, and how to separate a convention error from a reading error |
