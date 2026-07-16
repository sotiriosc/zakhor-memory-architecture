"""closing_audit_2026-07-11.py — Closing Audit: Decision Rule for the End of the Series.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
================================================================================

Status: DECISION RULE — frozen before computation.

Not an experiment. No pre-registered verdict is touched. No mechanism is
modified. No new hypothesis is tested. This is a steward's audit: the
choice between closing the series (Path A) and opening the permitted exp007b
follow-up is placed under a frozen rule, decided by measurement.

Measurements (defined before computation):
  E_f  — mean per-block maximum relative reconstruction error
          (max over nonzero v: |v − q| / |v|) across MID-RETURN-flagged
          blocks, EXCLUDING stranger-flagged and REGIME-settle blocks.
  E_u  — same, across unflagged blocks.
  Lift — E_f / E_u.
  Sensitivity — fraction of ground-truth transient blocks that are flagged.
  S1 noise floor — MID-RETURN coverage on S1.

Ground-truth transients:
  S4: cold-start blocks t=0..K+4 (0-indexed).
  S3: blocks step..step+8 (0-indexed), step = N_BLOCKS // 2.

Decision rule (frozen):
  Lift ≥ 2.0 AND sensitivity = 100% → CLOSE (Path A).
  Lift < 1.25                        → OPEN exp007b.
  1.25 ≤ Lift < 2.0                 → Gray zone, steward's judgment.
  Sensitivity < 100% in any branch   → reported in bold.

Constraints:
  Bit-identical replay of exp007 (SHA-256 must match 8c7757cb…).
  The persistence-gated fix is NOT simulated.
  H11 METRIC-DEFECT and H12 FALSIFIED stand unchanged in Note 02.

Prediction on record (Claude, pre-computation):
  Lift will land low (~1.0–1.3) because:
  (a) The maximum relative error per phi-codebook block is structurally
      bounded by (φ-1)/(φ+1) ≈ 0.236, occurring at midpoints between
      shells — independent of calibration state.
  (b) Formula-clock triggers fire on blocks with |d_raw| > 0.75 shells,
      which is a moderate deviation that moves hi only slightly off from
      the block's true scale; the structural 23.6% violation dominates
      in both flagged and unflagged blocks.
  (c) Therefore Lift ≈ 1.0, pointing to OPEN exp007b.
  The rule decides, not the expectation.
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import Dict, List, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

from exp002_scale_memory import (  # noqa: E402
    N_BLOCKS, BLOCK_SIZE, LEVELS, ALPHA_PRIMARY,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    SPIKE_SHELLS, SPIKE_PERIOD,
    hi_from_state,
    _phi_codebook, _snap, _block_stats,
    PhiZakhor, PhiStatic, GridZakhor, GridStatic, OraclePhi,
    _scales_stationary, _scales_step_up, _scales_step_down, _scales_spike,
    _mean,
)
from exp004_guard_and_return import _percentile  # noqa: E402
from exp005_gated_rebirth import K_REBIRTH, RECOVERY_SETTLE  # noqa: E402
from exp006_symmetric_gate import OraclePhiG, calibrate_exp6  # noqa: E402
from exp007_geometric_promise import (  # noqa: E402
    PhiZakhorKeepG3, _fresh_competitors_exp7, _run_exp7, _hash_raw, _all_runs,
)
from core.phi_theory import PHI, PHI_INV, _clipped_gauss, _lcg  # noqa: E402

# ── Replay hash from exp007 ────────────────────────────────────────────────
EXP007_SHA_PREFIX = "8c7757cb17bc6298"

STEP_BLOCK = N_BLOCKS // 2   # 2048 (0-indexed), = block_idx 2049 (1-indexed)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _regime_settle_set(regime_log: List[Tuple]) -> Set[int]:
    """Return set of 0-indexed block indices that are REGIME-settle blocks."""
    settle: Set[int] = set()
    for (block_idx, *_) in regime_log:
        t_start = block_idx - 1   # 1-indexed → 0-indexed
        for dt in range(RECOVERY_SETTLE):
            t = t_start + dt
            if 0 <= t < N_BLOCKS:
                settle.add(t)
    return settle


def _max_rel_err(block: List[float], book: Tuple[float, ...]) -> float:
    """Max |v − q| / |v| over nonzero v in block.

    Returns 0 if all values are zero (degenerate block).
    """
    max_err = 0.0
    for v in block:
        if abs(v) < 1e-300:
            continue
        _, q = _snap(v, book)
        err = abs(v - q) / abs(v)
        if err > max_err:
            max_err = err
    return max_err


def _run_with_blocks(
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> Tuple[Dict, List[List[float]]]:
    """Run stream and record blocks (for max-rel-err computation)."""
    rnd = _lcg(seed)
    results: Dict[str, List] = {c.name: [] for c in competitors}
    blocks: List[List[float]] = []
    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)
        blocks.append(block)
        for c in competitors:
            results[c.name].append(c.process_block(list(block)))
    return results, blocks


# ─────────────────────────────────────────────────────────────────────────────
# Audit engine
# ─────────────────────────────────────────────────────────────────────────────

def _audit_stream(
    stream_label: str,
    g3: PhiZakhorKeepG3,
    raw: Dict,
    blocks: List[List[float]],
    gt_transient_range: List[int],
) -> Dict:
    """Compute E_f, E_u, Lift, sensitivity for one stream's G3 run.

    Excludes from both E_f and E_u:
      - blocks where _block_stranger[t] is True (STRANGER register covers them)
      - blocks in REGIME-settle window (REGIME register covers them)

    E_f: over blocks that are MID-RETURN-flagged (formula-clock only).
    E_u: over blocks that are none of the above (truly unflagged).

    Sensitivity: fraction of gt_transient_range blocks (that are not
    excluded) that are MID-RETURN-flagged.
    """
    settle_set = _regime_settle_set(g3.regime_log)

    ef_vals: List[float] = []
    eu_vals: List[float] = []

    for t in range(N_BLOCKS):
        is_stranger = (t < len(g3._block_stranger) and g3._block_stranger[t])
        is_settle = t in settle_set

        if is_stranger or is_settle:
            continue   # excluded from both groups

        hi_t = raw["PHI-ZAKHOR-KEEP-G3"][t][3]
        book_t = _phi_codebook(max(hi_t, 1e-300), LEVELS)
        mre = _max_rel_err(blocks[t], book_t)

        is_mid = (t < len(g3.mid_return_flags) and g3.mid_return_flags[t])
        if is_mid:
            ef_vals.append(mre)
        else:
            eu_vals.append(mre)

    E_f = _mean(ef_vals) if ef_vals else float("nan")
    E_u = _mean(eu_vals) if eu_vals else float("nan")
    Lift = E_f / E_u if E_u > 0 else float("nan")

    # Sensitivity over gt_transient_range
    gt_numer = 0
    gt_flagged = 0
    for t in gt_transient_range:
        is_stranger = (t < len(g3._block_stranger) and g3._block_stranger[t])
        is_settle = t in settle_set
        if is_stranger or is_settle:
            continue   # excluded (covered by other registers)
        gt_numer += 1
        is_mid = (t < len(g3.mid_return_flags) and g3.mid_return_flags[t])
        if is_mid:
            gt_flagged += 1

    sensitivity = gt_flagged / gt_numer if gt_numer > 0 else float("nan")
    mid_total = sum(g3.mid_return_flags)
    mid_rate = mid_total / N_BLOCKS

    return {
        "stream": stream_label,
        "E_f": E_f, "E_u": E_u, "Lift": Lift,
        "n_flagged": len(ef_vals), "n_unflagged": len(eu_vals),
        "gt_numer": gt_numer, "gt_flagged": gt_flagged,
        "sensitivity": sensitivity,
        "mid_rate": mid_rate, "mid_total": mid_total,
        "n_settle": len(settle_set),
        "n_stranger": sum(g3._block_stranger),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Closing Audit — 2026-07-11")
    print("=" * 96)
    print("  Decision rule frozen before computation. Read-only replay of exp007.")
    print(f"  Expected SHA-256 prefix: {EXP007_SHA_PREFIX}")
    print(f"  K+4 = {K_REBIRTH+4}  settle_window = {RECOVERY_SETTLE}")
    print(f"  Decision branches: Lift ≥ 2.0 AND sens=100% → CLOSE;"
          f"  Lift < 1.25 → OPEN exp007b;  gray zone → steward judgment.")

    # ── Replay hash verification ─────────────────────────────────────────────
    G_r, D_r, nt_r, _ = calibrate_exp6(ALPHA_PRIMARY, STD_PEAKED)
    rA = _all_runs(G_r, D_r, nt_r)
    rB = _all_runs(G_r, D_r, nt_r)
    hA, hB = hashlib.sha256(), hashlib.sha256()
    for k in sorted(rA):
        hA.update(_hash_raw(rA[k]).encode())
        hB.update(_hash_raw(rB[k]).encode())
    sha_full = hA.hexdigest()
    sha_match = sha_full.startswith(EXP007_SHA_PREFIX) and hA.hexdigest() == hB.hexdigest()
    print(f"\n  SHA-256: {sha_full}")
    print(f"  Bit-identical: {'PASS' if hA.hexdigest()==hB.hexdigest() else 'FAIL'}"
          f"  Prefix match: {'PASS' if sha_full.startswith(EXP007_SHA_PREFIX) else 'FAIL'}")
    if not sha_match:
        print("  *** HASH MISMATCH. Audit aborted — replay is not bit-identical to exp007.")
        return
    print()

    all_audits: Dict[str, Dict] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                           (STD_SPREAD,  f"spread(std={STD_SPREAD})")):

        G, D, noise_thr, e_hat = calibrate_exp6(ALPHA_PRIMARY, std)
        print(f"{'━'*96}")
        print(f"  Distribution: {std_label}  G={G:.1f}  D={D:.1f}"
              f"  noise_threshold={noise_thr:.4f}")
        print("━" * 96)

        gt_s4 = list(range(0, K_REBIRTH + 4 + 1))       # t=0..7 (0-indexed)
        gt_s3 = list(range(STEP_BLOCK, STEP_BLOCK + 9))  # t=2048..2056

        for stream_tag, fn_s, off_s, spike_s, gt_range in (
            ("S1", _scales_stationary, 1, False, []),          # no true transients on S1
            ("S3↑", _scales_step_up, 4, False, gt_s3),
            ("S3↓", _scales_step_down, 5, False, gt_s3),
            ("S4", _scales_spike, 6, True, gt_s4),
        ):
            cs = _fresh_competitors_exp7(G, D, noise_thr, ALPHA_PRIMARY)
            raw, blocks = _run_with_blocks(
                cs, fn_s(), std, SEED_BASE + off_s, is_spike=spike_s
            )
            g3: PhiZakhorKeepG3 = next(
                c for c in cs if c.name == "PHI-ZAKHOR-KEEP-G3"
            )
            audit = _audit_stream(stream_tag, g3, raw, blocks, gt_range)
            all_audits[f"{stream_tag}-{std}"] = audit

            sens_str = (f"{100*audit['sensitivity']:.1f}%"
                        if audit['gt_numer'] > 0 else "N/A (all excl.)")
            print(f"\n  [{stream_tag} {std_label}]")
            print(f"    Settle set:  {audit['n_settle']} blocks"
                  f"  Stranger: {audit['n_stranger']} blocks"
                  f"  Mid-return (formula-clock): {audit['n_flagged']} blocks"
                  f"  Unflagged: {audit['n_unflagged']} blocks")
            print(f"    E_f = {audit['E_f']:.4f}  E_u = {audit['E_u']:.4f}"
                  f"  Lift = {audit['Lift']:.4f}")
            if gt_range:
                bold = "**" if (not (audit['sensitivity'] is float('nan'))
                                and audit['sensitivity'] < 1.0
                                and audit['gt_numer'] > 0) else ""
                print(f"    {bold}Sensitivity: {audit['gt_flagged']}/{audit['gt_numer']}"
                      f" = {sens_str}  (gt blocks not excl.){bold}")
            else:
                print(f"    S1 noise floor: mid-return coverage = "
                      f"{audit['mid_total']}/{N_BLOCKS}"
                      f" = {100*audit['mid_rate']:.1f}%  (all flags are false alarms by construction)")

    # ── Pooled Lift ──────────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("POOLED MEASUREMENTS")
    print(f"{'='*96}")
    print(f"\n  {'stream':<8} {'dist':<24} {'E_f':>8} {'E_u':>8} {'Lift':>8}"
          f" {'sensitivity':>14} {'mid_rate':>10}")

    s4_lifts, all_lifts = [], []
    s1_noise: List[float] = []
    sensitivity_misses: List[str] = []

    for std, std_label in ((STD_PEAKED, f"peaked"), (STD_SPREAD, f"spread")):
        for stream_tag in ("S1", "S3↑", "S3↓", "S4"):
            key = f"{stream_tag}-{std}"
            a = all_audits.get(key, {})
            if not a:
                continue
            lft = a.get("Lift", float("nan"))
            sens = a.get("sensitivity", float("nan"))
            gt_n = a.get("gt_numer", 0)
            sens_str = (f"{100*sens:.1f}%" if gt_n > 0 else "N/A")
            print(f"  {stream_tag:<8} {std_label:<24}"
                  f" {a.get('E_f',float('nan')):>8.4f}"
                  f" {a.get('E_u',float('nan')):>8.4f}"
                  f" {lft:>8.4f}"
                  f" {sens_str:>14}"
                  f" {100*a.get('mid_rate',0):>9.1f}%")
            if stream_tag == "S4":
                s4_lifts.append(lft)
            if stream_tag != "S1":
                all_lifts.append(lft)
            if stream_tag == "S1":
                s1_noise.append(a.get("mid_rate", 0.0))
            if gt_n > 0 and not (sens is float("nan")) and sens < 1.0:
                sensitivity_misses.append(f"{stream_tag}/{std_label} sens={100*sens:.1f}%")

    import math
    valid_lifts = [l for l in all_lifts if not math.isnan(l)]
    pooled_lift = _mean(valid_lifts) if valid_lifts else float("nan")
    s4_lift_mean = _mean([l for l in s4_lifts if not math.isnan(l)]) if s4_lifts else float("nan")
    s1_floor_mean = _mean(s1_noise) if s1_noise else 0.0

    print(f"\n  Pooled Lift (non-S1 streams): {pooled_lift:.4f}")
    print(f"  S4-only Lift:                 {s4_lift_mean:.4f}")
    print(f"  S1 noise floor mean:          {100*s1_floor_mean:.1f}%  (target: definitional false-alarm rate)")

    if sensitivity_misses:
        print(f"\n  *** SENSITIVITY < 100% IN: {', '.join(sensitivity_misses)}")
        print(f"  *** Per decision rule, Path A (CLOSE) is blocked regardless of Lift.")

    # ── Decision ─────────────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("DECISION")
    print(f"{'='*96}")

    # Apply rule to pooled (primary) and S4-only (secondary) Lift
    sens_100_everywhere = not sensitivity_misses
    # Determine branch
    if pooled_lift >= 2.0 and sens_100_everywhere:
        branch = "PATH A — CLOSE"
        rationale = (
            f"Pooled Lift={pooled_lift:.3f} ≥ 2.0 and sensitivity=100% everywhere. "
            f"Register is conservative but informative. "
            f"Series CLOSES. No exp007b."
        )
    elif pooled_lift < 1.25:
        branch = "OPEN exp007b"
        rationale = (
            f"Pooled Lift={pooled_lift:.3f} < 1.25. "
            f"Register carries insufficient information to distinguish "
            f"genuinely miscalibrated blocks from normal blocks. "
            f"A memory whose confidence signal carries no information "
            f"has an unkept register. exp007b opens (§2 mechanics only)."
        )
    else:
        branch = "GRAY ZONE — steward's judgment"
        rationale = (
            f"Pooled Lift={pooled_lift:.3f} in [1.25, 2.0). "
            f"Sensitivity={'100%' if sens_100_everywhere else '<100%'}. "
            f"Rule does not decide; steward's judgment, recorded in Note 02."
        )

    print(f"\n  Branch: {branch}")
    print(f"  Rationale: {rationale}")
    if sensitivity_misses:
        print(f"  *** Sensitivity misses: {', '.join(sensitivity_misses)}")
        print(f"  *** Path A was blocked by sensitivity < 100% regardless of Lift.")
    print()
    print(f"  S1 noise floor: {100*s1_floor_mean:.1f}% of blocks flagged on purely stationary data.")
    print(f"  Every S1 mid-return flag is a false alarm by construction.")
    print(f"  This is the register's irreducible base rate, entering Note 02.")
    print()
    print("  Note 02 note: H11 METRIC-DEFECT and H12 FALSIFIED stand unchanged.")
    print("  The audit verdict is copied verbatim into Note 02 §2 (funerals/costs).")

    # ── Claude's prediction postmortem ───────────────────────────────────────
    print(f"\n{'='*96}")
    print("PREDICTION POSTMORTEM (Claude, recorded pre-computation)")
    print(f"{'='*96}")
    print(f"  Predicted Lift: ~1.0–1.3  (structural 23.6% max-rel-err dominates both groups)")
    print(f"  Observed pooled Lift: {pooled_lift:.4f}")
    if pooled_lift < 1.3:
        print("  MATCH: structural floor hypothesis confirmed.")
        print("  The maximum relative error per block is bounded by (φ−1)/(φ+1)≈0.236")
        print("  for any phi-codebook block with adequate sample count, independent of")
        print("  calibration state. Formula-clock triggers do not elevate this floor.")
    elif pooled_lift >= 2.0:
        print("  MISMATCH: Lift exceeded prediction. Model of where register noise lives is wrong.")
        print("  The register carries more information than the structural analysis suggested.")
    else:
        print(f"  PARTIAL MATCH: Lift in gray zone, slightly above prediction.")

    # ── Save hash ────────────────────────────────────────────────────────────
    print(f"\n  Replay SHA-256: {sha_full}")
    print(f"  Output: research/results/closing_audit_2026-07-11.txt")


if __name__ == "__main__":
    main()
