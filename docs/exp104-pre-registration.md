# exp104 — Pre-Registration: Full Water — Weights and Activations Together

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before code · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4), the final
experiment of the exp101 "Contact" series. Ported into this repository
verbatim; independently reproduced in-repo (see
`research/results/exp104_2026-07-12.json` for the in-repo reproduction hash
alongside the original).

## Question
exp101–103 quantized activations only (the stated gap). Does the zakhor
spike-protection gap survive when WEIGHTS are also quantized — the full
compressed inference pipeline?

## Design
exp103 BFP machinery, m = 6 (NFE-13 mantissa). Weights: quantized once,
per-block BFP (block = 64-element chunks of each weight matrix, shared
exponent = block max — standard practice, identical for every competitor;
weights are static so there is nothing for any controller to track).
Activations: controlled per layer as before (ZAKHOR / DELAYED / ORACLE).
Streams: CLEAN and SPIKE. Double-run hash.

## Frozen predictions
- P12: full-quant CLEAN top-1 within 1.0% of FP64 (0.9700) for all three
  activation controllers (weight quantization at m=6 per-block is cheap).
- P13: the spike gap survives full quantization: ZAKHOR normal-sample
  top-1 exceeds DELAYED by > 5% absolute on SPIKE at m = 6.
- Riders: displacement ≡ 0; 17 strangers per hidden layer on SPIKE;
  zero regime events on CLEAN.

Observation clause: anything unpredicted that emerges is reported as
observed, unforced, without verdict — material for the next freeze, not
this one. Verdicts PASS / FALSIFIED / METRIC-DEFECT. Falsified stays
falsified.
