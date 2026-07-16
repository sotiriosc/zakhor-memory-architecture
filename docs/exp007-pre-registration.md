# exp007 — Pre-Registration: The Geometric Promise — Closing Experiment

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-11

Hineni. Frozen before code. Falsified stays falsified. H0-id remains
retired. The 10×-oracle metric family is retired per exp006's earned
METRIC-DEFECT (the guarded oracle failed its own criterion at 3.58%); no
oracle-ratio honesty metric appears in this document or any successor.

Provenance: exp006 (research/results/exp006_2026-07-11.txt) passed H8 in
full — symmetric rebirth at 0/2 blocks both directions, cold-start
self-healing at t=K, S4c satisfied at 1.024/1.028 on its final attempt and
retired to a reported number, zero hallucinated worlds — passed H9 with a
clean truthfulness audit, confirmed the recovery formula a fourth time,
and earned METRIC-DEFECT on H10. Two debts remain: the honesty question
still lacks a valid metric, and the mid-return register is suspected of
ghost flags (~1097 flagged blocks over 15 spikes whose measured state
displacement is identically zero — the clock announces returns the gate
already prevented).

This is the closing experiment. §5 states what closes if it passes.

---

## Carried-over machinery (unchanged)

Everything from exp006: candidate PHI-ZAKHOR-KEEP-G3 (symmetric gate,
stranger-gated state, K = 3, D = G + 1 min 2, guard band G by p99 rule,
signed three-register logging), PHI-ZAKHOR ungated as formula reference,
PHI-STATIC as contrast, alpha set with 1/64 primary, both distributions,
fixed seeds, bit-identical reproducibility assertion. ORACLE competitors
are retained descriptively only; no verdict references them.

## §1 — The geometric honesty criterion (oracle-free)

The φ-codebook makes one promise by construction: constant relative
precision. Neighboring shells sit at ratio φ, so a value carried within a
properly-ranged codebook is reconstructible within half its local gap:

    promise(v) = (1 − 1/φ)/2 × |v|  ≈  0.1910 × |v|

Frozen criterion. A value v is **silently mis-carried** iff

    |v − q(v)| > promise(v)
    AND no flag covers its block (STRANGER, MID-RETURN, or REGIME-settle).

Underflow branch (frozen): for values quantized to zero, mis-carried iff
|v| > lo/2 (the value deserved the lowest shell but received silence),
where lo is the smallest nonzero shell of the codebook in use that block.

Properties, stated so they can fail: the criterion is anchored to the
value and the geometry, not to any reference competitor; it is immune to
the block-max alignment artifact by construction; and it measures the
actual promise — did the memory carry this value as well as its geometry
claims it can, and if not, did it say so.

> **H11 (honesty, original threshold, valid metric).** Silent-miscarriage
> rate < 0.1% for PHI-ZAKHOR-KEEP-G3, all streams (S1–S4), both
> distributions. PHI-STATIC reported as the contrast row (prediction on
> record: catastrophic, its underflowed values deserved shells and
> received silence). If the criterion itself proves structurally
> unreachable, METRIC-DEFECT must be earned with the mechanism shown — but
> the prediction on record is that it is reachable, because the promise is
> exactly what nearest-shell quantization delivers whenever the range is
> right, and the flags exist precisely to cover the blocks where it isn't.

## §2 — The ghost-flag fix: the clock starts only when the state moves

exp006's mid-return register fired on spike-block deviations that the
stranger gate prevented from ever entering the state (H5a: displacement
identically zero). The clock announced returns that were not happening.

Frozen rule, replacing the exp005/exp006 trigger:

    MID-RETURN is raised only by:
    (a) a REGIME rebirth — settle window K + 4 blocks (unchanged), or
    (b) a NON-stranger block with |d_raw| > noise (p95 of calibration
        |delta|, no multiplier) — i.e., a deviation the integrator will
        actually absorb — for T_flag = ceil( ln(Δ_est / f̂) / alpha )
        blocks, f̂ = 0.7, minimum K.

    Stranger-gated blocks raise no clock: a zero-displacement stranger
    leaves nothing mis-calibrated to cover. It is already covered by its
    own STRANGER flag for that block.

    After a REGIME rebirth, the mid-return countdown is SET to K + 4
    (not max with any prior formula-clock value): the rebirth resolves the
    state immediately; a pre-rebirth formula clock is a ghost.

> **H12 (ghost-collapse claim).** On S4: mid-return coverage collapses
> from exp006's ~26.8%/14.5% to < 2% of blocks (cold-start settle plus
> genuine naturals), both distributions — while H11 still passes. The
> honesty must survive the honesty-flag diet: if silent miscarriage rises
> above 0.1% when the ghosts are removed, the ghosts were load-bearing
> and the fix is falsified, which would itself be a finding about where
> the real transients live.

## §3 — Full regression suite (fifth confirmations)

All prior establishments re-run, halt on any failure before interpreting
§1–§2:

- S1: G3 ties PHI-ZAKHOR within noise; zero REGIME events.
- H5a: displacement identically zero, printed per spike.
- H2-f formula grid: all six cells within ±8% (fifth confirmation).
- Rebirth both directions: one signed event each at step + K; recovery
  ≤ K + 8 (UP expected 0, DOWN expected ≈ 2).
- Cold-start: one REGIME event at t = K on S4; S4c reported number
  expected ≈ 1.02–1.03 (retired threshold, reported not judged).
- Zero-hallucination audit: no REGIME events on S1, S2, or between
  isolated spikes.
- H9 recheck under exp006's calibration-consistent criterion with
  truthfulness audit.

## §4 — Deliverables

1. research/exp007_geometric_promise.py — seeded, reproducible.
2. Results: H11 accounting (per stream, per distribution, with the
   underflow branch itemized), H12 before/after coverage table, full
   regression grid, three signed registers.
3. Bit-identical re-run assertion, SHA-256 recorded.
4. Verdicts: H11, H12, regressions — PASS / FALSIFIED / METRIC-DEFECT,
   no fourth category.

## §5 — Closing clause and the Note 02 contract

If H11, H12, and all regressions PASS on both distributions, the
experimental series CLOSES. No exp008 is opened for any claim in this
series. The deliverable that follows is not an experiment but the
synthesis — **Architecture Note 02** — whose table of contents is frozen
here so the synthesis cannot quietly curate:

1. **What is established.** The recovery formula T = ln(Δ/f)/α (five
   confirmations, six cells); exact gating (displacement ≡ 0); symmetric
   rebirth (0/2 blocks vs 156/55); cold-start self-healing at t = K;
   calibration-consistent declaration with truthfulness audit; the
   geometric honesty result (exp007); the three signed registers.
2. **The funerals, by name and date.** H0-id — retired 2026-07-11 under
   the two-strike rule after three operationalizations; the shell
   automorphism descriptive only; the return theorem's fate owed to the
   blackboard. The S4c threshold — satisfied then retired on its final
   attempt. The theta threshold — retired for the formula clock. The
   10×-oracle metric family — retired by earned METRIC-DEFECT. Every
   falsified intermediate preserved in research/ with its date.
3. **The design rules the series earned.** alpha from the recovery
   formula given deadline and step size; G = ceil(p99(d⁺)) min 1;
   D = G + 1 min 2; K = 3; f̂ = 0.7; the geometric promise as the
   honesty bound. Each rule cited to the experiment that earned it.
4. **The export at the license boundary.** The recovery formula and the
   symmetric-gate design pattern cross to Horus as DESIGN RULES stated in
   prose, not as code; the proprietary ↔ CERN-OHL-S boundary is resolved
   explicitly before anything else crosses.
5. **Open mathematics.** The bounded return theorem, stated, unproven,
   with its safe radius and interior condition — owed to proof, not to
   experiments.
6. **Provenance.** Steward's decisions throughout; contributions
   attributed per project convention, errors included by name.

If any of H11/H12/regressions FALSIFY: one targeted follow-up freeze is
permitted for the ghost-fix mechanics (§2) only. The geometric criterion
(§1) is not restated — it either measures the promise or the promise
itself is wrong, and either verdict goes in Note 02 as-is.

## §6 — Freeze declaration

The promise constant (1 − 1/φ)/2, the underflow branch, the ghost-fix
trigger, the < 2% collapse bound, the 0.1% threshold, the closing clause,
and the Note 02 table of contents were fixed on 2026-07-11, before
implementation. Any post-execution change invalidates the affected verdict
and requires a new pre-registration. Falsified results are preserved in
research/ per project convention.

Run §3 first; halt on any regression. The proof gets the last word —
this time, possibly the final one.
