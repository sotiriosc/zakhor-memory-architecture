# exp006 — Pre-Registration: The Symmetric Gate — Excess, Absence, and the Guarded Oracle

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-11

Hineni. Frozen before code. Falsified stays falsified. H0-id remains
retired and appears nowhere here.

Provenance: exp005 (research/results/exp005_2026-07-11.txt) established
three foundations — state displacement under gating identically zero;
regime rebirth for step-UP at 0 blocks vs 156 ungated; the recovery formula
T = ln(Δ/f)/α confirmed a third time — and falsified H5b, H5c (peaked),
H6-dn, and H7. Root-cause analysis found: (1) H6-dn and H5b are one dual —
the stranger-persistence gate perceives excess but is blind to absence, so
a quieter world (step-DOWN) and a too-loud birth (cold-start spike) both
fall through to slow integration; (2) H5c-peaked was made unreachable by an
internal contradiction in the exp005 freeze itself — G derived at p99
guarantees ~1% natural exceedance while the threshold demanded ≤ 5% of the
spike count; the contradiction was the spec author's (Claude), and this
line is its record; (3) H7's 10× raw-oracle criterion is structurally
unreachable for any guarded competitor at steady state, independent of
behavior. exp005's H7 verdict classification (FALSIFIED vs METRIC-DEFECT)
is the steward's call under the pre-registered categories and is recorded
in the exp005 results file; exp006 proceeds identically under either.

This experiment tests one symmetric correction and two consistent
restatements.

---

## Carried-over machinery (unchanged)

Mechanism, alpha = 1/64 primary with {1/16, 1/256} sweep, causal pre-update
read, log-φ domain, guard band G by the exp004 rule, gating (declared
stranger contributes zero to the integrator — logged, not remembered),
K = 3, formula-clocked MID-RETURN flags with f̂ = 0.7, three registers,
matched budgets, fixed logged seeds, both distributions, bit-identical
reproducibility assertion.

Candidate: PHI-ZAKHOR-KEEP-G3 — as G2, with §1 replacing
stranger-persistence as the rebirth trigger. PHI-ZAKHOR (ungated) retained
as formula reference; PHI-STATIC retained as the silence contrast;
ORACLE-PHI retained descriptively; ORACLE-PHI-G added per §3.

## §1 — Symmetric regime detection: a procession of silences is also a new world

The gate stops watching for strangers and starts watching the deviation the
integrator already computes — direction-agnostic.

Frozen rule. Every block, before any gating decision, compute the raw
deviation d_raw = obs − scale_state (obs is measurable on stranger blocks
too). Derived bound:

    D = ceil( p99( d⁺_calibration ) ) + 1   shells, minimum 2.

    if |d_raw| > D:  regime_counter += 1
    else:            regime_counter  = 0

    if regime_counter == K:  REBIRTH — state ← obs, counter cleared,
                             REGIME log entry with signed shells jumped.

Stranger gating (§ exp005) still governs the *state update* on non-rebirth
blocks; §1 governs only *rebirth*. One stranger is noise; a procession of
strangers is a new world; a procession of silences is also a new world.
Zakhor's own grammar includes *do not forget* — absence is remembered too.

> **H8 (symmetry claim).**
> (a) Step-DOWN (φ^−8): exactly one REGIME event at step + K; recovery
>     (oracle-relative R within 2× R̄) in ≤ K + 8 blocks. The exp005
>     falsified budget, retested unmodified.
> (b) Step-UP (φ^+8): exp005's result reproduces — one event at step + K,
>     recovery ≤ K + 8.
> (c) Cold-start self-healing: on S4, the spike-seeded state rebirths at
>     block K (deltas ≈ −10 shells > D for K consecutive blocks), with no
>     special infancy logic. Consequence retested: S4c collateral ≤ 1.20×
>     S1 R (the exp003 threshold, third and final attempt — if S4c fails
>     with the cold-start healed, the residual cost is structural and the
>     threshold is retired to a reported number, not attempted again).
> (d) Zero REGIME events on S1, S2 (drift ≈ 0.003 shells/block << D), and
>     among isolated S4 spikes (single blocks, counter resets). A rebirth
>     where no new world exists falsifies (a)–(c) collectively — the
>     hallucination tooth, carried over, still the sharpest.

FALSIFIED per sub-claim, either distribution.

## §2 — Over-declaration restated consistently with its own derivation

Declarations of values beyond the representable range are truthful; the
metric measures calibration consistency, not slander. The threshold must be
consistent with the G rule that generates natural exceedances.

Frozen rule. On the calibration window, measure the empirical exceedance
fraction ê = P̂(d⁺ > G). Predicted natural declarations
N̂ = ê × n_blocks.

> **H9 (calibration-consistency claim).** Declared-loss count ≤
> true_spike_count + 2·N̂ + 3   (both distributions; the +3 is small-count
> slack, frozen). Additionally the stranger log is audited: every
> declaration must correspond to a value genuinely beyond hi_effective
> (truthfulness check — any false declaration falsifies outright).

## §3 — H7 restated against the guarded oracle

New reference: ORACLE-PHI-G — per-block hi = block_max × φ^G, same G as the
candidate. Structural band overhead is thereby normalized out; what remains
is genuine transient and spike error.

> **H10 (honesty claim, original threshold).** Silent-error rate
> (reconstruction error > 10× ORACLE-PHI-G error, with neither STRANGER nor
> MID-RETURN nor REGIME-settle flag) < 0.1% for PHI-ZAKHOR-KEEP-G3, all
> streams, both distributions. Raw-oracle comparison reported
> descriptively beside it, so the band's permanent price stays visible.
> PHI-STATIC's ~92.6% stands as the contrast row.

FALSIFIED if ≥ 0.1% anywhere. If a new structural unreachability is
discovered in the guarded-oracle criterion itself, the verdict is
METRIC-DEFECT with the mechanism shown — the category exists to be earned,
not assumed.

## §4 — Regression gates

- S1: G3 ties PHI-ZAKHOR within noise; zero REGIME events; stranger log
  ≈ empty.
- Displacement under gating: identically zero reproduces (H5a).
- H2-f formula grid: PHI-ZAKHOR within ±8%, all six cells (fourth
  confirmation expected).
- Rebirth-UP: exp005's decisive contrast reproduces under §1's new trigger.
- Any regression halts interpretation.

## §5 — Deliverables

1. research/exp006_symmetric_gate.py — seeded, reproducible.
2. Results: H8 table with REGIME audit (events, blocks, signed shells),
   H9 count + truthfulness audit, H10 accounting against both oracles,
   regression grid.
3. Three registers, now with signed rebirths (the regime log records which
   direction the world moved).
4. Bit-identical re-run assertion, SHA-256 recorded.
5. Verdicts: H8 (a–d), H9, H10 — PASS / FALSIFIED / METRIC-DEFECT, no
   fourth category.

## §6 — Freeze declaration

D's derivation, K = 3, f̂ = 0.7, the +1/minimum-2 rule, the 2·N̂ + 3
criterion, the guarded-oracle definition, and all thresholds above were
fixed on 2026-07-11, before implementation. The S4c threshold is on its
third and final attempt per §1(c); the H10 threshold is the original 0.1%,
unmodified. Any post-execution change invalidates the affected verdict and
requires a new pre-registration. Falsified results are preserved in
research/ per project convention.

Run §4 first; halt on any regression. The proof speaks for itself — in
both directions now.
