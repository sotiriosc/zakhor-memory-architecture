# exp102 — Pre-Registration: The Shallow Water Test

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before code change · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4), continuing
the exp101 "Contact" series. Ported into this repository verbatim;
independently reproduced in-repo (see `research/results/exp102_2026-07-12.json`
for the in-repo reproduction hash alongside the original).

## Question
exp101 found zakhor confers no accuracy advantage at 16 shells because the
codebook's ~1364x dynamic range absorbs window poisoning. Does the advantage
appear where range is scarce — shallow codebooks (FP8-class)?

## Design
exp101 machinery unchanged (same model, seeds, streams, causal DELAYED,
double-run hash). Sweep LEVELS in {4, 6, 8, 16}: dynamic ranges of
~4.2x, ~11x, ~29x, ~1364x. Streams: CLEAN and SPIKE only (regime streams
were METRIC-DEFECT on this workload — the network itself is scale-
sensitive). Spike magnitude x phi^10 ≈ 123x: exhausts every depth below
~11 shells of headroom.

## Frozen predictions
- P6 (the payoff claim): at LEVELS in {4, 6}, ZAKHOR normal-sample top-1
  exceeds DELAYED normal-sample top-1 by > 1.0% absolute. Mechanism on
  record: each spike inflates DELAYED's window ceiling x123 for W=16
  blocks; at shallow depth, normal data under that ceiling falls below the
  codebook floor and underflows to zero; ZAKHOR gates the spike out of
  state and its ceiling never moves (displacement ≡ 0, established).
- P7 (no honesty tax): on CLEAN at every depth, |ZAKHOR − DELAYED| ≤ 1.0%
  absolute (the machinery costs nothing when nothing is wrong).
- P8 (dose-response): the ZAKHOR−DELAYED normal-sample gap is
  non-increasing in LEVELS across {4, 6, 8, 16} (allowing ties within
  0.3% noise).
- Audit riders: displacement ≡ 0 at all depths; stranger count ≈ spike
  count at all depths; zero regime events on CLEAN.

Verdicts PASS / FALSIFIED / METRIC-DEFECT. Falsified stays falsified.
