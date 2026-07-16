# exp003 — Pre-Registration: Identity, Recovery, and the Declared Stranger

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-11

This document is written before any exp003 code exists. Its hypotheses,
metrics, and pass/fail thresholds may not be altered after the experiment
runs. If a metric proves ill-posed in execution, the experiment records the
failure of the metric and defers — it does not quietly substitute a better
one. This is the shamor discipline: the test is kept so the test can say no.

Provenance: exp002 (research/results/exp002_2026-07-11.txt) falsified H0 in
aggregate-MSE form, confirmed the shell automorphism (0.91 vs 0.22 shell
consistency at 1-shell drift), identified the H2 recovery metric as
unreachable by construction for step-UP, and found S4's pass criterion
rewarded silence (99.99% underflow scoring as low MSE). exp003 exists to
test the corrected claims. All exp002 verdicts stand as recorded.

---

## Carried-over machinery (unchanged from exp002)

Mechanism, alpha = 1/64 primary, cold-start rule, causal pre-update read,
log-φ domain, competitors PHI-ZAKHOR / PHI-STATIC / GRID-ZAKHOR /
GRID-STATIC / ORACLE-PHI, matched codebook budgets, fixed logged seeds,
bit-identical reproducibility assertion. Peaked (std 0.15) and spread
(std 0.30) distributions both run, both reported.

New sixth competitor, defined in §4:
    PHI-ZAKHOR-KEEP — PHI-ZAKHOR plus the declare-loss branch.

## §1 — H0 restated at the identity layer (H0-id)

exp002 established that the leaky integrator reduces aggregate MSE almost
equally on φ and grid geometry. The surviving claim is about identity, not
error:

> **H0-id.** Under scale drift, the φ-codebook preserves the *identity* of
> carried values — which counterpart they descend from — at a rate that
> makes the return operation feasible; the uniform grid does not.

Operationalization (all frozen):

- **Shell consistency** at whole-shell drifts m ∈ {1, 2, 4}: fraction of
  values whose shell index moves by exactly m.
  PASS threshold: φ ≥ 0.85 at m=1 and ≥ 0.75 at m=4; grid reported as
  baseline with no threshold (its lack of the property is the point, but it
  gets measured, not assumed).
- **Return feasibility**: fraction of drifted values whose phase deviation
  lies within the safe radius (half the smallest three-distance gap for the
  active prefix), i.e. provably re-seatable per KEEP.md §4.
  PASS threshold: φ ≥ 0.80 under the S2 slow ramp; grid reported.
- **Return correctness** (the theorem's empirical shadow): among values the
  test re-seats, fraction restored to their true (ground-truth) counterpart.
  PASS threshold: ≥ 0.99 within the safe radius. A single systematic
  violation within the radius falsifies the safe-radius derivation itself
  and blocks the return theorem — record loudly if so.

H0-id is FALSIFIED if φ fails any threshold, or if grid matches φ within
0.05 on all three (the property would then not be φ-specific).

## §2 — H2 revised: oracle-relative recovery

Absolute-MSE recovery is unreachable by construction when the post-step
signal is larger; exp002 recorded this as a metric defect. Frozen
replacement:

    R(t) = MSE_competitor(block t) / MSE_ORACLE-PHI(block t)

ORACLE-PHI experiences the same post-step signal, so R normalizes signal
magnitude out. Pre-step baseline R̄ computed over the 256 blocks before the
step.

> **H2-r.** After a step of φ^±8, PHI-ZAKHOR's R(t) returns to within 2× of
> R̄ in ≤ 2/alpha = 128 blocks (step-UP), and in ≤ 8 blocks (step-DOWN,
> predicted ~0 from exp002's depth-absorption finding).

FALSIFIED if recovery exceeds the block budget on either direction, on
either distribution.

**Asymmetry documentation (descriptive, no threshold):** record the
step-DOWN vs step-UP recovery asymmetry explicitly. Prediction on record:
downward drift is absorbed by shell depth (constant relative precision);
only upward drift needs the living scale. This goes in Note 01 either way.

## §3 — S4 decomposed: three questions the old S4 conflated

> **S4a — State integrity.** Does one spike overthrow the memory?
> Prediction on record: per-spike state displacement ≈ alpha × Δshell =
> (1/64) × 10 ≈ 0.156 shells, decaying with horizon ~64 blocks.
> PASS: measured peak displacement ≤ 0.25 shells and return to within
> 0.02 shells of pre-spike state before the next spike (spacing 256).

> **S4b — Spike fidelity.** How is the spike value itself represented?
> Measured, not thresholded, for PHI-ZAKHOR (known to overflow by design);
> thresholded only for PHI-ZAKHOR-KEEP via §4.

> **S4c — Collateral damage.** MSE on the *normal* blocks only (spike blocks
> excluded), oracle-relative per §2.
> PASS: PHI-ZAKHOR's normal-block R within 1.2× of its S1 stationary R.
> This is what the original S4 was actually asking.

The exp002 S4 verdict ("both competitors fail for opposite reasons")
stands; S4a–c replace, not reinterpret, that test.

## §4 — The declared stranger (KEEP.md §4 at the value layer)

New competitor behavior PHI-ZAKHOR-KEEP: identical to PHI-ZAKHOR except
that any incoming value whose magnitude falls beyond the outermost shell of
the current codebook (equivalently: whose shell coordinate deviation from
the representable range exceeds the safe radius) is **declared a stranger**:

- it is NOT quantized into the codebook (no silent garbage),
- it is NOT integrated into the scale state beyond the normal alpha step
  (the memory is not overthrown),
- it IS logged: block index, observed shell coordinate, deviation.

Frozen honesty metrics, reported for every competitor:

- **Declared-loss rate**: fraction of values flagged as strangers.
- **Silent-error rate**: fraction of values whose reconstruction error
  exceeds 10× the oracle's for that value, WITHOUT a declaration.

> **H3 (the keeping claim).** On S4, PHI-ZAKHOR-KEEP achieves a silent-error
> rate < 0.1% while declaring ≤ 1.05× the true spike fraction as strangers
> (i.e. it catches the spikes without slandering normal data), and its
> normal-block collateral (S4c) matches plain PHI-ZAKHOR within noise.

FALSIFIED if the declare-loss branch either misses spikes (silent-error
rate ≥ 0.1%) or over-declares (> 1.05× true spike fraction) on either
distribution. Note: PHI-STATIC's exp002 "win" (99.99% underflow, everything
snapped to zero) will register here as a catastrophic silent-error rate —
this is the metric doing its job, and it is pre-registered as expected.

## §5 — Regression gate

S1 stationary re-run for all six competitors. PHI-ZAKHOR-KEEP must tie
PHI-ZAKHOR within noise (declare-loss must cost nothing when nothing is
strange). Any competitor regressing against its exp002 S1 numbers halts the
campaign for review before later sections are interpreted.

## §6 — Deliverables

1. research/exp003_identity_recovery.py — seeded, reproducible.
2. Results: §1 identity table, §2 recovery curves R(t), §3 three-way S4
   decomposition, §4 honesty metrics for all six competitors.
3. Stranger log (the first artifact of the keeping discipline: a memory
   that records what it could not carry).
4. Bit-identical re-run assertion, SHA-256 recorded.
5. Verdict paragraphs against H0-id, H2-r, S4a/c, H3 — each explicitly
   PASS / FALSIFIED / METRIC-DEFECT, no fourth category.

## §7 — Freeze declaration

Thresholds above were fixed on 2026-07-11, before implementation. Any
change after first execution invalidates the affected verdict and requires
a new pre-registration (exp004). Falsified results are preserved in
research/ per project convention.
