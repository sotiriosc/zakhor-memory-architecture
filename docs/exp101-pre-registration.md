# exp101 — Pre-Registration: Contact — Real Workload vs Delayed Scaling

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4) from
Architecture Note 02 §3 alone — no zakhor source code was transferred, only
the design-rule table. Ported into this repository verbatim; independently
reproduced in-repo (see `research/results/exp101_2026-07-12.txt` for the
in-repo reproduction hash alongside the original). This is a **new series**
(exp101–104, "Contact"). The exp00x series (exp001–exp007b) is CLOSED
(Architecture Note 02); nothing in this document reopens it.

New series (the exp00x series is closed; none of its verdicts are touched).

## Question
On a real trained workload, does the zakhor scale controller beat the
industry-standard mechanism (delayed scaling: rolling amax-history window,
as used for FP8 training) — and where does it lose?

## Workload
sklearn digits (real data), MLP (hidden 64-32) trained in FP64, fixed seed.
Manual FP64 forward pass on the test split with per-layer ACTIVATION
quantization only (weights stay FP64 — isolates the scale-controller
question). φ-codebook, 16 shells, per-layer scale state. Block = one
sample's activation vector per layer.

## Competitors (independent reimplementation from Note 02 §3 only)
- ZAKHOR-G3: log-φ leaky integrator α=1/64, causal pre-update read,
  calibration window 128 blocks, G = ceil(p99(d+)) min 1, D = G+1 min 2,
  K = 3 (rebirth / persistence / infancy), stranger gating (zero state
  contribution), signed regime log, noise = p95(|delta|).
- DELAYED: amax history window W = 16 blocks per layer, hi = max(window).
- STATIC: hi frozen from calibration window max.
- ORACLE: per-block max (descriptive only).
- FP64 reference: unquantized accuracy ceiling.

## Streams (test split, natural order, fixed seed)
- CLEAN: as-is.
- SPIKE: every 100th sample's input × φ^10 (corrupted frames). Accuracy
  measured on normal samples; spiked samples reported separately.
- REGIME-DOWN: from sample 900 on, inputs × φ^-8 (gain drop).
- REGIME-UP: from sample 900 on, inputs × φ^+8 (gain jump).

## Frozen predictions (directional, falsifiable)
- P1 CLEAN: all controllers within 0.5% top-1 of FP64.
- P2 SPIKE: ZAKHOR normal-sample top-1 ≥ DELAYED. Mechanism on record:
  each spike poisons DELAYED's window max for W = 16 blocks (~16% of the
  stream degraded); ZAKHOR gates the spike out of state entirely.
- P3 REGIME-DOWN: ZAKHOR post-step top-1 ≥ DELAYED. Mechanism: window max
  lingers W blocks high; ZAKHOR rebirths in ~K.
- P4 REGIME-UP (the honest one, against ourselves): DELAYED ≥ ZAKHOR.
  Mechanism: a new max enters the window in 1 block; ZAKHOR needs K.
  Prediction of near-tie (rebirth at K = 3 vs window at 1).
- P5 Note-sufficiency: the §3 table alone suffices to reproduce the
  documented behaviors (zero hallucinated regimes on CLEAN; gating
  displacement ≡ 0 on SPIKE; one signed rebirth per regime stream).

Reproducibility: fixed seeds, double run, identical results hash required.
Verdicts per prediction: PASS / FALSIFIED / METRIC-DEFECT, no fourth
category. Falsified stays falsified.
