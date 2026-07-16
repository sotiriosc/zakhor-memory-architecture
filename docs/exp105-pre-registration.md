# exp105 — Pre-Registration: The Neighbors — Keeper-Gated Exponent Selection at N=8

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4) from
Architecture Note 03 §5 alone — no zakhor source code was transferred, only
the design-rule table and the Contact series baseline model. Ported into this
repository verbatim; independently reproduced in-repo (see
`research/results/exp105_2026-07-12_inrepo.txt` for the in-repo reproduction
hash alongside the original). This experiment tests the N=8 local-max BFP
(E3M6+block) configuration, distinct from the tracked-scale mode of
exp103/104; those series' numbers remain scoped to their own mode.

## Question
Horus's native compressed mode is E3M6+block: a 6-bit shared exponent per
8-element block, set from the block's OWN local max (per-block oracle
scaling — no window to poison). exp103/104's +12-point result was measured
in a tracked-scale mode and MAY NOT be cited for this configuration. So:
in the mode Horus actually builds, what does the keeper keep?

Hypothesis under test: local-max scaling is oracle-perfect against drift
and MAXIMALLY vulnerable to in-block outliers — a corrupted element IS the
max, inflating its own block's exponent and crushing its 7 honest
neighbors' mantissas toward zero. A keeper carrying a tracked scale can
recognize that element as a stranger, exclude it from the max, tag the
block, and preserve the neighbors.

## Design
exp101 model/seeds/streams reused (digits MLP 64-32, FP64 weights — the
activation-scale question isolated; weights re-tested at m=6 per exp104 if
time permits, reported separately). Activations quantized as E3M6+block:
blocks of N=8 consecutive elements per layer, shared exponent per block,
6-bit mantissa, values below half an LSB underflow, above range clip.

Competitors (per 8-element block):
- LOCALMAX (Horus as-built): E = f(max |v| in block). No keeper.
- KEEPER-GATED: a per-layer tracked scale (leaky integrator, alpha=1/64,
  causal pre-update read, guard band G from p99 of calibration positive
  deviations, K=3 procession rules — the established machinery). Per
  block: any element whose magnitude exceeds the tracked ceiling
  (state + G) is declared a STRANGER, excluded from the block's max
  computation; E is set from the max of the surviving elements; strangers
  are clipped to the block ceiling and the block is tagged. Tracked state
  updates only from non-stranger block maxima.
- ORACLE-CLEAN (diagnostic, not a competitor): E from the max of the
  UNCORRUPTED activations — the unreachable ceiling, showing what the
  neighbors would have gotten had the spike never arrived.

## Streams (the corruption model changes — this is the point)
Element-level corruption, not frame-level. On the corrupted streams, a
fixed fraction p of individual ACTIVATION elements (chosen by seeded RNG,
per layer, per sample) are multiplied by phi^10 (~123x).
- CLEAN: p = 0.
- SPARSE: p = 1/512 (~1 corrupted element per 64 blocks).
- DENSE: p = 1/64 (~1 corrupted element per 8 blocks — most blocks
  clean, but corruption common enough to bite).

## Frozen predictions
- P14 (concentration claim, the headline): on DENSE, KEEPER-GATED top-1
  exceeds LOCALMAX by > 3.0% absolute. Mechanism on record: each
  corrupted element inflates its own block's exponent by ~10 phi-shells
  (~7 octaves), pushing its 7 neighbors below the 6-bit mantissa floor —
  they underflow to zero. The keeper excludes the stranger; the neighbors
  keep their precision.
- P15 (sparse regime): on SPARSE, KEEPER-GATED >= LOCALMAX − 0.5%
  (i.e., no harm when corruption is rare; the advantage may be small).
- P16 (no honesty tax): on CLEAN, |KEEPER-GATED − LOCALMAX| <= 1.0%
  absolute.
- P17 (the audit): on DENSE, stranger-declaration count is within
  1.05x of the true corrupted-element count per layer, and zero
  strangers are declared on CLEAN beyond the calibration-tail rate
  (reported).
- P18 (ceiling proximity): on DENSE, KEEPER-GATED top-1 is within 1.0%
  of ORACLE-CLEAN — i.e., excluding the stranger nearly restores what
  the neighbors would have had.

Riders: tracked-state displacement from stranger-only blocks ≡ 0; zero
regime events on CLEAN.

Reproducibility: fixed seeds, double run, identical results hash.
Verdicts PASS / FALSIFIED / METRIC-DEFECT, no fourth category. Falsified
stays falsified. This experiment does not touch any prior verdict; it
tests a NEW configuration, and the exp103/104 numbers remain scoped to
tracked-scale mode regardless of the outcome here.
