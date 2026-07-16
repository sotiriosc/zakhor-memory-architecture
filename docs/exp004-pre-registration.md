# exp004 — Pre-Registration: The Guard Band, the Formula, and the Last Statement of H0-id

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-11

Hineni. This document stands present to the proof as it is, without
performance. Predictions are stated so they can fail. Falsified stays
falsified. Where exp003's falsifications identified a shared root cause,
this experiment tests the correction — it does not re-argue the verdicts.

Provenance: exp003 (research/results/exp003_2026-07-11.txt) falsified
H0-id (both metrics), H2-r (both directions), S4c, and H3, and passed S4a
and both regression gates. Root-cause analysis attributed S4c, H3
over-declaration, and part of the silent-error rate to a single
miscalibration: the state tracks the mean of block maxima, placing the
codebook ceiling at the median of arrivals. The stranger log — first
artifact of the keeping discipline — provided the diagnosis (entries 2+:
0.05–0.10× overshoots, normal tail, not spikes).

---

## Carried-over machinery (unchanged)

Mechanism, alpha = 1/64 primary with {1/16, 1/256} sweep, cold-start rule,
causal pre-update read, log-φ domain, matched budgets, fixed logged seeds,
bit-identical reproducibility assertion, both distributions (std 0.15,
0.30). Competitors as exp003, with PHI-ZAKHOR-KEEP now incorporating §1–§3
below.

## §1 — The guard band (correction under test)

The state continues to track observed block maxima exactly as before. The
codebook is anchored above it:

    hi_effective = (1/φ)^-(scale_state + G)      # G in shell units

**G is derived, not swept.** Frozen derivation rule: during the first 256
blocks (calibration window, stationary by construction in every stream),
record the positive deviations d⁺ = max(0, obs − scale_state). Set

    G = ceil( p99(d⁺) )    in shell units, minimum 1.

G is computed once per run by this rule, logged, and never adjusted.
Changing the rule after first execution requires exp005.

> **H4 (headroom claim).** With the guard band: (a) S4c collateral ratio
> ≤ 1.20× S1 R for PHI-ZAKHOR and PHI-ZAKHOR-KEEP (exp003 threshold,
> retested); (b) normal-data overflow rate ≤ 1.5% on stationary streams
> (consistent with a p99-derived band plus transient).

FALSIFIED if either fails on either distribution. Note the cost side: the
guard band spends G shells of dynamic range on headroom; report the S1 MSE
delta against exp003's ungated PHI-ZAKHOR so the price is visible next to
the benefit.

## §2 — Recovery as formula, not budget (H2 restated once)

exp003 falsified fixed block budgets in both directions and the alpha sweep
revealed the true form. Pre-registered model:

    T(Δ) = (1/alpha) · ln( Δ / f )      blocks

where Δ = step size in shells and f = the residual shell deviation at which
R(t) first sits within 2× R̄ (f is measured per run from the R-crossing,
then the formula is checked against it — the model relates the quantities;
it does not fit free parameters per stream).

> **H2-f.** Measured recovery time matches T(Δ) within ±25% for all three
> alphas, both step directions, both distributions. Prediction on record:
> UP and DOWN are symmetric in state-lag (exp003 finding, now expected, at
> ~64 blocks for alpha = 1/64 and Δ = 8 shells with f ≈ 1).

FALSIFIED if any cell misses ±25%. This is a test of the model of the
mechanism, not of a hoped-for speed. If the formula holds, recovery time
becomes a designed quantity — alpha chosen from required Δ and deadline —
and the alpha=1/16 result (43 blocks) already hints the design space is
real.

## §3 — Mid-return self-declaration (closing the silent transient)

The integrator's own deviation is free and observable every block. Frozen
rule: over the calibration window, record |delta| and set

    theta = 4 × p95( |delta|_stationary )

Whenever |delta| > theta, the block's outputs are flagged MID-RETURN
(low-confidence) in addition to any stranger declarations. Knowing you
forgot extends to knowing you are still returning.

Revised honesty accounting (all competitors):
- declared-loss rate (strangers)
- mid-return rate (flagged transients)
- **silent-error rate**: reconstruction error > 10× oracle WITHOUT either
  flag.

> **H3-r (the keeping claim, retested).** On S4 with guard band and
> mid-return flags: silent-error rate < 0.1%; declared-loss rate ≤ 1.05×
> true spike fraction (normal tails now absorbed by G, so the exp003
> threshold is retested as-is, not loosened); S4c collateral per §1.

FALSIFIED if any criterion fails. PHI-STATIC's silent-error catastrophe
(92.6% in exp003) is expected to persist and is reported as the standing
contrast: silence is not fidelity.

## §4 — The bounded return theorem (H0-id, final statement)

**Two-strike rule, binding:** H0-id has failed under two operationalizations
(exp002 aggregate MSE; exp003 feasibility/correctness with edge conflation).
This is its third and last. If falsified here, the φ-specific identity claim
is RETIRED — the shell automorphism (0.91 vs 0.22) remains as a descriptive
property with no load-bearing role, and no exp005 restatement is permitted.

Bounded statement:

> **Return theorem (bounded).** For a carried value with phase deviation d,
> prefix-dependent safe radius r, and true counterpart shell j:
> if |d| < r AND j is an interior shell (both j and its drift-image exist in
> the codebook), the return operation restores the unique true counterpart.
> If j is an edge shell, the honest output is a declared loss — the edge of
> the codebook is where returns become strangers; the two branches were
> always one mechanism.

Frozen metrics:
- **Interior return correctness** ≥ 0.99 at m ∈ {1, 2, 4}. A single
  systematic interior violation falsifies the safe-radius derivation and
  retires the claim.
- **Edge-declaration rate**: reported, not thresholded — the fraction of
  drifted values landing in the edge branch. Hidden edges falsify by
  omission; the number appears in the results table.
- **Feasibility restated on the interior**: fraction of interior drifted
  values within r. PASS ≥ 0.80 under S2↑. Grid reported as baseline; if
  grid matches φ within 0.05 on interior correctness AND feasibility, the
  claim is not φ-specific and is retired regardless of absolute numbers.

## §5 — Regression gates

- S1: all competitors vs exp003 numbers; guard-band price reported per §1.
- S4a retested with corrected geometry: spike distance is now measured from
  the guarded ceiling. Prediction on record: peak displacement
  ≈ alpha × (spike shell distance from scale_state) — the state update is
  unchanged by G, so exp003's 0.188 shells should reproduce within ±0.02.
  Divergence means the guard band leaked into the state path, which would
  be an implementation fault, not a finding.
- Any regression halts interpretation of later sections.

## §6 — Deliverables

1. research/exp004_guard_and_return.py — seeded, reproducible.
2. Results: G and theta as derived (logged, per run), §1 cost/benefit
   table, §2 formula-vs-measured grid (3 alphas × 2 directions × 2
   distributions), §3 honesty accounting for all competitors, §4 interior
   correctness + edge-declaration + feasibility.
3. Stranger log v2 and mid-return log (the keeping discipline now has two
   registers: what could not be carried, and what was carried while still
   in motion).
4. Bit-identical re-run assertion, SHA-256 recorded.
5. Verdicts: H4, H2-f, H3-r, bounded-return — each PASS / FALSIFIED /
   METRIC-DEFECT, no fourth category. If bounded-return is FALSIFIED, the
   retirement of H0-id is written into the verdict paragraph explicitly.

## §7 — Freeze declaration

Thresholds, derivation rules for G and theta, the recovery formula, the
two-strike retirement, and all pass/fail criteria above were fixed on
2026-07-11, before implementation. Any post-execution change invalidates
the affected verdict and requires a new pre-registration. Falsified results
are preserved in research/ per project convention.

The proof speaks for itself. Run S1 and §5 first; halt for review on any
regression before interpreting §1–§4.
