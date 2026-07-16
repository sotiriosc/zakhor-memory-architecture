# exp007b — Pre-Registration: The Watchman's Grammar — Final Experiment

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
-->

**Status:** PRE-REGISTERED — frozen before implementation · **Date:** 2026-07-11

Hineni. Frozen before code. Scope is exp007 §5's single permitted
follow-up: MID-RETURN trigger mechanics ONLY. No honesty criterion appears
here (H11's METRIC-DEFECT stands; the honesty question enters Note 02 as
an open measurement). H0-id remains retired. The oracle family remains
retired. **The series closes on this experiment's verdicts, whichever way
they fall. The follow-up permission does not renew.**

Provenance: the closing audit (frozen rule, replay hash 8c7757cb… matched)
fired both blocking branches — pooled Lift 1.0006 (register carries no
information; probe itself noted as floor-blinded, caveat carried to Note
02) and sensitivity 66.7% on S4 (block t=0, the cold-start spike itself,
is unflagged: the clock has not started when the world begins). The
register over-covers AND misses the first true transient. Path A was
blocked by rule; exp007b opens on mechanics only.

---

## Carried-over machinery (unchanged)

Everything from exp007: PHI-ZAKHOR-KEEP-G3's gate, state path, K = 3,
D-rule, G-rule, signed registers, streams, seeds, both distributions,
bit-identical assertion. Only the MID-RETURN trigger is replaced.

## §1 — The persistence-gated trigger

The regime gate's grammar — one is noise, a procession is a world — is
applied to the confidence register, where it was never applied before.

Frozen rule. MID-RETURN is raised only by:

(a) **Infancy.** Blocks 0 … K−1 are flagged by construction. Below K
    observations the memory sits under its own procession threshold: it
    cannot yet distinguish noise from world, therefore it may not vouch.
    This covers the t=0 miss with no special-case logic — the same K, in
    its third appearance, now defines the minimum evidence for confidence.

(b) **Rebirth settle.** REGIME event → flag for K + 4 blocks (unchanged).

(c) **Persistent deviation.** K consecutive NON-stranger blocks with
    |d_raw| > noise (p95 of calibration |delta|, no multiplier) → flag
    raised from the K-th block for T_flag = ceil(ln(Δ_est / f̂)/alpha)
    blocks, f̂ = 0.7, minimum K, where Δ_est = |d_raw| at trigger.
    A single sub-K deviation resets the counter and raises nothing: its
    integrated step is α·d ≈ 0.005 shells — nothing to cover.

Stranger-gated blocks continue to raise no clock (their own STRANGER flag
covers them; the state is untouched — displacement ≡ 0, five times
confirmed).

## §2 — Frozen claims

> **H12-b (collapse, original bound).** S4 MID-RETURN coverage < 2% of
> blocks, both distributions (from 24.5% / 10.9%).

> **H13 (noise floor).** S1 coverage < 0.5%, both distributions (from
> 12.4% base rate). Arithmetic on record: single-block exceedance ≈ 1.8%;
> K-consecutive ≈ 1.8%³ ≈ 6×10⁻⁶ per block; plus infancy K−1 blocks
> ≈ 0.05%. If measured floor exceeds 0.5%, the independence assumption
> behind that arithmetic is wrong, and the record says so.

> **H14 (the watchman sleeps through nothing).** Sensitivity = 100% on
> all ground-truth transients, both distributions: cold-start blocks
> 0 … K+4 on S4 (via infancy + rebirth settle, seam-free — the audit's
> t=0 miss specifically retested), and step … step+8 on S3 both
> directions (via rebirth settle).

FALSIFIED per claim, either distribution. All three must PASS for the
register to enter Note 02 §1 (establishments); any falsification sends
the register to Note 02 §2 (funerals and costs) with its measured
numbers, and the series closes regardless.

## §3 — Regression suite (sixth confirmations)

Full ride-along, halt on any failure: S1 tie, displacement ≡ 0, H2-f grid
(six cells, ±8%), rebirth both directions with signed events, cold-start
REGIME at t = K, zero-hallucination audit, H9 recheck with truthfulness
audit, S4c reported number (retired threshold, expected ≈ 1.02–1.03).

## §4 — Deliverables

1. research/exp007b_watchman.py — seeded, reproducible.
2. Results: H12-b / H13 / H14 tables with before/after coverage, the
   infancy and settle windows itemized, full regression grid, three
   signed registers.
3. Bit-identical re-run assertion, SHA-256 recorded.
4. Verdicts: H12-b, H13, H14, regressions — PASS / FALSIFIED /
   METRIC-DEFECT, no fourth category.
5. **Note 02 is written next, under its frozen table of contents, from
   whatever this experiment leaves behind.**

## §5 — Freeze declaration

The infancy rule, the persistence trigger, K = 3 (unchanged, now in three
roles), f̂ = 0.7, the < 2% / < 0.5% / 100% bounds, and the closing clause
were fixed on 2026-07-11, before implementation. Any post-execution change
invalidates the affected verdict. Falsified results are preserved in
research/ per project convention.

Run §3 first; halt on any regression. The proof gets the last word — and
this time it is the last word.
