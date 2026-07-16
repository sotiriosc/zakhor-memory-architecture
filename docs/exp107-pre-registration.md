# exp107 — Pre-Registration: The Rival, the Range, and the Residue

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4) as a
solidification follow-on to exp105/106. Ported into this repository verbatim;
independently reproduced in-repo (see
`research/results/exp107_2026-07-12_inrepo.txt`).

## Question
Three solidification attacks on exp105's +53.9: (A) can a memoryless
heuristic — TRIMMED, block exponent from the SECOND-largest element —
recover the gap without a keeper? (B) is the gap stable across corruption
seeds? (C) how much of the 9.2% agree-wrong frontier is corruption-
attributable vs the model's own error?

## Design
exp105 machinery unchanged (digits MLP, N=8 E3M6, phi^10 element
corruption, CLEAN/SPARSE/DENSE). New competitor TRIMMED: per block,
E = exp_from_max(second-largest |v|); the largest element clips at that
codebook's top; no state, no flags. Seed sweep: corruption RNG seeds
{1,2,3,4,5} on DENSE for LOCALMAX / TRIMMED / KEEPER. Decomposition at
seed 1: FP64 forward on the corrupted DENSE stream; classify KEEPER-wrong
samples into FP64-also-wrong (model error) vs FP64-right (corruption-
attributable residue).

## Frozen predictions
- P22 (the rival is strong — conceded in advance): TRIMMED beats LOCALMAX
  on DENSE by > 20 points.
- P23 (memory resolves the dilemma): KEEPER − TRIMMED >= −0.3% on EVERY
  stream, and > +0.5% on at least one. Mechanism on record: TRIMMED must
  clip the legitimate maximum of every clean block (chronic tax); KEEPER
  distinguishes legitimate maxima from strangers via the tracked state.
  If TRIMMED matches KEEPER within noise everywhere, the keeper's
  accuracy claim at N=8 is FALSIFIED down to telemetry, and that verdict
  is recorded.
- P24 (stability): across the 5 DENSE corruption seeds, KEEPER − LOCALMAX
  gap mean > 40 points and minimum > 30 points.
- P25 (frontier decomposition, reported with one bound): corruption-
  attributable residue (KEEPER-wrong AND FP64-right on the same corrupted
  stream) <= 6.0% of samples on DENSE; the model-error share is reported
  beside it.

Riders: keeper audit numbers at seed 1 match exp105/106 exactly; double
run, identical hash. Verdicts PASS / FALSIFIED / METRIC-DEFECT. Falsified
stays falsified — especially if it is our own headline that falls.
