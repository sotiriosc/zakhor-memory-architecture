# EXPORT DRAFT — For publication in Horus-Geometry-Fabric (CERN-OHL-S) as prose design rules

<!--
 STAGING DRAFT — NOT YET EXPORTED.
 Contains no zakhor code, identifiers, or file contents.
 Steward reviews before anything crosses into Horus-Geometry-Fabric.
 Written in this repository (zakhor-memory-architecture) for steward review;
 this file itself is not intended to remain in the proprietary repository
 once the export is approved and performed — it is the draft of what
 would cross, not a permanent artifact here.
-->

**Status:** STAGING DRAFT — awaiting steward review · **Date:** 2026-07-16

This document proposes four prose design rules for the Horus-Geometry-Fabric
project (licensed CERN-OHL-S). Each rule is stated as general engineering
guidance for scale-tracking and quantization controllers, with no reference
to any proprietary source code, class or variable name, module structure,
or file content from the originating research. Citations below identify
the originating experiment by number and date only, so the empirical basis
of each rule can be traced without transferring anything proprietary. The
license boundary is resolved by this scoping: only the prose rules below
are proposed for export; no code, identifiers, or file contents cross with
them, so the CERN-OHL-S license would apply solely to what Horus's own
engineers write from this prose, not to any originating artifact.

---

## Rule 1 — The recovery clock

When a scale-tracking controller uses a leaky integrator to follow a
slowly varying statistic (such as a per-block magnitude ceiling), the time
to recover from a step change of size `delta` down to a residual fraction
`f` of that step follows a closed form:

```
T = (1 / alpha) * ln(delta / f)
```

where `alpha` is the integrator's update rate. This relationship lets an
implementer choose `alpha` directly from two operational requirements —
the worst-case step size the system must tolerate, and the deadline by
which recovery must be complete — rather than tuning `alpha` empirically.
The formula was derived and confirmed against measurement (±8% error
across a six-point sweep of update rates and step directions) in
experiment 2 (2026-07-11) and reconfirmed in every subsequent regression
through the sixth confirmation (2026-07-11).

## Rule 2 — The symmetric persistence gate

A scale-tracking controller should not treat every large deviation as a
genuine change in the tracked statistic — a single outlier and a real
regime shift look identical for one observation. The gate: define a
tail-derived bound from the calibration distribution (e.g., a high
percentile of observed deviation magnitude); when the raw deviation
exceeds that bound for `K` consecutive observations, in either direction
(the gate must be symmetric — a drop and a rise are treated the same
way), treat this as a genuine change and re-seed the tracked state
directly from the new observation. Any observation whose magnitude
exceeds the controller's current representable ceiling before the gate
fires is excluded from the state update entirely (it contributes zero
influence to the tracked statistic) and is separately logged as an
outlier. This decouples "the state was not updated by this value" from
"this value was silently corrupted or dropped" — the two must never be
conflated. This rule and its symmetric (both-direction) form were
established across experiments 5 and 6 (2026-07-11); the exclusion-and-log
behavior was confirmed to introduce zero state contribution from excluded
values across every regression re-run of the series (five to six
confirmations per check, 2026-07-11).

## Rule 3 — The guarded ceiling

A controller that tracks a running statistic and derives a representable
ceiling directly from it will systematically under-cover the true
maximum, because the tracked statistic lags the instantaneous signal by
construction. Fix: anchor the representable ceiling one tail-derived
margin above the tracked statistic, where the margin is itself derived
from the calibration distribution (e.g., a high percentile of positive
deviation, with a floor of at least one unit in the controller's native
step size) rather than fixed by hand. This converts a source of silent
under-coverage into a bounded, calibrated safety margin whose cost can be
measured directly. Established in experiment 4 (2026-07-11) and carried
unchanged through every subsequent experiment in the series (2026-07-11)
and into a real-workload validation series (2026-07-12).

## Rule 4 — The confidence sideband

A scale-tracking controller can emit a small per-block honesty signal at
no additional computational cost, because the classification it requires
— is this block within the controller's currently trusted range, or not
— is already implicit in the comparison the block normalizer performs on
every block. A 2-bit per-block tag distinguishing four states (nominal /
outlier-present / recently-reseeded / actively re-seeding) costs two bits
of side information per block and no new arithmetic. Beyond honesty
reporting, this sideband is empirically load-bearing at low-precision
depths: in a real-workload validation series (2026-07-12) sweeping
codebook depth and, separately, binary block-floating-point mantissa
width, a controller carrying this sideband matched or exceeded an
industry-standard rolling-window scale estimator by 12–15 percentage
points of classification accuracy under corrupted-frame conditions, at
mantissa widths as narrow as 3 and 6 bits — the range relevant to FP8-class
and BFP-class compressed inference. The accuracy cost of carrying the
sideband on uncorrupted data was measured at zero to within 1% absolute at
every depth tested except the shallowest (4-shell-equivalent), where a
small honesty tax (≈2%) was measured and is reported as a real, non-zero
cost of the mechanism at extreme shallowness, not hidden. The outlier flag
alone identified 100% of corrupted frames with zero false positives across
every depth and format tested in that series.

---

## Attribution

> These design rules were developed in the Zakhor Memory Architecture
> research project by Sotirios Chortogiannos. Claude (Anthropic) contributed
> formalization, adversarial review, and pre-registered experimental
> validation; all architectural decisions are the steward's. Exported as
> prose design rules only, resolving the proprietary ↔ CERN-OHL-S boundary
> by construction.

## License boundary

This export is scoped deliberately to prose design rules only. No zakhor
source code, class or function names, variable names, file paths, or file
contents are included above, by design — only mathematical relationships
(Rule 1's formula), general procedural descriptions (Rules 2–4), and
citations to experiment number and date for traceability. Because nothing
proprietary crosses with these rules, the CERN-OHL-S license governing
Horus-Geometry-Fabric applies only to whatever implementation Horus's own
engineers write from this prose — not to any originating repository or
artifact. **Steward reviews and approves before this document, or any
part of it, is copied into Horus-Geometry-Fabric.**
