"""exp007b_watchman.py — The Watchman's Grammar: Final Experiment.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Pre-registered: hypotheses and thresholds frozen on 2026-07-11 before any code
was written. See docs/exp007b-pre-registration.md.

Scope: exp007 §5 single permitted follow-up — MID-RETURN trigger mechanics only.
H11 METRIC-DEFECT stands; H0-id remains retired; oracle family remains retired.
The series closes on this experiment's verdicts, whichever way they fall.
The follow-up permission does not renew.

Only change from exp007: PhiZakhorKeepG3 MID-RETURN trigger replaced by:
  (a) Infancy:            blocks 0…K−1 flagged by construction.
  (b) Rebirth settle:     REGIME event → K+4 blocks (ghost-fix unchanged).
  (c) Persistent deviat.: K consecutive non-stranger blocks with |d_raw| > noise
                          → flag from the K-th block for T_flag blocks (min K).
                          A single sub-K block resets the counter.

H12-b: S4 MID-RETURN coverage < 2%.
H13:   S1 MID-RETURN coverage < 0.5%.
H14:   sensitivity = 100% on all ground-truth transients (both distributions).

Run from repository root:

    python3 research/exp007b_watchman.py

Bit-identical re-run asserted inline; SHA-256 recorded.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from typing import Dict, List, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

from exp002_scale_memory import (  # noqa: E402
    N_BLOCKS, BLOCK_SIZE, LEVELS, ALPHA_PRIMARY, ALPHA_SWEEP,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    STEP_SHELLS, SPIKE_SHELLS, SPIKE_PERIOD,
    shell_coord, hi_from_state,
    _phi_codebook, _snap, _block_stats,
    ZakhorScale, PhiZakhor, PhiStatic, GridZakhor, GridStatic, OraclePhi,
    _scales_stationary, _scales_drift_up,
    _scales_step_up, _scales_step_down, _scales_spike,
    _mean,
)
from exp003_identity_recovery import (  # noqa: E402
    h2_r_recovery, s4a_state_integrity, s4c_collateral,
    SPIKE_TRUE_FRAC, H3_SILENT_THRESHOLD, S4C_MAX_R_RATIO, _pf,
)
from exp004_guard_and_return import (  # noqa: E402
    _percentile, h2_f_check, CAL_BLOCKS, CAL_SEED,
    H2F_TOLERANCE,
    EXP003_S4A_PEAK_PEAKED, EXP003_S4A_PEAK_SPREAD,
)
from exp005_gated_rebirth import (  # noqa: E402
    K_REBIRTH, F_HAT, RECOVERY_SETTLE, H6_RECOVERY_BUDGET,
    H5_DISP_LIMIT,
)
from exp006_symmetric_gate import (  # noqa: E402
    OraclePhiG, calibrate_exp6,
    h8_recovery, h9_declaration, h5a_displacement, honesty_v4,
    H10_SILENT_LIMIT, H9_SLACK, S4A_REG_TOL, _H8_CONSECUTIVE,
)
from core.phi_theory import PHI, PHI_INV, _clipped_gauss, _lcg  # noqa: E402

# ── exp007b constants ─────────────────────────────────────────────────────────

H12B_COLLAPSE_LIMIT: float = 0.02   # < 2% S4 MID-RETURN coverage — frozen §5
H13_NOISE_LIMIT: float = 0.005      # < 0.5% S1 MID-RETURN coverage — frozen §5

# exp007 baseline (from research/results/exp007_2026-07-11.txt)
H12_EXP007_PEAKED: int = 1003   # peaked S4 mid-return count
H12_EXP007_SPREAD: int = 445    # spread S4 mid-return count

# exp007 S1 baseline
H13_EXP007_PEAKED: int = 509    # peaked S1 mid-return count
H13_EXP007_SPREAD: int = 509    # spread S1 mid-return count

_NAMES_7B: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G3b", "PHI-STATIC",
    "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI", "ORACLE-PHI-G",
)

STEP_BLOCK: int = N_BLOCKS // 2   # 2048 (0-indexed)


# ─────────────────────────────────────────────────────────────────────────────
# 1. PHI-ZAKHOR-KEEP-G3b — persistence-gated MID-RETURN trigger
# ─────────────────────────────────────────────────────────────────────────────

class PhiZakhorKeepG3b:
    """Guard-band KEEP with persistence-gated MID-RETURN trigger.

    Three-part trigger (frozen §5):
      (a) Infancy:           blocks 0…K−1 flagged by construction.
      (b) Rebirth settle:    REGIME rebirth → SET mid_countdown = K+4.
      (c) Persistent deviat: K consecutive non-stranger blocks with
                             |d_raw| > noise → flag from K-th block for
                             T_flag = max(K, ceil(ln(Δ/f̂)/α)) blocks.

    Replaces the formula-clock trigger from exp007 (PhiZakhorKeepG3).
    All other mechanics (regime gate, G-rule, D-rule, stranger gating,
    state path) are unchanged from exp007.
    """

    name = "PHI-ZAKHOR-KEEP-G3b"
    is_phi = True

    def __init__(self, G: float, D: float, noise_threshold: float,
                 alpha: float = ALPHA_PRIMARY) -> None:
        self.G = G
        self.D = D
        self.noise_threshold = noise_threshold
        self.alpha = alpha

        self._s: float = 0.0
        self._ready: bool = False
        self._regime_counter: int = 0
        self._mid_countdown: int = 0
        self._persist_counter: int = 0   # NEW: persistence counter

        self._block_idx: int = 0
        self._total: int = 0
        self._declared: int = 0

        self.stranger_log: List[Tuple[int, float, float]] = []
        self.mid_return_flags: List[bool] = []
        self.regime_log: List[Tuple[int, float, float, float]] = []
        self._state_log: List[Tuple[float, float]] = []
        self._block_stranger: List[bool] = []   # True if stranger non-reborn block

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        self._block_idx += 1
        block_idx_0 = self._block_idx - 1    # 0-indexed block number
        max_mag = max(abs(v) for v in block) if block else 0.0
        obs = shell_coord(max_mag) if max_mag > 1e-300 else 0.0

        # ── Cold start ───────────────────────────────────────────────────────
        if not self._ready:
            self._s = obs
            self._ready = True
            pre_orig = obs
        else:
            pre_orig = self._s

        # ── Symmetric regime detection (before gating) ────────────────────
        d_raw = obs - pre_orig
        if abs(d_raw) > self.D:
            self._regime_counter += 1
        else:
            self._regime_counter = 0

        hi = hi_from_state(pre_orig - self.G)
        is_stranger = max_mag > hi
        reborn = False

        if self._regime_counter >= K_REBIRTH:
            old_state = self._s
            self._s = obs
            self._regime_counter = 0
            signed_shells = obs - old_state
            self.regime_log.append(
                (self._block_idx, old_state, obs, signed_shells)
            )
            reborn = True
            hi = hi_from_state(obs - self.G)
            is_stranger = max_mag > hi
        elif is_stranger:
            pass   # gating: state frozen
        else:
            self._s = pre_orig + self.alpha * (obs - pre_orig)

        self._state_log.append((pre_orig, self._s))
        self._block_stranger.append(is_stranger and not reborn)

        # ── Persistence-gated mid-return flag ─────────────────────────────
        #
        # (a) Infancy: 0-indexed blocks 0…K-1 are always flagged.
        is_infancy = block_idx_0 < K_REBIRTH

        # (b) Rebirth settle: SET countdown (ghost-fix unchanged from exp007).
        # (c) Persistent deviation: count consecutive qualifying blocks;
        #     fire on K-th and every subsequent qualifying block.
        if reborn:
            # Ghost-fix: SET countdown to K+4, reset persistence counter.
            self._mid_countdown = RECOVERY_SETTLE
            self._persist_counter = 0
        elif not is_stranger and abs(d_raw) > self.noise_threshold:
            # Qualifying block: increment persistence counter.
            self._persist_counter += 1
            if self._persist_counter >= K_REBIRTH:
                # K-th (or later) consecutive qualifying block → fire.
                d_est = max(abs(d_raw), 1e-6)
                if d_est > F_HAT:
                    try:
                        T_flag = max(K_REBIRTH,
                                     math.ceil(math.log(d_est / F_HAT) / self.alpha))
                    except (ValueError, OverflowError):
                        T_flag = K_REBIRTH
                else:
                    T_flag = K_REBIRTH
                self._mid_countdown = max(self._mid_countdown, T_flag)
        else:
            # Sub-K deviation or stranger: reset persistence counter.
            self._persist_counter = 0

        # Combined flag: infancy OR countdown active.
        is_mid = is_infancy or (self._mid_countdown > 0)
        if self._mid_countdown > 0:
            self._mid_countdown -= 1
        self.mid_return_flags.append(is_mid)

        # ── Quantize ─────────────────────────────────────────────────────────
        book = _phi_codebook(hi, LEVELS)
        normal: List[float] = []
        for v in block:
            self._total += 1
            if is_stranger and not reborn and abs(v) > hi:
                self._declared += 1
                self.stranger_log.append(
                    (self._block_idx, shell_coord(abs(v)), abs(v) / hi - 1.0)
                )
            else:
                normal.append(v)

        mse, under, over = _block_stats(normal, book) if normal else (0.0, 0.0, 0.0)
        return mse, under, over, hi

    @property
    def declared_rate(self) -> float:
        return self._declared / self._total if self._total else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. h8_recovery wrapper for G3b name
# ─────────────────────────────────────────────────────────────────────────────

def h8_recovery_7b(
    raw: Dict,
    g3b: PhiZakhorKeepG3b,
    step_block: int,
    stream_label: str,
    pre_window: int = 256,
    near_window: int = 16,
) -> Dict:
    """H8: recovery check using PHI-ZAKHOR-KEEP-G3b name.

    h8_recovery (exp006) hard-codes 'PHI-ZAKHOR-KEEP-G3'; this wrapper
    calls h2_r_recovery directly and looks up the G3b competitor by its
    actual name so the regression is correctly attributed.
    """
    from exp003_identity_recovery import h2_r_recovery  # noqa: F401
    rec = h2_r_recovery(raw, step_block, pre_window)
    g3b_rec = rec.get("PHI-ZAKHOR-KEEP-G3b", {})
    pz_rec = rec.get("PHI-ZAKHOR", {})

    regime_events = g3b.regime_log
    near = [e for e in regime_events
            if step_block <= e[0] <= step_block + near_window]

    T = g3b_rec.get("recovery_blocks")
    ok = T is not None and T <= H6_RECOVERY_BUDGET and len(near) == 1
    return {
        "stream": stream_label,
        "recovery_blocks": T,
        "budget": H6_RECOVERY_BUDGET,
        "pz_recovery": pz_rec.get("recovery_blocks"),
        "regime_total": len(regime_events),
        "regime_near_step": near,
        "pass": ok,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stream runner
# ─────────────────────────────────────────────────────────────────────────────

def _fresh_competitors_7b(G: float, D: float, noise_threshold: float,
                           alpha: float = ALPHA_PRIMARY) -> List:
    return [
        PhiZakhor(alpha),
        PhiZakhorKeepG3b(G, D, noise_threshold, alpha),
        PhiStatic(),
        GridZakhor(alpha),
        GridStatic(),
        OraclePhi(),
        OraclePhiG(G),
    ]


def _run_7b(
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> Dict[str, List[Tuple[float, float, float, float]]]:
    rnd = _lcg(seed)
    results: Dict[str, List[Tuple[float, float, float, float]]] = {
        c.name: [] for c in competitors
    }
    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)
        for c in competitors:
            results[c.name].append(c.process_block(list(block)))
    return results


def _hash_raw_7b(raw: Dict) -> str:
    h = hashlib.sha256()
    for name in sorted(raw.keys()):
        for mse, under, over, _ in raw[name]:
            h.update(f"{mse:.15e}{under:.15e}{over:.15e}".encode())
    return h.hexdigest()[:16]


def _print_summary_7b(label: str,
                      raw: Dict[str, List[Tuple[float, float, float, float]]]) -> None:
    print(f"\n{label}")
    print("-" * 88)
    print(f"  {'competitor':<28} {'MSE':>14} {'underflow':>12} {'overflow':>12}")
    for name in _NAMES_7B:
        if name not in raw:
            continue
        ms = [r[0] for r in raw[name]]
        us = [r[1] for r in raw[name]]
        os_ = [r[2] for r in raw[name]]
        print(f"  {name:<28} {_mean(ms):>14.4e} {_mean(us):>12.4e} {_mean(os_):>12.4e}")


def _all_runs_7b(G: float, D: float, noise_thr: float,
                  alpha: float = ALPHA_PRIMARY) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for std in (STD_PEAKED, STD_SPREAD):
        for tag, fn, off, spike in (
            (f"S1-{std}", _scales_stationary, 1, False),
            (f"S3u-{std}", _scales_step_up, 4, False),
            (f"S3d-{std}", _scales_step_down, 5, False),
            (f"S4-{std}", _scales_spike, 6, True),
        ):
            cs = _fresh_competitors_7b(G, D, noise_thr, alpha)
            out[tag] = _run_7b(cs, fn(), std, SEED_BASE + off, is_spike=spike)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 3. H12-b / H13 coverage checks
# ─────────────────────────────────────────────────────────────────────────────

def h12b_coverage(g3b: PhiZakhorKeepG3b) -> Dict:
    """H12-b: S4 MID-RETURN coverage < 2%."""
    mid_total = sum(g3b.mid_return_flags)
    mid_rate = mid_total / N_BLOCKS
    return {
        "mid_total": mid_total,
        "mid_rate": mid_rate,
        "pass": mid_rate < H12B_COLLAPSE_LIMIT,
    }


def h13_noise_floor(g3b: PhiZakhorKeepG3b) -> Dict:
    """H13: S1 MID-RETURN coverage < 0.5%."""
    mid_total = sum(g3b.mid_return_flags)
    mid_rate = mid_total / N_BLOCKS
    return {
        "mid_total": mid_total,
        "mid_rate": mid_rate,
        "pass": mid_rate < H13_NOISE_LIMIT,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. H14 sensitivity check
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


def h14_sensitivity(g3b: PhiZakhorKeepG3b, gt_range: List[int]) -> Dict:
    """H14: fraction of non-excluded ground-truth transients that are flagged.

    Excludes: REGIME-settle blocks and STRANGER blocks.
    Ground-truth ranges (0-indexed):
      S4: blocks 0…K+4.
      S3: blocks step…step+8.
    """
    settle_set = _regime_settle_set(g3b.regime_log)
    missed: List[int] = []
    n_excluded = 0
    n_non_excluded = 0
    n_flagged = 0

    for t in gt_range:
        if t >= N_BLOCKS:
            continue
        is_stranger = (t < len(g3b._block_stranger) and g3b._block_stranger[t])
        in_settle = t in settle_set
        if is_stranger or in_settle:
            n_excluded += 1
            continue
        n_non_excluded += 1
        is_mid = (t < len(g3b.mid_return_flags) and g3b.mid_return_flags[t])
        if is_mid:
            n_flagged += 1
        else:
            missed.append(t)

    sens = n_flagged / n_non_excluded if n_non_excluded > 0 else None
    return {
        "sensitivity": sens,
        "n_non_excluded": n_non_excluded,
        "n_flagged": n_flagged,
        "n_excluded": n_excluded,
        "missed": missed,
        "na": n_non_excluded == 0,
        "pass": (sens == 1.0) if sens is not None else False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 007b — The Watchman's Grammar")
    print("=" * 96)
    print("  Pre-registered 2026-07-11. Final experiment. Series closes on these verdicts.")
    print(f"  K={K_REBIRTH} (now in three roles: regime, settle, infancy + persistence threshold)")
    print(f"  f̂={F_HAT}  settle={RECOVERY_SETTLE}  H12b_limit={H12B_COLLAPSE_LIMIT:.0%}"
          f"  H13_limit={H13_NOISE_LIMIT:.1%}")
    print(f"  MID-RETURN trigger: (a) Infancy t<K; (b) Rebirth → K+4; "
          f"(c) K consecutive |d_raw|>noise.")
    print(f"  H11 METRIC-DEFECT stands (not retested). H0-id retired. Oracle family retired.")
    print(f"  exp007 S4 baseline: peaked={H12_EXP007_PEAKED}/{N_BLOCKS}"
          f" ({100*H12_EXP007_PEAKED/N_BLOCKS:.1f}%)"
          f"  spread={H12_EXP007_SPREAD}/{N_BLOCKS}"
          f" ({100*H12_EXP007_SPREAD/N_BLOCKS:.1f}%)")
    print(f"  exp007 S1 baseline: peaked≈{H13_EXP007_PEAKED}/{N_BLOCKS}"
          f" ({100*H13_EXP007_PEAKED/N_BLOCKS:.1f}%)"
          f"  spread≈{H13_EXP007_SPREAD}/{N_BLOCKS}"
          f" ({100*H13_EXP007_SPREAD/N_BLOCKS:.1f}%)")

    gt_s4  = list(range(0, K_REBIRTH + 4 + 1))     # 0…K+4 = 0…7 inclusive
    gt_s3  = list(range(STEP_BLOCK, STEP_BLOCK + 9)) # step…step+8

    verdicts: Dict[str, str] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                            (STD_SPREAD, f"spread(std={STD_SPREAD})")):

        # ── Calibration ────────────────────────────────────────────────────
        G, D, noise_thr, e_hat = calibrate_exp6(ALPHA_PRIMARY, std)
        true_spike_count = int(N_BLOCKS / SPIKE_PERIOD) - 1
        N_hat = e_hat * N_BLOCKS
        h9_limit = true_spike_count + 2 * N_hat + H9_SLACK

        print(f"\n{'━'*96}")
        print(f"  Distribution: {std_label}")
        print(f"  Calibration: G={G:.1f}  D={D:.1f}  noise_threshold={noise_thr:.4f}"
              f"  e_hat={e_hat:.4f}  N̂={N_hat:.1f}  H9_limit={h9_limit:.1f}")
        print("━" * 96)

        # ── §3 Regression: S1 stationary ────────────────────────────────────
        cs_s1 = _fresh_competitors_7b(G, D, noise_thr)
        raw_s1 = _run_7b(cs_s1, _scales_stationary(), std, SEED_BASE + 1)
        g3b_s1: PhiZakhorKeepG3b = next(
            c for c in cs_s1 if c.name == "PHI-ZAKHOR-KEEP-G3b")
        _print_summary_7b(f"§3 S1 STATIONARY ({std_label})", raw_s1)

        pz_mse = _mean([raw_s1["PHI-ZAKHOR"][t][0] for t in range(N_BLOCKS)])
        g3b_mse = _mean([raw_s1["PHI-ZAKHOR-KEEP-G3b"][t][0] for t in range(N_BLOCKS)])
        reg_ok = g3b_mse <= pz_mse * 1.05
        verdicts[f"regression-{std}"] = _pf(reg_ok)
        n_regime_s1 = len(g3b_s1.regime_log)
        mid_s1 = sum(g3b_s1.mid_return_flags)
        print(f"  Regression: PHI-ZAKHOR {pz_mse:.4e}  G3b {g3b_mse:.4e}"
              f" — {verdicts[f'regression-{std}']}")
        print(f"  S1 REGIME events: {n_regime_s1} (want 0)"
              f"  stranger: {len(g3b_s1.stranger_log)}"
              f"  mid-return blocks: {mid_s1}/{N_BLOCKS}"
              f" ({100*mid_s1/N_BLOCKS:.2f}%)")
        if not reg_ok:
            print("  *** REGRESSION FAIL. Halting.")
            return

        # S1 oracle-relative for S4c
        oracle_mse_s1 = [raw_s1["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]
        R_s1: Dict[str, float] = {}
        for name in _NAMES_7B:
            if name in raw_s1 and name != "ORACLE-PHI":
                R_s1[name] = _mean([
                    raw_s1[name][t][0] / max(oracle_mse_s1[t], 1e-30)
                    for t in range(N_BLOCKS)
                ])

        # ── §3 Regression: S2 drift — hallucination audit ──────────────────
        cs_s2 = _fresh_competitors_7b(G, D, noise_thr)
        raw_s2 = _run_7b(cs_s2, _scales_drift_up(), std, SEED_BASE + 2)
        g3b_s2: PhiZakhorKeepG3b = next(
            c for c in cs_s2 if c.name == "PHI-ZAKHOR-KEEP-G3b")
        _print_summary_7b(f"S2 SLOW DRIFT ↑ ({std_label})", raw_s2)
        n_regime_s2 = len(g3b_s2.regime_log)
        mid_s2 = sum(g3b_s2.mid_return_flags)
        print(f"  S2 REGIME events: {n_regime_s2}"
              f"  mid-return: {mid_s2}/{N_BLOCKS} ({100*mid_s2/N_BLOCKS:.2f}%)"
              f"  ({'expected 0 regime' if n_regime_s2 == 0 else '*** FINDING: drift fired regime'})")

        # ── §3 Regression: H8 S3↑ step-UP (sixth confirmation) ─────────────
        cs_s3u = _fresh_competitors_7b(G, D, noise_thr)
        raw_s3u = _run_7b(cs_s3u, _scales_step_up(), std, SEED_BASE + 4)
        g3b_s3u: PhiZakhorKeepG3b = next(
            c for c in cs_s3u if c.name == "PHI-ZAKHOR-KEEP-G3b")
        _print_summary_7b(
            f"§3 S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})", raw_s3u)
        h8_up = h8_recovery_7b(raw_s3u, g3b_s3u, STEP_BLOCK, "S3↑")
        verdicts[f"H8b-{std}"] = _pf(h8_up["pass"])
        pz_up_T = h8_up["pz_recovery"]
        g3b_up_T = h8_up["recovery_blocks"]
        print(f"  H8(b) S3↑: REGIME_total={h8_up['regime_total']}"
              f"  near_step={len(h8_up['regime_near_step'])} (want 1)"
              f"  PHI-ZAKHOR T={pz_up_T}  G3b T={g3b_up_T}"
              f" (budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H8b-{std}']}")
        for ev in h8_up["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  signed={ev[3]:+.3f} shells")
        mid_s3u = sum(g3b_s3u.mid_return_flags)
        print(f"  S3↑ mid-return blocks (persistence trigger): {mid_s3u}/{N_BLOCKS}"
              f"  ({100*mid_s3u/N_BLOCKS:.2f}%)")

        # H14 sensitivity on S3↑
        h14_s3u = h14_sensitivity(g3b_s3u, gt_s3)
        if h14_s3u["na"]:
            s3u_sens_str = "N/A (all excluded — strangers+settle cover S3↑)"
        else:
            s3u_sens_str = (f"{h14_s3u['n_flagged']}/{h14_s3u['n_non_excluded']}"
                            f" = {h14_s3u['sensitivity']:.1%}"
                            f"  {'PASS' if h14_s3u['pass'] else 'MISS: t=' + str(h14_s3u['missed'])}")
        print(f"  H14 sensitivity S3↑: {s3u_sens_str}")

        # ── §3 Regression: H8 S3↓ step-DOWN (sixth confirmation) ───────────
        cs_s3d = _fresh_competitors_7b(G, D, noise_thr)
        raw_s3d = _run_7b(cs_s3d, _scales_step_down(), std, SEED_BASE + 5)
        g3b_s3d: PhiZakhorKeepG3b = next(
            c for c in cs_s3d if c.name == "PHI-ZAKHOR-KEEP-G3b")
        _print_summary_7b(
            f"§3 S3 STEP ↓ (−{STEP_SHELLS} shells) ({std_label})", raw_s3d)
        h8_dn = h8_recovery_7b(raw_s3d, g3b_s3d, STEP_BLOCK, "S3↓")
        verdicts[f"H8a-{std}"] = _pf(h8_dn["pass"])
        pz_dn_T = h8_dn["pz_recovery"]
        g3b_dn_T = h8_dn["recovery_blocks"]
        print(f"  H8(a) S3↓: REGIME_total={h8_dn['regime_total']}"
              f"  near_step={len(h8_dn['regime_near_step'])} (want 1)"
              f"  PHI-ZAKHOR T={pz_dn_T}  G3b T={g3b_dn_T}"
              f" (budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H8a-{std}']}")
        for ev in h8_dn["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  signed={ev[3]:+.3f} shells")
        mid_s3d = sum(g3b_s3d.mid_return_flags)
        print(f"  S3↓ mid-return blocks (persistence trigger): {mid_s3d}/{N_BLOCKS}"
              f"  ({100*mid_s3d/N_BLOCKS:.2f}%)")
        verdicts[f"H8ab-{std}"] = _pf(h8_up["pass"] and h8_dn["pass"])

        # H14 sensitivity on S3↓
        h14_s3d = h14_sensitivity(g3b_s3d, gt_s3)
        if h14_s3d["na"]:
            s3d_sens_str = "N/A (all excluded)"
        else:
            sens_val = h14_s3d['sensitivity']
            missed_str = (f"  missed: t={h14_s3d['missed']}"
                          if h14_s3d['missed'] else "")
            s3d_sens_str = (f"{h14_s3d['n_flagged']}/{h14_s3d['n_non_excluded']}"
                            f" = {sens_val:.1%}{missed_str}")
        print(f"  H14 sensitivity S3↓: {s3d_sens_str}")
        h14_s3d_pass = h14_s3d["pass"] or h14_s3d["na"]
        h14_s3u_pass = h14_s3u["pass"] or h14_s3u["na"]
        verdicts[f"H14-S3-{std}"] = _pf(h14_s3d_pass and h14_s3u_pass)
        print(f"  H14 S3 combined (both directions): {verdicts[f'H14-S3-{std}']}")

        # ── §3 Regression: S4 spikes ─────────────────────────────────────────
        cs_s4 = _fresh_competitors_7b(G, D, noise_thr)
        raw_s4 = _run_7b(cs_s4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        g3b_s4: PhiZakhorKeepG3b = next(
            c for c in cs_s4 if c.name == "PHI-ZAKHOR-KEEP-G3b")
        _print_summary_7b(
            f"§3 S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            raw_s4,
        )

        # S4a regression (PHI-ZAKHOR ungated — sixth confirmation)
        s4a = s4a_state_integrity(raw_s4, "PHI-ZAKHOR")
        ref = EXP003_S4A_PEAK_PEAKED if std == STD_PEAKED else EXP003_S4A_PEAK_SPREAD
        s4a_reg_ok = abs(s4a["peak_displacement"] - ref) <= S4A_REG_TOL
        verdicts[f"S4a-reg-{std}"] = _pf(s4a_reg_ok)
        print(f"\n  §3 S4a regression: peak_disp={s4a['peak_displacement']:.4f}"
              f" (ref={ref:.4f}) — {verdicts[f'S4a-reg-{std}']}")

        # H8(c): cold-start self-healing on S4
        n_regime_s4 = len(g3b_s4.regime_log)
        regime_s4_early = [e for e in g3b_s4.regime_log if e[0] <= K_REBIRTH + 1]
        regime_s4_late = [e for e in g3b_s4.regime_log if e[0] > K_REBIRTH + 1]
        h8c_ok = (len(regime_s4_early) == 1 and len(regime_s4_late) == 0)
        verdicts[f"H8c-{std}"] = _pf(h8c_ok)
        print(f"  §3 H8(c) cold-start: REGIME_total={n_regime_s4}"
              f"  early={len(regime_s4_early)} (want 1)"
              f"  late={len(regime_s4_late)} (want 0) — {verdicts[f'H8c-{std}']}")
        for ev in g3b_s4.regime_log[:3]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  signed={ev[3]:+.3f} shells")

        # H5a: displacement identically zero under gating
        h5a = h5a_displacement(g3b_s4)
        verdicts[f"H5a-{std}"] = _pf(h5a["pass"])
        print(f"  §3 H5a displacement: peak={h5a['peak']:.6f}"
              f"  all_zero={h5a['all_zero']}  n={h5a['n']} — {verdicts[f'H5a-{std}']}")

        # H8(d): zero hallucinations on S1, S2, between isolated spikes
        h8d_ok = (len(regime_s4_late) == 0
                  and n_regime_s1 == 0
                  and n_regime_s2 == 0)
        verdicts[f"H8d-{std}"] = _pf(h8d_ok)
        print(f"  §3 H8(d) hallucination: S1={n_regime_s1}  S2={n_regime_s2}"
              f"  S4_isolated={len(regime_s4_late)} (all want 0) — {verdicts[f'H8d-{std}']}")

        verdicts[f"H8-{std}"] = _pf(
            h8_up["pass"] and h8_dn["pass"] and h8c_ok and h8d_ok
        )
        print(f"  H8 overall: {verdicts[f'H8-{std}']}")

        # S4c collateral (retired threshold — reported only)
        s4c = s4c_collateral(raw_s4, R_s1)
        print(f"  §3 S4c collateral (retired threshold {S4C_MAX_R_RATIO}, reported only):")
        for nm in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G3b"):
            if nm in s4c:
                d2 = s4c[nm]
                print(f"    {nm:<30} R_normal={d2['R_normal']:.3f}"
                      f"  R_s1={d2['R_s1']:.3f}  ratio={d2['ratio']:.3f}")

        # H9 recheck (sixth confirmation)
        h9 = h9_declaration(g3b_s4, true_spike_count, e_hat)
        verdicts[f"H9-{std}"] = _pf(h9["pass"])
        print(f"\n  §3 H9 declaration: declared={h9['declared']}"
              f"  true_spikes={h9['true_spikes']}  N̂={h9['N_hat']:.1f}"
              f"  limit={h9['limit']:.1f}"
              f"  truthful={h9['truthful']} — {verdicts[f'H9-{std}']}")
        print(f"    Stranger log (first 3): {g3b_s4.stranger_log[:3]}")

        # ── §2 H12-b: persistence-gated collapse ────────────────────────────
        mid_s4 = sum(g3b_s4.mid_return_flags)
        mid_rate_s4 = mid_s4 / N_BLOCKS
        exp7_ref = H12_EXP007_PEAKED if std == STD_PEAKED else H12_EXP007_SPREAD
        h12b = h12b_coverage(g3b_s4)
        verdicts[f"H12b-coverage-{std}"] = _pf(h12b["pass"])

        # Itemize infancy + settle vs persistence contributions
        infancy_count = sum(1 for t in range(min(K_REBIRTH, N_BLOCKS))
                            if g3b_s4.mid_return_flags[t])
        settle_set_s4 = _regime_settle_set(g3b_s4.regime_log)
        settle_non_infancy = sum(
            1 for t in settle_set_s4 if t >= K_REBIRTH and g3b_s4.mid_return_flags[t]
        )
        persistence_only = mid_s4 - infancy_count - settle_non_infancy

        print(f"\n  §2 H12-b ghost-collapse ({std_label}):")
        print(f"    exp007={exp7_ref}/{N_BLOCKS} ({100*exp7_ref/N_BLOCKS:.1f}%)"
              f"  exp007b={mid_s4}/{N_BLOCKS} ({100*mid_rate_s4:.2f}%)"
              f"  limit={H12B_COLLAPSE_LIMIT:.0%} — {verdicts[f'H12b-coverage-{std}']}")
        print(f"    Infancy (t=0…{K_REBIRTH-1}): {infancy_count} blocks"
              f"  Rebirth-settle (t≥K): {settle_non_infancy} blocks"
              f"  Persistence-only: {persistence_only} blocks")

        # ── H13: S1 noise floor ──────────────────────────────────────────────
        h13 = h13_noise_floor(g3b_s1)
        verdicts[f"H13-coverage-{std}"] = _pf(h13["pass"])
        exp7_s1_ref = H13_EXP007_PEAKED if std == STD_PEAKED else H13_EXP007_SPREAD
        infancy_s1 = sum(1 for t in range(min(K_REBIRTH, N_BLOCKS))
                         if g3b_s1.mid_return_flags[t])
        print(f"\n  §1 H13 noise floor ({std_label}):")
        print(f"    exp007≈{exp7_s1_ref}/{N_BLOCKS} ({100*exp7_s1_ref/N_BLOCKS:.1f}%)"
              f"  exp007b={h13['mid_total']}/{N_BLOCKS} ({100*h13['mid_rate']:.3f}%)"
              f"  limit={H13_NOISE_LIMIT:.1%} — {verdicts[f'H13-coverage-{std}']}")
        print(f"    Infancy (t=0…{K_REBIRTH-1}): {infancy_s1} blocks"
              f"  REGIME events: {n_regime_s1}"
              f"  Persistence triggers: {h13['mid_total'] - infancy_s1}")

        # ── H14: sensitivity on S4 ───────────────────────────────────────────
        h14_s4 = h14_sensitivity(g3b_s4, gt_s4)
        settle_set_s4_labeled = sorted(settle_set_s4)
        sens_s4 = h14_s4["sensitivity"]
        verdicts[f"H14-S4-{std}"] = _pf(h14_s4["pass"])

        print(f"\n  §1 H14 sensitivity ({std_label}):")
        print(f"    Ground-truth S4: t=0…{K_REBIRTH+4} = {gt_s4}")
        print(f"    Regime-settle blocks (0-indexed): {settle_set_s4_labeled[:10]}"
              f"{'…' if len(settle_set_s4_labeled)>10 else ''}")
        if h14_s4["na"]:
            print(f"    S4: N/A (all ground-truth excluded)")
        else:
            print(f"    S4: {h14_s4['n_flagged']}/{h14_s4['n_non_excluded']}"
                  f" = {sens_s4:.1%} (excluded: {h14_s4['n_excluded']})"
                  f"  — {verdicts[f'H14-S4-{std}']}")
            if h14_s4["missed"]:
                print(f"    *** S4 MISSED (0-indexed): {h14_s4['missed']}")
        print(f"    S3↑: {s3u_sens_str}")
        print(f"    S3↓: {s3d_sens_str}")

        # H14 overall for this distribution
        h14_all_ok = (
            (h14_s4["pass"] or h14_s4["na"])
            and h14_s3u_pass
            and h14_s3d_pass
        )
        verdicts[f"H14-{std}"] = _pf(h14_all_ok)
        print(f"    H14 ({std_label}): {verdicts[f'H14-{std}']}")

        # Three registers on S4
        print(f"\n  Three registers ({std_label}, S4):")
        print(f"    Stranger: {len(g3b_s4.stranger_log)} entries."
              f"  Mid-return: {mid_s4}/{N_BLOCKS} ({100*mid_rate_s4:.2f}%)."
              f"  Regime: {len(g3b_s4.regime_log)} entries (signed).")
        for ev in g3b_s4.regime_log:
            dir_word = "quieter" if ev[3] > 0 else "louder"
            print(f"    REGIME block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  {ev[3]:+.3f} shells ({dir_word})")

    # ── H2-f regression: sixth confirmation ─────────────────────────────────
    print(f"\n{'='*96}")
    print("§3 H2-f REGRESSION (PHI-ZAKHOR ungated, sixth confirmation expected)")
    print(f"{'='*96}")
    print(f"  {'alpha':>8} | {'dir':>5} | {'T_meas':>8} | {'T_form':>8} | "
          f"{'f_shells':>10} | {'err_frac':>10} | verdict")
    h2f_ok = True
    for alpha_sw in ALPHA_SWEEP:
        G_sw, D_sw, nt_sw, _ = calibrate_exp6(alpha_sw, STD_PEAKED)
        for direction, fn_s, off_s in (("UP", _scales_step_up, 4),
                                       ("DN", _scales_step_down, 5)):
            cs_reg = _fresh_competitors_7b(G_sw, D_sw, nt_sw, alpha_sw)
            raw_reg = _run_7b(cs_reg, fn_s(), STD_PEAKED,
                              SEED_BASE + off_s + round(1 / alpha_sw))
            fc = h2_f_check(raw_reg, STEP_BLOCK, alpha_sw, direction)
            T_m, T_f = fc.get("T_measured"), fc.get("T_formula")
            ef, p = fc.get("error_frac"), fc.get("pass")
            if p is False:
                h2f_ok = False
            print(f"  {alpha_sw:>8.4f} | {direction:>5} | "
                  f"{str(T_m) if T_m is not None else '>N':>8} | "
                  f"{f'{T_f:.1f}' if T_f is not None else '—':>8} | "
                  f"{fc.get('f', 0):>10.4f} | "
                  f"{f'{ef:.3f}' if ef is not None else '—':>10} | "
                  f"{_pf(p) if p is not None else 'METRIC-DEFECT'}")
    verdicts["H2f-reg"] = _pf(h2f_ok)
    print(f"  H2-f regression (sixth confirmation): {verdicts['H2f-reg']}")

    # ── Verdict summary ──────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("VERDICT SUMMARY — exp007b")
    print(f"{'='*96}")
    print(f"  {'check':<32} {'peaked':>12} {'spread':>12}")
    for stem in ("regression", "H5a", "S4a-reg",
                 "H8a", "H8b", "H8ab", "H8c", "H8d", "H8",
                 "H9"):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<32} {vp:>12} {vs:>12}")
    print(f"  {'H2f-reg':32} {verdicts.get('H2f-reg', '—'):>12}")
    print()
    print(f"  {'H12b-coverage':32} "
          f"{verdicts.get(f'H12b-coverage-{STD_PEAKED}', '—'):>12} "
          f"{verdicts.get(f'H12b-coverage-{STD_SPREAD}', '—'):>12}")
    print(f"  {'H13-coverage':32} "
          f"{verdicts.get(f'H13-coverage-{STD_PEAKED}', '—'):>12} "
          f"{verdicts.get(f'H13-coverage-{STD_SPREAD}', '—'):>12}")
    print(f"  {'H14-S4':32} "
          f"{verdicts.get(f'H14-S4-{STD_PEAKED}', '—'):>12} "
          f"{verdicts.get(f'H14-S4-{STD_SPREAD}', '—'):>12}")
    print(f"  {'H14-S3':32} "
          f"{verdicts.get(f'H14-S3-{STD_PEAKED}', '—'):>12} "
          f"{verdicts.get(f'H14-S3-{STD_SPREAD}', '—'):>12}")
    print(f"  {'H14 overall':32} "
          f"{verdicts.get(f'H14-{STD_PEAKED}', '—'):>12} "
          f"{verdicts.get(f'H14-{STD_SPREAD}', '—'):>12}")

    # Overall claim verdicts
    h12b_pass = all(
        verdicts.get(f"H12b-coverage-{s}", "FALSIFIED") == "PASS"
        for s in (STD_PEAKED, STD_SPREAD)
    )
    h13_pass = all(
        verdicts.get(f"H13-coverage-{s}", "FALSIFIED") == "PASS"
        for s in (STD_PEAKED, STD_SPREAD)
    )
    h14_pass = all(
        verdicts.get(f"H14-{s}", "FALSIFIED") == "PASS"
        for s in (STD_PEAKED, STD_SPREAD)
    )
    verdicts["H12b"] = _pf(h12b_pass)
    verdicts["H13"] = _pf(h13_pass)
    verdicts["H14"] = _pf(h14_pass)
    print()
    print(f"  {'H12b (S4 coverage <2%)':32} {verdicts['H12b']:>12}")
    print(f"  {'H13 (S1 floor <0.5%)':32} {verdicts['H13']:>12}")
    print(f"  {'H14 (sensitivity=100%)':32} {verdicts['H14']:>12}")
    print()
    print("  H0-id: RETIRED (two-strike rule, exp004).")
    print("  H11: METRIC-DEFECT (exp007). Not retested.")
    print("  H10 metric family: RETIRED (METRIC-DEFECT, exp006).")
    print("  Verdicts: PASS / FALSIFIED / METRIC-DEFECT — no fourth category.")

    # ── §5 Closing clause ────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("§5 CLOSING CLAUSE — The follow-up permission does not renew.")
    print(f"{'='*96}")
    reg_stems = ["regression", "H5a", "S4a-reg", "H8a", "H8b", "H8c", "H8d", "H9"]
    regressions_pass = all(
        verdicts.get(f"{s}-{std}", verdicts.get(s, "FALSIFIED")) == "PASS"
        for s in reg_stems
        for std in (STD_PEAKED, STD_SPREAD)
        if f"{s}-{std}" in verdicts or s in verdicts
    )
    regressions_pass = regressions_pass and verdicts.get("H2f-reg", "FALSIFIED") == "PASS"

    all_claims_pass = h12b_pass and h13_pass and h14_pass and regressions_pass
    any_falsified = not all_claims_pass

    if all_claims_pass:
        print("  ALL CLAIMS PASS. Register enters Architecture Note 02 §1 (establishments).")
        print("  Experimental series CLOSES with a confirmation.")
        print("  Deliverable: Architecture Note 02.")
    else:
        failing_claims = []
        if not h12b_pass:
            failing_claims.append("H12-b (S4 coverage)")
        if not h13_pass:
            failing_claims.append("H13 (S1 noise floor)")
        if not h14_pass:
            failing_claims.append("H14 (sensitivity)")
        if not regressions_pass:
            failing_claims.append("regressions")
        print(f"  FALSIFIED claims: {failing_claims}")
        print("  Register enters Architecture Note 02 §2 (funerals and costs)")
        print("  with its measured numbers.")
        print("  Experimental series CLOSES. The follow-up permission does not renew.")
        print("  Deliverable: Architecture Note 02.")

    # ── Reproducibility ──────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("REPRODUCIBILITY")
    G_r, D_r, nt_r, _ = calibrate_exp6(ALPHA_PRIMARY, STD_PEAKED)
    rA = _all_runs_7b(G_r, D_r, nt_r)
    rB = _all_runs_7b(G_r, D_r, nt_r)
    hA, hB = hashlib.sha256(), hashlib.sha256()
    for k in sorted(rA):
        hA.update(_hash_raw_7b(rA[k]).encode())
        hB.update(_hash_raw_7b(rB[k]).encode())
    da, db = hA.hexdigest()[:16], hB.hexdigest()[:16]
    full_sha = hA.hexdigest()
    match = da == db
    print(f"  run1={da}  run2={db}  {_pf(match)} (bit-identical)")
    print(f"  SHA-256: {full_sha}")
    print()
    print("  Save dated output to research/results/exp007b_<YYYY-MM-DD>.txt.")


if __name__ == "__main__":
    main()
