# exp103 — Pre-Registration: Horus Water — Zakhor on the BFP Block Exponent

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before code · **Date:** 2026-07-12

**Provenance:** proposed, pre-registered, implemented, and executed by Claude
(Anthropic) in an external sandbox (sklearn 1.8.0, numpy 2.4.4), continuing
the exp101 "Contact" series. Ported into this repository verbatim;
independently reproduced in-repo (see `research/results/exp103_2026-07-12.json`
for the in-repo reproduction hash alongside the original).

## Question
Horus's compressed-block mode (block floating point: one shared binary
exponent per block, m-bit mantissas) collapses per-element range to ~2^m.
Does a zakhor-controlled block exponent protect accuracy against corrupted
frames vs the industry amax-window, at Horus-relevant mantissa widths?

## Design
exp101 machinery (same model/seeds/streams/causal DELAYED/double-run hash),
quantizer replaced by binary BFP: controller supplies hi; shared exponent
E = ceil(log2(hi)); elements quantized as signed m-bit integers x 2^(E-m);
values below half an LSB underflow to zero; values above range clip.
Controllers unchanged (zakhor state still lives in log-phi; only the
codebook changed — the controller is format-agnostic by design and this
tests that too). Mantissa sweep m in {3, 6}: 6 = NFE-13's mantissa width;
3 = aggressive compression. Streams: CLEAN and SPIKE.

## Frozen predictions
- P9 (Horus payoff): at m = 6, ZAKHOR normal-sample top-1 exceeds DELAYED
  by > 5% absolute on SPIKE. Mechanism: 2^6 = 64x range ≈ 9 phi-shells —
  the shallow band where exp102 measured +13.8; window poisoning by x123
  pushes normal data below the BFP floor for W = 16 blocks per spike.
- P10 (deeper compression): at m = 3, same direction, gap > 5%.
- P11 (no honesty tax at Horus width): on CLEAN at m = 6,
  |ZAKHOR − DELAYED| ≤ 1.0% absolute.
- Audit riders at both widths: displacement on strangers ≡ 0; stranger
  count = 17 per hidden layer on SPIKE; zero regime events on CLEAN.

Verdicts PASS / FALSIFIED / METRIC-DEFECT. Falsified stays falsified.
