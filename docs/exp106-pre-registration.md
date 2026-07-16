# exp106 — Pre-Registration: Dissonance — The Two Layers Caught Mid-Argument

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4) as a direct
follow-on to exp105. Ported into this repository verbatim; independently
reproduced in-repo (see `research/results/exp106_2026-07-12_inrepo.txt`).

## Question
Run the same inference through two paths — LOCALMAX (fast, per-block,
memoryless) and KEEPER (slow tracked state, exp105 machinery, stateful
across the stream) — and emit ONE BIT per sample: did the two paths'
predictions disagree? Is that bit an integrity signal — i.e., when the
layers argue, is the served answer actually more likely to be wrong?

The served prediction is KEEPER's (the better path per exp105). The flag
costs one comparison. Streams and corruption model identical to exp105
(CLEAN p=0, SPARSE p=1/512, DENSE p=1/64; elements x phi^10; N=8 E3M6
blocks; digits MLP; fixed seeds; double-run hash).

## Frozen predictions
- P19 (informativeness): on SPARSE and on DENSE,
  P(served wrong | disagree) >= 3.0 x P(served wrong | agree).
- P20 (clean floor): CLEAN disagreement rate <= 3.0% of samples
  (inherits exp105's known false-declaration footprint; the cost of the
  bit when nothing is wrong).
- P21 (wrongness coverage, lift form): on DENSE,
  P(disagree | served wrong) >= 2.0 x P(disagree | served right).
- Riders: disagreement rate reported per stream; keeper audit numbers
  (strangers, regime events) must match exp105 exactly (same seeds, same
  machinery — any drift is an implementation fault).

Verdicts PASS / FALSIFIED / METRIC-DEFECT, no fourth category. Falsified
stays falsified. A visualization of the dissonance is produced AFTER the
numbers exist and asserts nothing the table does not.
