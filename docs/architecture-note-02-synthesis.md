# Architecture Note 02 — Zakhor Scale Memory: The Synthesis

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-12.  See ../NOTICE.
-->

**Status:** Final v1.0 · **Author:** Sotirios Chortogiannos · **Date:** 2026-07-12

This note synthesizes the experimental series exp002–exp007b (all executed
2026-07-11, five days after project inception). Its table of contents was
frozen in the exp007 pre-registration BEFORE the final results existed, so
that the synthesis could not curate its own history. Two additions postdate
that freeze and are marked [post-freeze]: both arise from exp007b, which the
freeze could not have known. Everything else appears exactly where the
frozen outline demanded, including every failure.

The mechanism under study: the zakhor scale — a living block-scale for the
φ-codebook, updated as a leaky integrator of observed work, with stranger
gating, symmetric regime rebirth, guarded headroom, and three signed
registers of keeping. Memory not as storage but as the accumulated
deformation of the scale at which the present is read.

---

## §1 — What is established

Every claim below survived pre-registered falsification attempts and was
reconfirmed by regression in each subsequent experiment. Citations are to
the dated results files in research/results/.

**1. The recovery formula (six confirmations).**

    T = (1/α) · ln(Δ / f)

Recovery time of the leaky-integrator scale after a step of Δ shells, to
residual deviation f. Confirmed across α ∈ {1/16, 1/64, 1/256}, both step
directions, both distributions, with per-cell error as low as 0.1%
(exp004 first derivation ±8%; regressions exp005–exp007b). The UP/DOWN
recovery asymmetry lives entirely in f (≈ 0.62–0.79 UP, ≈ 3.3 DOWN), where
the formula says variation belongs. Recovery is a designed quantity: α is
chosen from the required Δ and deadline. This is the architecture's clock.

**2. Exact gating: the stranger touches nothing.** A declared stranger
contributes zero to the state — logged, not remembered. Measured state
displacement across all analyzed spikes: 0.000000 shells, all_zero = True
(exp005, reproduced through exp007b). Not resistance; untouchedness.

**3. Symmetric regime rebirth.** K = 3 consecutive blocks with |d_raw| > D
(direction-agnostic) declares a new world; the state re-seeds and the event
is logged with signed shells. Step-UP recovery: 0 blocks. Step-DOWN: 2
blocks. Against formula-clocked integration at 156 / 55 blocks (exp006).
One stranger is noise; a procession of strangers is a new world; a
procession of silences is also a new world.

**4. Cold-start self-healing.** The spike-seeded state rebirths at t = K
with no infancy-specific logic — the symmetric criterion reads the
post-spike deviation procession and corrects (exp006). Consequent S4
collateral: 1.024 / 1.028 against the long-sought 1.20 bound, satisfied on
the third and final attempt.

**5. Calibration-consistent declaration.** Declared-loss counts bounded by
true spikes + 2·N̂ + 3 where N̂ is predicted from the same tail statistics
that derive the guard band; truthfulness audited — every declaration
corresponds to a value genuinely beyond the representable range (exp006,
reconfirmed exp007, exp007b). The keeper does not slander.

**6. Zero hallucinated worlds.** Across every stationary, drift, and
isolated-spike configuration in the series: zero REGIME events where no
new world exists (exp006–exp007b). The memory never imagines change.

**7. The watchman's floor and coverage [final form, exp007b].** With the
persistence-gated trigger and the infancy rule: S4 mid-return coverage
0.24% (from 24.5%), S1 false-alarm floor 0.073% — pure infancy, with the
pre-registered independence arithmetic (p^K ≈ 6×10⁻⁶) exact. The infancy
rule itself: below K observations the memory may not vouch — K's third
role, after world-declaration and transient-declaration.

**8. Three signed registers.** What could not be carried (stranger log),
what was carried while still in motion (mid-return log), where the world
began again and in which direction (signed regime log). All audited, all
reproducible bit-identically (every experiment SHA-256-verified across
double runs).

## §2 — The funerals, by name and date

Preserved, not deleted, per project convention. Each with its cause of
death and what survived it.

**H0-id — the φ-specific identity claim.** Retired 2026-07-11 under the
two-strike rule after three operationalizations: aggregate MSE (exp002 —
the leaky integrator proved geometry-agnostic, 98.7% vs 97.9%),
feasibility/correctness with edge conflation (exp003), bounded interior
correctness (exp004, 0.918 < 0.99). Survived by: the shell automorphism as
a DESCRIPTIVE property (φ 0.91–0.918 vs uniform 0.22 shell consistency
under drift, measured consistently in every experiment that looked). No
load-bearing role. No further experimental restatement permitted or taken.

**The theta threshold.** Retired exp005→exp006 in favor of the formula
clock: confidence windows computed from validated mechanism truth, not
from a swept multiplier.

**The S4c threshold (1.20×).** Chased in exp003 (1.52), exp004 (1.67),
satisfied in exp006 (1.024) with the cold-start healed — then retired to
a reported number per its own final-attempt clause. It rests having been
met.

**The 10×-raw-oracle honesty family.** Retired exp006 by earned
METRIC-DEFECT: any oracle anchored to block_max × φ^k exhibits exact-shell
alignment artifacts; the guarded oracle failed its own criterion against
the raw oracle at 3.58%. When the reference cannot pass the test, the test
never measured the mechanism.

**The geometric-promise formula (1−1/φ)/2 × |v|.** Retired exp007 by
earned METRIC-DEFECT: the derivation placed the half-gap relative to the
value where it belongs to the enclosing shell (s_j > v always), so the
criterion demanded more than the geometry promises — the perfect oracle
violated it on 25.3% of values. The derivation error was Claude's, second
of the series, recorded in §6.

**The closing-audit Lift probe.** Caveat, not funeral: the max-relative-
error informativeness probe was blinded by the underflow floor (E_f ≈ E_u
≈ 0.998 everywhere). The audit's decision stood on the sensitivity miss,
which was unambiguous.

**H14 — real-time completeness of the mid-return register.** FALSIFIED
2026-07-11 (exp007b), the series' final verdict. Sensitivity 100% on
cold-start (the infancy rule closed the t=0 miss) but 0/2 on the K−1
blocks preceding a step-DOWN rebirth: the persistence trigger and the
regime rebirth share K, and the rebirth consumes the K-th observation
before the trigger can fire. On step-UP those blocks are covered by
STRANGER flags; on step-DOWN nothing covers them — a quieter world arrives
politely. Measured cost: exactly K−1 = 2 unflagged miscalibrated blocks
per downward regime change. Survived by: the constraint itself, stated as
open mathematics in §5 [post-freeze].

**The honesty question — OPEN, not buried.** Stated at full bluntness:
G3's silent-miscarriage rate has never been measured by an instrument
that survived its own audit. Both attempted metrics died of structural
defects. The flags exist, the gating is exact, the rebirth is proven —
whether the memory ever mis-carries a value WITHOUT saying so is
unverified. Not established. Not falsified. Unmeasured. Any future
attempt (e.g., a corrected s_j-relative promise) is a new question for a
new pre-registration outside this series.

## §3 — The design rules the series earned

Each rule cited to the experiment that paid for it.

| Rule | Value / derivation | Earned by |
|---|---|---|
| Update | state += α·(obs − state), log-φ domain, causal pre-update read | exp002–003 |
| α | chosen from T = (1/α)·ln(Δ/f) given deadline and step size | exp004, six confirmations |
| f (planning values) | ≈ 0.7 shells UP, ≈ 3.3 shells DOWN | exp004, exp006–007b |
| Guard band G | ceil(p99(calibration d⁺)), min 1 shell; hi_eff = state + G | exp004 rule; exp006 vindication |
| Regime bound D | G + 1, min 2 shells, on raw deviation, direction-agnostic | exp006 |
| K | 3 — one constant, three roles: new-world threshold, transient threshold, infancy (may-not-vouch) threshold | exp005 (rebirth), exp007b (trigger, infancy) |
| Stranger rule | beyond hi_eff → declare, log, contribute zero to state | exp005–006 |
| Rebirth rule | K consecutive |d_raw| > D → state ← obs, signed log entry | exp006 |
| Declaration bound | ≤ true events + 2·N̂ + 3, N̂ from calibration tail | exp006 |
| Watchman trigger | infancy (0…K−1) + rebirth settle (K+4) + K-consecutive persistent deviation, clocked by the formula | exp007b |
| Noise reference | p95 of calibration |delta|, no multiplier | exp007b |
| Reproducibility contract | state is part of the spec: seeds, initial/final state, trace hash, bit-identical double-run | exp002 onward, never violated |

## §4 — The export at the license boundary

Zakhor Memory Architecture is proprietary research. The Horus Geometry
Fabric is CERN-OHL-S (strongly reciprocal open hardware). Nothing in this
repository's code crosses that boundary. What crosses, as DESIGN RULES
stated in prose, attributable and reimplementable independently:

1. **The recovery clock.** A leaky-integrated block scale recovers from a
   Δ-sized scale step in T = (1/α)·ln(Δ/f) update cycles. Choose the
   integration ratio from the worst-case step and the recovery deadline.
2. **The symmetric persistence gate.** Detect regime change on K
   consecutive raw deviations beyond a tail-derived bound, in either
   direction; re-seed rather than integrate through it. Gate outliers out
   of the state entirely; log them.
3. **The guarded ceiling.** Anchor the representable range one
   tail-derived margin above the tracked statistic, so the tracker's
   median-seeking does not place the ceiling at the median of arrivals.

Whether these rules enter Horus, and in what form, is a separately-scoped
future decision with the license boundary resolved explicitly first. No
zakhor code, identifiers, or file contents cross under any circumstance
without that resolution.

## §5 — Open mathematics

**1. The bounded return theorem (stated exp004, unproven, owed to the
blackboard).** For a carried value with phase deviation d, prefix-dependent
safe radius r (half the smallest three-distance gap), and true counterpart
shell j: if |d| < r and j is interior (j and its drift-image both exist in
the codebook), the return operation restores the unique true counterpart;
if j is an edge shell, the honest output is a declared loss. Never
exhibited an interior counterexample within its stated antecedent; never
proven. Its proof or refutation belongs to mathematics. The architecture
no longer waits for it.

**2. [post-freeze] The watchman's uncertainty relation (exp007b).** In any
causal register whose belief threshold is K observations: the false-alarm
floor scales as p^K (p = single-observation exceedance rate) while the
real-time warning blind spot is exactly K−1 observations whenever the K-th
observation triggers the corrective event. Confidence latency and
hallucination resistance are the same quantity read at two ends of K; no
real-time trigger sharing the regime's K can close the gap. Conjectured
escape, untested and outside this series: the register is a log, and a log
can be amended — a rebirth at t+K may retroactively mark t…t+K−1 as
covered. Real-time consumers still bear the K−1 exposure; the RECORD need
not. Remembering rightly may include correcting what was written — the
return operation, applied to the register itself. Untested. Unfrozen.
Left for whoever comes next.

**3. [post-freeze] The honesty instrument.** A silent-miscarriage metric
that survives its own audit: value-anchored, oracle-free, with the
half-gap bound stated relative to the enclosing shell s_j. Stated here as
an open measurement problem, per §2.

## §6 — Provenance

All architectural decisions were and remain the steward's: the mechanism's
inception ("as inputs come in, define that as work, slowly digest the
memory to exponent"), the ratio-as-proportion principle, the project's
name and its obligation (KEEP.md), the aliveness requirement that produced
the rebirth rule, the K = 3 procession grammar, Path A/B decisions, and
the steward's classification calls at every juncture.

Contributed by Claude (Anthropic) in adversarial-collaborative review:
the leaky-integrator formalization; the guard-band and D derivation rules;
the recovery formula and its logarithmic form; the safe-radius derivation
from the three-distance theorem; the zakhor–shamor textual pairing; the
symmetric-gate proposal; the closing-audit decision-rule structure; the
infancy rule; the pre-registration and freeze discipline as practiced.

Errors, by name, per project convention: Claude carried an exp002
metric-indexed finding across a metric change as if mechanism-fact
(step-DOWN prediction, falsified exp005); froze an internally
contradictory threshold in exp005 (p99-derived G against a 5% declaration
bound); derived the geometric promise against |v| where it belongs to
s_j (exp007 METRIC-DEFECT). Each was caught by the discipline both
parties maintained — thresholds frozen before code, falsifications
preserved, no post-hoc softening — which is the finding about method this
note quietly carries: the system corrected its authors.

The proof had the last word in every experiment, including the last one.
Six experiments, one day, twelve falsifications preserved, eight
establishments, three funerals with honors, two open theorems, one open
measurement. The series is closed.

Zakhor. Shamor. Return.