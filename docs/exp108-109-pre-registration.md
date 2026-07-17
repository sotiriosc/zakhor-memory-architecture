# exp108/109 — Pre-Registration: The Loss Scale and the Warning

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4). Ported into
this repository verbatim; independently reproduced in-repo (see
`research/results/exp108_2026-07-12_inrepo.txt` and
`research/results/exp109_2026-07-12_inrepo.txt`).

## exp108 — Keeper-controlled dynamic loss scaling

Manual numpy MLP (digits, 64-32, softmax CE, SGD lr=0.05, batch 32, 3000
steps, fixed seed). Simulated FP16 gradient path: g_q = fp16(g x S)/S with
FP16 overflow at 65504 (overflow => step skipped, both controllers) and
flush-to-zero below 2^-24. Master weights FP64.

Controllers of the global loss scale S:
- HEURISTIC (industry): S doubles every 500 non-overflow steps; on
  overflow, halve S and skip.
- KEEPER: track log2(max|g|) per step via leaky integrator (alpha=1/16,
  causal), guard/target: S = 2^(14 - state) (headroom to 2^14 of FP16
  range). Stranger rule: step-max beyond state + G (G from p99 of first
  128 steps, min 1) => skip the step but DO NOT move S and DO NOT update
  state. K=3 consecutive out-of-bound steps => regime rebirth (state <-
  obs, S recomputed). No periodic doubling, no halving.

Streams: CLEAN (no injection) and SPIKED (every 100th step, gradients
x 2^8 — transient fault).

Frozen predictions:
- P26: on SPIKED, KEEPER skips <= 1/3 as many steps as HEURISTIC.
- P27: on SPIKED, KEEPER final test accuracy >= HEURISTIC - 0.3%, AND
  KEEPER's mean flushed-gradient fraction < HEURISTIC's (the halving
  aftermath is where small gradients die).
- P28: on CLEAN, |KEEPER - HEURISTIC| final accuracy <= 0.5% (no harm).

## exp109 — The persistent-outlier warning (testing against ourselves)

exp105 machinery (N=8 E3M6, digits MLP inference, keeper-gated exponent
selection). New stream PERSISTENT: 4 fixed activation channels per hidden
layer scaled x 2^7 on EVERY sample (SmoothQuant-shaped structure), vs the
established transient DENSE stream (elements x phi^10 at p=1/64).

Frozen prediction, siding with the external warning:
- P29: on PERSISTENT, KEEPER - LOCALMAX <= +1.0% (the advantage
  vanishes: the tracked state learns the hot channels, the ceiling rises
  to cover them, no strangers fire, and hot blocks quantize
  LOCALMAX-equivalently — the keeper converges to what per-channel
  methods already handle). On DENSE (rerun, same seed), the gap remains
  > +20%. If P29 passes, the product thesis is sharpened as the external
  analysis stated: this is a fault-tolerance play, not a general
  quantization play, and that conclusion is recorded in Note 03.

Riders: double-run hashes; keeper audits reported. Verdicts PASS /
FALSIFIED / METRIC-DEFECT. Falsified stays falsified — in either
direction, including if the warning itself is what falls.
