# Architecture Note 01 — Scale Memory (Living hi)

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
-->

    10|**Status:** Draft v0.1 · **Author:** Sotirios Chortogiannos · **Date:** 2026-07-11

Architecture Note 00 removed the *positional* anchor — fixed origins and uniform
strides are replaced by φ-proportion. One anchor remains: the outer shell
magnitude `hi` at the top of the φ-codebook. This note specifies the mechanism
for making `hi` a piece of living state and derives the key property that makes
adaptation compose with the φ-codebook geometry rather than merely grafting onto it.

---

## 1. The remaining anchor

    20|The φ-codebook places reconstruction shells at magnitudes `hi · (1/φ)^j`. The
shape of the codebook — the *relative* spacing of shells — is self-similar and
anchorless. But the outer shell magnitude `hi` is a frozen calibration constant
set once (or never updated). This is the **scale anchor**: a surviving assumption
that the distribution of incoming values does not drift after calibration.

Real weight distributions move. Fine-tuning, quantization-aware training, and
layer-wise rescaling all shift the distribution during the life of a model. A
frozen `hi` responds with silent degradation: overflow when the distribution
expands, underflow when it contracts, and MSE that drifts monotonically away
from the oracle ceiling.

## 2. The mechanism: zakhor scale

    30|*Zakhor* (זָכוֹר) means "remember" in Hebrew — remembering as an act, not a
storage retrieval. The zakhor scale is memory in exactly this sense: the history
of observed magnitudes exists only as the accumulated deformation of a single
floating-point state, updated on every block.

**Work in the log domain, base 1/φ**, so shell arithmetic is additive:

```
L(x) = log(x) / log(1/φ)           # shell coordinate of magnitude x
L(x · (1/φ)^k) = L(x) + k         # φ-scaling is additive in L
```

**State:** a single float `scale_state` representing `L(hi)`. On each incoming
block (strictly causal — read before write):

    40|```
obs         = L(max |x| in block)
hi_eff      = (1/φ)^(scale_state)  # pre-update; used for quantization
delta       = obs − scale_state
scale_state = scale_state + alpha × delta
```

Cold start: `scale_state ← obs` of the first block. The mechanism costs one
subtract, one multiply-by-constant (a power-of-two alpha = 1/64 is a right
shift in hardware), and one add per block — three arithmetic operations on a
single scalar. It introduces no new arrays, no new indexing, no new memory.

## 3. Why φ specifically — the automorphism

    50|For a **uniform codebook**, scaling `hi` by any factor relocates every
reconstruction level to unrelated positions. There is no integer relationship
between old and new shell indices. Adaptation is real but generic.

For the **φ-codebook**, scaling `hi` by `(1/φ)^m` (a whole-shell shift) is an
*automorphism of the codebook geometry*:

```
old shell j:  hi · (1/φ)^j
new shell j:  hi · (1/φ)^m · (1/φ)^j  =  hi · (1/φ)^(m+j)
```

Every level maps onto another level — re-indexed by exactly `m`. A value
reconstructed at shell `j` before the drift will be reconstructed at shell
`j − m` after, with no approximation error from the mapping itself. This is

    60|the **scale automorphism**: the zakhor update is geometrically coherent with
the codebook it drives.

**Measurable consequence.** After a drift of `m` shells, re-encoding the same
block against the shifted codebook should move every shell index by exactly
`−m`. Shell-consistency = fraction of values satisfying this exactly; it
approaches 1.0 for the φ-codebook and has no analogous integer structure for
the uniform codebook. See `research/exp002_scale_memory.py`, Section 9.

## 4. Hypotheses

**H0 (composition):** The living scale is worth *more* on φ geometry than on
uniform geometry — not just helpful, but specifically enabled by the

    70|self-similarity. Measured as: (PHI-ZAKHOR advantage over PHI-STATIC) exceeds
(GRID-ZAKHOR advantage over GRID-STATIC) on the slow-drift stream.

**H1 (drift tracking):** PHI-ZAKHOR tracks a φ^12 slow ramp better than
PHI-STATIC on both MSE and under/overflow rates.

**H2 (step cost):** After a sudden φ^8 jump, PHI-ZAKHOR recovers within
`~1/alpha` blocks and post-recovery metrics return to stationary-equivalent.
A living scale that holds well but forgets too slowly is a partial failure;
the damage window must be bounded.

## 5. Honest caveats

    80|- **Peaked distributions only for H0.** The φ-codebook densifies toward zero;
  for spread distributions (std ≳ 0.30) the uniform codebook catches up.
  The exp001 regime boundary applies here too. The zakhor scale mechanism is
  geometry-agnostic; the *composition claim* (H0) is peaked-only unless the
  regime boundary shifts. Spread-regime results are reported, not hidden.
- **Single-block spikes.** With alpha = 1/64, one spike shifts `scale_state`
  by at most `|delta|/64` ≤ the spike amplitude / 64. The state is robust to
  isolated outliers by construction; the S4 stream verifies this.
- **Integer/residue split deferred.** For hardware honesty, `scale_state`
  could be split into an integer shell offset and a fractional residue, making
    90|  the re-indexing explicit in silicon. This is a co-design detail outside the
  scope of the software prototype.

## 6. Experimental results (exp002, 2026-07-11)

Results from `research/results/exp002_2026-07-11.txt`. Primary distribution peaked
(std=0.15); spread (std=0.30) reported separately and consistent unless noted.

**S1 STATIONARY — PASS.** PHI-ZAKHOR at parity with PHI-STATIC (ratio 0.017 peaked,
0.011 spread). No cost from the integrator when the distribution is constant.

**H1 (drift tracking) — PASS.** On S2 slow drift (φ^+12 ramp), PHI-ZAKHOR MSE is
46× lower than PHI-STATIC (4.1e+0 vs 192 peaked; 16 vs 770 spread). The memory
tracks the drift; static calibration degrades completely.

**H0 (φ-composition) — FALSIFIED by aggregate-MSE criterion.** GRID-ZAKHOR's
advantage over GRID-STATIC (98.7%) marginally exceeds PHI-ZAKHOR's advantage over
PHI-STATIC (97.9%) on S2↑. The memory is nearly equally effective on both
geometries by the aggregate metric. The distinction shows in the **shell-consistency
test**: φ automorphism confirmed for 1-shell drift (consistency 0.91 φ vs 0.22
uniform), weakening at 4 shells (0.70) and collapsing at 8 shells (0.00) where the
finite codebook edge clips the outer shells. The structural property holds; the
aggregate MSE does not demonstrate a φ-specific gain. Record H0 as falsified in its
strong MSE form; keep the automorphism finding as a separate geometric result.

**H2 (step cost) — metric requires revision.** After a permanent scale step of φ^8,
absolute MSE never returns to pre-step absolute level because the distribution itself
is now 47× larger. The 2× threshold on absolute pre-step MSE is unreachable by any
finite-levels quantizer after a scale-up. The metric is valid for scale-DOWN steps
(S3↓ recovery: PHI-ZAKHOR 0 blocks, GRID-ZAKHOR 1 block — immediate). For scale-UP,
the correct metric is MSE normalized by the new distribution scale (or ratio to
ORACLE-PHI). That measurement is deferred to a follow-up. The mechanism does adapt
(state visibly tracking the new scale in the alpha sweep), but H2 as specified cannot
be falsified or confirmed for step-up.

**S4 (spike tolerance) — FAIL.** PHI-ZAKHOR MSE (8.6e-1) is 40× higher than
PHI-STATIC (2.2e-2). The mechanism is not protecting against spikes. Root cause:
the causal design (pre-update hi for each block) means the spike block is always
quantized with the *current* hi, which has adapted to the normal-data level (~0.5).
A spike at φ^10 ≈ 123 then overflows catastrophically: it snaps to the outermost
shell at 0.5 with MSE ≈ (123-0.5)^2 ≈ 15 000. One spike block contributes ~234
to block-MSE; 15 such blocks over 4096 total yield mean MSE ≈ 0.86. Ironically,
PHI-STATIC's apparent "good" MSE (2.2e-2) is itself pathological — 99.99% underflow
(everything snaps to 0) because hi is frozen to the first block's spike value (123),
making the entire codebook useless for normal data. Both competitors fail S4 for
different reasons. The S4 pass criterion (PHI-ZAKHOR ≤ PHI-STATIC) rewards freezing
to a pathological hi; the metric should instead compare to ORACLE-PHI. Deferred.

**Alpha sweep.** Faster alpha (1/16) improves S2 MSE and S3 recovery at the cost
of higher spike sensitivity. Slower alpha (1/256) degrades S2 and S3. Primary
alpha 1/64 is a reasonable middle value; the regime boundary for the spike tolerance
trade-off is not yet instrumented.

**Reproducibility — PASS.** Bit-identical re-run confirmed (SHA-256 prefix match).

## 8. Roadmap update

| Stage | Deliverable | Location | Status |
|---|---|---|---|
| 0 | Reference prototype + demo benchmark | `core/phi_theory.py` | done |
| 1 | Regime-boundary sweep (H0 of Note 00) | `research/exp001_regime_sweep.py` | done — boundary at std ≈ 0.28 |
| 2a | Scale memory + automorphism test | `research/exp002_scale_memory.py` | done — H1 PASS, H0 falsified aggregate-MSE form, S4 open |
| 2b | exp003: normalized step-recovery metric; S4 pass criterion vs oracle | `research/` | planned |
| 2c | Multi-dimensional φ-addressing | `core/` | planned |
| 3 | Memory-topology co-design sketch | `docs/` | planned |
| 4 | Agentic handshake protocol between engine modules | `core/` | planned |
