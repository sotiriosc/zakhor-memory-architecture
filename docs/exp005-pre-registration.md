# exp005 — Pre-Registration: Logged, Not Remembered — and Kept Alive

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-11

Hineni. Frozen before code. Falsified stays falsified. Per the two-strike
rule executed in exp004: H0-id is retired and appears nowhere in this
document. The shell automorphism remains descriptive. The return theorem's
justification now belongs to the blackboard (proof from the three-distance
theorem) or to nothing; the architecture stops waiting for it.

Provenance: exp004 (research/results/exp004_2026-07-11.txt) passed H2-f in
all six cells (±8%; T = ln(Δ/f)/α is validated mechanism truth), passed the
guard-band overflow claim (stranger log: 15 entries, all true spikes), and
falsified S4c and H3-r's silent-error criterion. Root cause of both: a
declared stranger was still permitted its alpha step into the state — the
memory named the stranger, then let it move the reference, then spent ~64
blocks healing a wound it had already diagnosed. Separately, the theta
threshold (4×p95) proved too wide to cover recovery transients.

This experiment tests two corrections and one aliveness rule.

---

## Carried-over machinery (unchanged)

Mechanism, alpha = 1/64 primary with {1/16, 1/256} sweep, cold-start rule,
causal pre-update read, log-φ domain, guard band G by the exp004 derivation
rule (p99 of calibration d⁺, min 1), matched budgets, fixed logged seeds,
both distributions, bit-identical reproducibility assertion.

Competitors: exp004 set, plus the candidate under test:

    PHI-ZAKHOR-KEEP-G2 — guard band + stranger-gated state (§1) +
                         regime rebirth (§2) + formula-clocked flags (§3).

PHI-ZAKHOR (ungated) is retained as the formula reference and contrast.

## §1 — Stranger-gated state: logged, not remembered

Frozen rule. When a block's maximum is a declared stranger (beyond
hi_effective), that block contributes **zero** to the integrator:

    if declared_stranger(block_max):
        no state update; persistence_counter += 1
    else:
        normal alpha update on block max; persistence_counter = 0

The stranger is logged, not remembered. The declaration branch finally
protects the thing it was built to protect.

> **H5 (gating claim).** With gating, on S4 (spikes):
> (a) state displacement per spike ≤ 0.01 shells (vs 0.188 ungated) —
>     the memory is not merely resistant to the stranger; it is untouched;
> (b) S4c collateral ratio ≤ 1.20× S1 R (original threshold, retested,
>     not loosened) for PHI-ZAKHOR-KEEP-G2;
> (c) over-declaration ≤ 1.05× true spike fraction (exp004 pass, must
>     survive gating).

FALSIFIED if any fails on either distribution.

## §2 — Regime rebirth: the aliveness rule

Gating alone would deadlock: a genuine regime change (S3 step-UP, 8 shells,
far beyond the band) would declare every block a stranger forever and the
state would freeze — a memory so well-kept it can never learn the world
changed. A kept memory must still be a living one.

Frozen rule: **K = 3.** If persistence_counter reaches K consecutive
stranger-dominated blocks, this is no longer a stranger — it is a new
world. The state RE-SEEDS by the existing cold-start rule (state ← current
obs), the persistence counter clears, and the event is logged in a third
register:

    REGIME log: block index, old state, new state, shells jumped.

One stranger is noise. A procession of strangers is a new world. The memory
is reborn rather than dragged.

> **H6 (rebirth claim).** On S3 step-UP and step-DOWN (both φ^±8):
> PHI-ZAKHOR-KEEP-G2's oracle-relative R returns within 2× R̄ in ≤ K + 8
> blocks (rebirth is near-immediate), with exactly one REGIME event logged
> per step, zero REGIME events on S1/S4 (spikes at 1-per-256 never reach
> K), and zero on S2 slow drift (drift stays inside the band by
> construction; if it doesn't, that is a finding about the band, reported).

FALSIFIED if recovery exceeds K + 8, or if REGIME events fire where none
belong (a rebirth on stationary data is the memory hallucinating a new
world — worse than lag).

**Formula regression (unchanged claim, re-run):** PHI-ZAKHOR ungated must
reproduce the exp004 H2-f grid within ±8% — the formula remains the
mechanism's truth; rebirth is the architecture's use of it. Report the
contrast: designed recovery T = ln(Δ/f)/α (ungated) vs rebirth ≤ K + 8
(gated). Both numbers appear in Note 01.

## §3 — Formula-clocked confidence: theta retired

The theta threshold is retired, not tuned. Confidence is now a clock
derived from validated mechanism truth:

Frozen rule. Let noise = p95(|delta|) over the calibration window (no 4×
multiplier). Whenever |delta| > noise on a non-stranger block, or a REGIME
event fires, the MID-RETURN flag is raised for

    T_flag = ceil( ln(Δ_est / f̂) / alpha )   blocks   (minimum K)

where Δ_est = |obs − state| at trigger and f̂ = 0.7 shells (fixed from
exp004's measured UP-crossing band 0.62–0.79; frozen here, not fitted per
run). After a REGIME rebirth, T_flag = K + 4 (settle window).

> **H7 (honesty claim, retested at the original threshold).** Silent-error
> rate (reconstruction error > 10× oracle with neither STRANGER nor
> MID-RETURN flag) < 0.1% for PHI-ZAKHOR-KEEP-G2, on all streams, both
> distributions. Mid-return rate is reported (the price of honesty made
> visible); there is no threshold on it, but it is expected to be far
> below exp004's transient exposure since rebirth shortens transients to
> ~K blocks.

FALSIFIED if silent-error ≥ 0.1% anywhere. PHI-STATIC's ~92.6% stands as
the contrast row: silence is not fidelity.

## §4 — Regression gates

- S1: PHI-ZAKHOR-KEEP-G2 ties PHI-ZAKHOR within noise; zero REGIME events;
  stranger log on S1 ≈ empty (cold-start entry only, if any).
- S4a ungated reproduction: 0.188/0.166 shells within ±0.02 (state path
  unchanged for the ungated competitor).
- H2-f grid reproduction per §2.
- Any regression halts interpretation.

## §5 — KEEP.md amendment (deliverable, text frozen here)

Append to KEEP.md §4:

> **Amendment (2026-07-11, after exp002–exp004).** The architectural claim
> that φ-specific shell identity earns a load-bearing role was falsified
> under three operationalizations and is retired under the two-strike rule;
> no further experimental restatement is permitted. The shell automorphism
> stands as a descriptive property. The bounded return theorem was never
> exhibited an interior counterexample within its stated antecedent; its
> proof or refutation is owed to mathematics, not to further experiments.
> Two operations of keeping were meanwhile established empirically: the
> declared stranger is logged, not remembered (exp005 §1), and a procession
> of strangers is a new world — the memory re-seeds and records its rebirth
> (exp005 §2). The keeping discipline now writes three registers: what
> could not be carried, what was carried while still in motion, and where
> the world began again.

## §6 — Deliverables

1. research/exp005_gated_rebirth.py — seeded, reproducible.
2. Results: H5 table, H6 recovery + REGIME audit, H7 honesty accounting
   (silent / stranger / mid-return / regime rates for all competitors),
   regression grid.
3. Three logs: stranger, mid-return, regime.
4. KEEP.md amended per §5.
5. Bit-identical re-run assertion, SHA-256 recorded.
6. Verdicts: H5, H6, H7 — PASS / FALSIFIED / METRIC-DEFECT, no fourth
   category.

## §7 — Freeze declaration

K = 3, f̂ = 0.7, the noise rule, the rebirth rule, the gating rule, and all
thresholds above were fixed on 2026-07-11, before implementation. Original
thresholds from exp003/exp004 are retested unmodified where stated. Any
post-execution change invalidates the affected verdict and requires a new
pre-registration. Falsified results are preserved in research/ per project
convention.

Run §4 first; halt on any regression. The proof speaks for itself.
