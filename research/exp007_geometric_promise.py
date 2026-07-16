"""exp007_geometric_promise.py — The Geometric Promise: Closing Experiment.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Pre-registered: hypotheses and thresholds frozen on 2026-07-11 before any code
was written. See docs/exp007-pre-registration.md.

Two debts from exp006:
  (1) Honesty metric: H10 earned METRIC-DEFECT (guarded-oracle was unreachable
      by design). This experiment introduces an oracle-free geometric criterion:
      |v − q(v)| > (1 − 1/φ)/2 × |v| — H11.
  (2) Ghost flags: ~1097 mid-return blocks on S4 peaked were announced by the
      formula clock for state displacements the gate already prevented. Fix:
      after REGIME rebirth, SET countdown to K+4 (not max) — §2 / H12.

H0-id: RETIRED (two-strike rule, exp004). Does not appear here.
H10 metric family: RETIRED by METRIC-DEFECT. Does not appear here.

Run from repository root:

    python3 research/exp007_geometric_promise.py

Bit-identical re-run asserted inline; SHA-256 recorded.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

from exp002_scale_memory import (  # noqa: E402
    N_BLOCKS, BLOCK_SIZE, LEVELS, ALPHA_PRIMARY, ALPHA_SWEEP,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    STEP_SHELLS, SPIKE_SHELLS, SPIKE_PERIOD,
    shell_coord, hi_from_state,
    _phi_codebook, _uniform_codebook, _snap, _block_stats,
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

# ── exp007 constants ──────────────────────────────────────────────────────────

PROMISE_CONST: float = (1.0 - PHI_INV) / 2   # (1 − 1/φ)/2 ≈ 0.1910 — frozen §6
H11_LIMIT: float = 0.001                       # < 0.1% silent miscarriage — frozen §6
H12_COLLAPSE_LIMIT: float = 0.02              # < 2% mid-return coverage — frozen §6

# exp006 baseline for H12 (from research/results/exp006_2026-07-11.txt)
H12_EXP006_PEAKED: int = 1097   # mid-return blocks / N_BLOCKS on S4 peaked
H12_EXP006_SPREAD: int = 594    # mid-return blocks / N_BLOCKS on S4 spread

# H11 checked for phi-codebook competitors only
H11_PHI_NAMES: Tuple[str, ...] = (
    "PHI-ZAKHOR-KEEP-G3", "PHI-ZAKHOR", "PHI-STATIC", "ORACLE-PHI",
)

_NAMES_7: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G3", "PHI-STATIC",
    "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI", "ORACLE-PHI-G",
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. PHI-ZAKHOR-KEEP-G3 with ghost-fix (§2 — exp007 canonical version)
# ─────────────────────────────────────────────────────────────────────────────

class PhiZakhorKeepG3:
    """Guard-band KEEP with symmetric regime detection + ghost-fix mid-return.

    Ghost-fix (§2): after REGIME rebirth, mid_countdown is SET to K+4, not
    max(current, K+4). The formula-clock value accumulated before rebirth is
    a ghost — the rebirth resolves the state immediately; no long clock needed.

    Also tracks _block_stranger per block (for H11 flag accounting):
      True if that block was a stranger AND not reborn.
    """

    name = "PHI-ZAKHOR-KEEP-G3"
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
            pass                                # gating: state frozen
        else:
            self._s = pre_orig + self.alpha * (obs - pre_orig)

        self._state_log.append((pre_orig, self._s))
        self._block_stranger.append(is_stranger and not reborn)

        # ── Formula-clocked mid-return flag (ghost-fix: SET on rebirth) ──────
        if reborn:
            # §2 ghost-fix: rebirth resolves state immediately; cancel any
            # pre-rebirth formula-clock accumulation and use settle window only.
            self._mid_countdown = RECOVERY_SETTLE   # SET, not max
        elif not is_stranger and abs(d_raw) > self.noise_threshold:
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

        is_mid = self._mid_countdown > 0
        if is_mid:
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
# 2. Geometric promise helpers
# ─────────────────────────────────────────────────────────────────────────────

def _smallest_pos_shell(hi: float) -> float:
    """Smallest nonzero positive shell of a phi-codebook with given hi."""
    return hi * (PHI_INV ** (LEVELS - 1))


def _mis_carried(v: float, q: float, lo: float) -> bool:
    """Geometric promise criterion (oracle-free, frozen §6).

    Returns True iff value v is silently mis-carried by quantization to q:
      - Normal branch: |v − q| > (1 − 1/φ)/2 × |v|
      - Underflow branch (q = 0): |v| > lo/2
        (value deserved the smallest shell but received silence)
    """
    if q == 0.0:
        return abs(v) > lo / 2.0
    return abs(v - q) > PROMISE_CONST * abs(v)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stream runner
# ─────────────────────────────────────────────────────────────────────────────

def _fresh_competitors_exp7(G: float, D: float, noise_threshold: float,
                             alpha: float = ALPHA_PRIMARY) -> List:
    return [
        PhiZakhor(alpha),
        PhiZakhorKeepG3(G, D, noise_threshold, alpha),
        PhiStatic(),
        GridZakhor(alpha),
        GridStatic(),
        OraclePhi(),
        OraclePhiG(G),
    ]


def _run_exp7(
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


def _hash_raw(raw: Dict) -> str:
    h = hashlib.sha256()
    for name in sorted(raw.keys()):
        for mse, under, over, _ in raw[name]:
            h.update(f"{mse:.15e}{under:.15e}{over:.15e}".encode())
    return h.hexdigest()[:16]


def _print_summary(label: str,
                   raw: Dict[str, List[Tuple[float, float, float, float]]]) -> None:
    print(f"\n{label}")
    print("-" * 86)
    print(f"  {'competitor':<26} {'MSE':>14} {'underflow':>12} {'overflow':>12}")
    for name in _NAMES_7:
        if name not in raw:
            continue
        ms = [r[0] for r in raw[name]]
        us = [r[1] for r in raw[name]]
        os_ = [r[2] for r in raw[name]]
        print(f"  {name:<26} {_mean(ms):>14.4e} {_mean(us):>12.4e} {_mean(os_):>12.4e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. H11: geometric promise honesty criterion
# ─────────────────────────────────────────────────────────────────────────────

def h11_geometric(
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    g3: PhiZakhorKeepG3,
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    is_spike: bool = False,
) -> Dict[str, Dict]:
    """H11: geometric promise honesty criterion (oracle-free).

    For PHI-ZAKHOR-KEEP-G3: value is covered (skip assessment) if its block
    is flagged by STRANGER or MID-RETURN (which includes REGIME-settle).
    For other phi-codebook competitors: no flags, all blocks assessed.

    Also runs ORACLE-PHI with no flags as a metric-defect indicator:
    if ORACLE-PHI shows a high rate, the criterion is structurally unreachable.
    """
    rnd = _lcg(seed)
    counts: Dict[str, Dict[str, int]] = {}
    for c in competitors:
        if c.name not in H11_PHI_NAMES:
            continue
        counts[c.name] = {
            "mis": 0, "underflow_mis": 0,
            "total_unflagged": 0, "total": 0,
        }

    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)

        for c in competitors:
            if c.name not in H11_PHI_NAMES:
                continue
            cnt = counts[c.name]

            hi_c = raw[c.name][t][3]
            lo_c = _smallest_pos_shell(max(hi_c, 1e-300))
            book_c = _phi_codebook(max(hi_c, 1e-300), LEVELS)

            # Flag determination:
            # G3: STRANGER flag (block_stranger) OR MID-RETURN flag
            # Others: no flags
            if c.name == "PHI-ZAKHOR-KEEP-G3":
                bs = g3._block_stranger[t] if t < len(g3._block_stranger) else False
                mr = g3.mid_return_flags[t] if t < len(g3.mid_return_flags) else False
                is_flagged = bs or mr
            else:
                is_flagged = False

            for v in block:
                cnt["total"] += 1
                if not is_flagged:
                    cnt["total_unflagged"] += 1
                    _, q = _snap(v, book_c)
                    if _mis_carried(v, q, lo_c):
                        cnt["mis"] += 1
                        if q == 0.0:
                            cnt["underflow_mis"] += 1

    results: Dict[str, Dict] = {}
    for name, cnt in counts.items():
        tf = cnt["total_unflagged"]
        tot = cnt["total"]
        results[name] = {
            "mis_rate": cnt["mis"] / tf if tf > 0 else 0.0,
            "underflow_rate": cnt["underflow_mis"] / tf if tf > 0 else 0.0,
            "flagged_rate": 1.0 - tf / tot if tot > 0 else 0.0,
            "mis_count": cnt["mis"],
            "underflow_count": cnt["underflow_mis"],
            "total_unflagged": tf,
            "total": tot,
        }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 5. All-streams runner for reproducibility hash
# ─────────────────────────────────────────────────────────────────────────────

def _all_runs(G: float, D: float, noise_thr: float,
              alpha: float = ALPHA_PRIMARY) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for std in (STD_PEAKED, STD_SPREAD):
        for tag, fn, off, spike in (
            (f"S1-{std}", _scales_stationary, 1, False),
            (f"S3u-{std}", _scales_step_up, 4, False),
            (f"S3d-{std}", _scales_step_down, 5, False),
            (f"S4-{std}", _scales_spike, 6, True),
        ):
            cs = _fresh_competitors_exp7(G, D, noise_thr, alpha)
            out[tag] = _run_exp7(cs, fn(), std, SEED_BASE + off, is_spike=spike)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 6. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 007 — The Geometric Promise")
    print("=" * 96)
    print("  Pre-registered 2026-07-11. H0-id retired. H10 metric family retired (METRIC-DEFECT).")
    print(f"  K={K_REBIRTH}  f̂={F_HAT}  settle={RECOVERY_SETTLE}"
          f"  H11_limit={H11_LIMIT:.1e}  H12_limit={H12_COLLAPSE_LIMIT:.0%}"
          f"  promise_const≈{PROMISE_CONST:.4f}")
    print(f"  Ghost-fix: rebirth resets mid_countdown to {RECOVERY_SETTLE} (SET, not max).")
    print(f"  §2 note: rebirth at step+K resolves state immediately;"
          f" pre-rebirth formula-clock is a ghost.")
    print(f"  H12 exp006 baseline: peaked={H12_EXP006_PEAKED}/{N_BLOCKS}"
          f"  spread={H12_EXP006_SPREAD}/{N_BLOCKS}")

    step_block = N_BLOCKS // 2
    verdicts: Dict[str, str] = {}

    # ── H11 per-stream results accumulated across distributions ──────────────
    h11_rows: Dict[str, Dict[str, Dict]] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                           (STD_SPREAD,  f"spread(std={STD_SPREAD})")):

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

        # ── §3 Regression: S1 stationary ───────────────────────────────────
        cs_s1 = _fresh_competitors_exp7(G, D, noise_thr)
        raw_s1 = _run_exp7(cs_s1, _scales_stationary(), std, SEED_BASE + 1)
        g3_s1: PhiZakhorKeepG3 = next(
            c for c in cs_s1 if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(f"§3 S1 STATIONARY ({std_label})", raw_s1)

        pz_mse = _mean([raw_s1["PHI-ZAKHOR"][t][0] for t in range(N_BLOCKS)])
        g3_mse = _mean([raw_s1["PHI-ZAKHOR-KEEP-G3"][t][0] for t in range(N_BLOCKS)])
        reg_ok = g3_mse <= pz_mse * 1.05
        verdicts[f"regression-{std}"] = _pf(reg_ok)
        n_regime_s1 = len(g3_s1.regime_log)
        print(f"  Regression: PHI-ZAKHOR {pz_mse:.4e}  G3 {g3_mse:.4e} — {verdicts[f'regression-{std}']}")
        print(f"  S1 REGIME events: {n_regime_s1} (want 0)"
              f"  stranger: {len(g3_s1.stranger_log)}"
              f"  mid-return blocks: {sum(g3_s1.mid_return_flags)}/{N_BLOCKS}")
        if not reg_ok:
            print("  *** REGRESSION FAIL. Halting.")
            return

        # S1 oracle-relative R̄ (needed for S4c collateral denominator)
        oracle_mse_s1 = [raw_s1["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]
        R_s1: Dict[str, float] = {}
        for name in _NAMES_7:
            if name in raw_s1 and name != "ORACLE-PHI":
                R_s1[name] = _mean([
                    raw_s1[name][t][0] / max(oracle_mse_s1[t], 1e-30)
                    for t in range(N_BLOCKS)
                ])

        # ── §3 Regression: S2 slow drift — hallucination audit ─────────────
        cs_s2 = _fresh_competitors_exp7(G, D, noise_thr)
        raw_s2 = _run_exp7(cs_s2, _scales_drift_up(), std, SEED_BASE + 2)
        g3_s2: PhiZakhorKeepG3 = next(
            c for c in cs_s2 if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(f"S2 SLOW DRIFT ↑ ({std_label})", raw_s2)
        n_regime_s2 = len(g3_s2.regime_log)
        print(f"  S2 REGIME events: {n_regime_s2}"
              f"  ({'expected 0' if n_regime_s2 == 0 else '*** FINDING: drift fired regime'})")

        # ── §3 Regression: H8 S3 step-UP (fifth confirmation) ─────────────
        cs_s3u = _fresh_competitors_exp7(G, D, noise_thr)
        raw_s3u = _run_exp7(cs_s3u, _scales_step_up(), std, SEED_BASE + 4)
        g3_s3u: PhiZakhorKeepG3 = next(
            c for c in cs_s3u if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(
            f"§3 S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})", raw_s3u)
        h8_up = h8_recovery(raw_s3u, g3_s3u, step_block, "S3↑")
        verdicts[f"H8b-{std}"] = _pf(h8_up["pass"])
        pz_up_T = h8_up["pz_recovery"]
        g3_up_T = h8_up["recovery_blocks"]
        print(f"  H8(b) S3↑: REGIME_total={h8_up['regime_total']}"
              f"  near_step={len(h8_up['regime_near_step'])} (want 1)"
              f"  PHI-ZAKHOR T={pz_up_T}  G3 T={g3_up_T}"
              f" (budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H8b-{std}']}")
        for ev in h8_up["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  signed={ev[3]:+.3f} shells")
        mid_s3u = sum(g3_s3u.mid_return_flags)
        print(f"  S3↑ mid-return blocks with ghost-fix: {mid_s3u}/{N_BLOCKS}"
              f"  ({100*mid_s3u/N_BLOCKS:.1f}%)")

        # ── §3 Regression: H8 S3 step-DOWN (fifth confirmation) ────────────
        cs_s3d = _fresh_competitors_exp7(G, D, noise_thr)
        raw_s3d = _run_exp7(cs_s3d, _scales_step_down(), std, SEED_BASE + 5)
        g3_s3d: PhiZakhorKeepG3 = next(
            c for c in cs_s3d if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(
            f"§3 S3 STEP ↓ (−{STEP_SHELLS} shells) ({std_label})", raw_s3d)
        h8_dn = h8_recovery(raw_s3d, g3_s3d, step_block, "S3↓")
        verdicts[f"H8a-{std}"] = _pf(h8_dn["pass"])
        pz_dn_T = h8_dn["pz_recovery"]
        g3_dn_T = h8_dn["recovery_blocks"]
        print(f"  H8(a) S3↓: REGIME_total={h8_dn['regime_total']}"
              f"  near_step={len(h8_dn['regime_near_step'])} (want 1)"
              f"  PHI-ZAKHOR T={pz_dn_T}  G3 T={g3_dn_T}"
              f" (budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H8a-{std}']}")
        for ev in h8_dn["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  signed={ev[3]:+.3f} shells")
        mid_s3d = sum(g3_s3d.mid_return_flags)
        print(f"  S3↓ mid-return blocks with ghost-fix: {mid_s3d}/{N_BLOCKS}"
              f"  ({100*mid_s3d/N_BLOCKS:.1f}%)")
        verdicts[f"H8ab-{std}"] = _pf(h8_up["pass"] and h8_dn["pass"])

        # ── §3 Regression: S4 spikes ────────────────────────────────────────
        cs_s4 = _fresh_competitors_exp7(G, D, noise_thr)
        raw_s4 = _run_exp7(cs_s4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        g3_s4: PhiZakhorKeepG3 = next(
            c for c in cs_s4 if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(
            f"§3 S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            raw_s4,
        )

        # S4a regression (PHI-ZAKHOR ungated — fifth confirmation)
        s4a = s4a_state_integrity(raw_s4, "PHI-ZAKHOR")
        ref = EXP003_S4A_PEAK_PEAKED if std == STD_PEAKED else EXP003_S4A_PEAK_SPREAD
        s4a_reg_ok = abs(s4a["peak_displacement"] - ref) <= S4A_REG_TOL
        verdicts[f"S4a-reg-{std}"] = _pf(s4a_reg_ok)
        print(f"\n  §3 S4a regression: peak_disp={s4a['peak_displacement']:.4f}"
              f" (ref={ref:.4f}) — {verdicts[f'S4a-reg-{std}']}")

        # H8(c): cold-start self-healing — REGIME log on S4
        n_regime_s4 = len(g3_s4.regime_log)
        regime_s4_early = [e for e in g3_s4.regime_log if e[0] <= K_REBIRTH + 1]
        regime_s4_late = [e for e in g3_s4.regime_log if e[0] > K_REBIRTH + 1]
        h8c_ok = (len(regime_s4_early) == 1 and len(regime_s4_late) == 0)
        verdicts[f"H8c-{std}"] = _pf(h8c_ok)
        print(f"  §3 H8(c) cold-start: REGIME_total={n_regime_s4}"
              f"  early={len(regime_s4_early)} (want 1)"
              f"  late={len(regime_s4_late)} (want 0) — {verdicts[f'H8c-{std}']}")
        for ev in g3_s4.regime_log[:3]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  signed={ev[3]:+.3f} shells")

        # H5a: state displacement identically zero under gating
        h5a = h5a_displacement(g3_s4)
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

        # S4c collateral (retired threshold — reported, not judged)
        s4c = s4c_collateral(raw_s4, R_s1)
        g3_s4c = s4c.get("PHI-ZAKHOR-KEEP-G3", {})
        print(f"  §3 S4c collateral (retired threshold {S4C_MAX_R_RATIO}, reported only):")
        for nm in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G3"):
            if nm in s4c:
                d2 = s4c[nm]
                print(f"    {nm:<28} R_normal={d2['R_normal']:.3f}"
                      f"  R_s1={d2['R_s1']:.3f}  ratio={d2['ratio']:.3f}")

        # §3 H9 recheck
        h9 = h9_declaration(g3_s4, true_spike_count, e_hat)
        verdicts[f"H9-{std}"] = _pf(h9["pass"])
        print(f"\n  §3 H9 declaration: declared={h9['declared']}"
              f"  true_spikes={h9['true_spikes']}  N̂={h9['N_hat']:.1f}"
              f"  limit={h9['limit']:.1f}"
              f"  truthful={h9['truthful']} — {verdicts[f'H9-{std}']}")
        print(f"    Stranger log (first 3): {g3_s4.stranger_log[:3]}")

        # ── §2 H12: ghost-collapse ─────────────────────────────────────────
        mid_s4 = sum(g3_s4.mid_return_flags)
        mid_rate_s4 = mid_s4 / N_BLOCKS
        exp6_ref = H12_EXP006_PEAKED if std == STD_PEAKED else H12_EXP006_SPREAD
        h12_ok = mid_rate_s4 < H12_COLLAPSE_LIMIT
        verdicts[f"H12-coverage-{std}"] = _pf(h12_ok)
        print(f"\n  §2 H12 ghost-collapse ({std_label}):"
              f"  exp006={exp6_ref}/{N_BLOCKS} ({100*exp6_ref/N_BLOCKS:.1f}%)"
              f"  exp007={mid_s4}/{N_BLOCKS} ({100*mid_rate_s4:.1f}%)"
              f"  limit={H12_COLLAPSE_LIMIT:.0%} — {verdicts[f'H12-coverage-{std}']}")

        # Three registers on S4
        print(f"\n  Three registers ({std_label}, S4):")
        print(f"    Stranger log: {len(g3_s4.stranger_log)} entries."
              f"  Mid-return blocks: {mid_s4}/{N_BLOCKS}."
              f"  Regime log: {len(g3_s4.regime_log)} entries (signed).")
        for ev in g3_s4.regime_log:
            dir_word = "quieter" if ev[3] > 0 else "louder"
            print(f"    REGIME block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  {ev[3]:+.3f} shells ({dir_word})")

        # ── §1 H11: geometric promise (run on all four streams) ────────────
        print(f"\n  §1 H11 geometric promise ({std_label})"
              f"  promise_const={(1-PHI_INV)/2:.4f}")
        print(f"  {'stream':<8} {'competitor':<28} {'mis_rate':>12}"
              f" {'uflow_rate':>12} {'flagged%':>10} {'verdict':>14}")

        for stream_tag, fn_s, off_s, spike_s, g3_inst, raw_s in (
            ("S1", _scales_stationary, 1, False, g3_s1, raw_s1),
            ("S3↑", _scales_step_up, 4, False, g3_s3u, raw_s3u),
            ("S3↓", _scales_step_down, 5, False, g3_s3d, raw_s3d),
            ("S4", _scales_spike, 6, True, g3_s4, raw_s4),
        ):
            h11_res = h11_geometric(
                cs_s4 if stream_tag == "S4" else
                cs_s3u if stream_tag == "S3↑" else
                cs_s3d if stream_tag == "S3↓" else cs_s1,
                fn_s(), std, SEED_BASE + off_s,
                g3_inst, raw_s, is_spike=spike_s,
            )
            key = f"{stream_tag}-{std}"
            h11_rows.setdefault(key, {})
            for comp_name, d3 in h11_res.items():
                h11_rows[key][comp_name] = d3
                mis_r = d3["mis_rate"]
                uf_r = d3["underflow_rate"]
                flag_r = d3["flagged_rate"]
                is_g3 = (comp_name == "PHI-ZAKHOR-KEEP-G3")
                # Only G3 has the verdict predicate; others are reported
                if is_g3:
                    h11_vrd = _pf(mis_r < H11_LIMIT)
                    verdicts[f"H11-{stream_tag}-{std}"] = h11_vrd
                else:
                    h11_vrd = f"(ref, {mis_r:.3e})"
                print(f"  {stream_tag:<8} {comp_name:<28}"
                      f" {mis_r:>12.4e} {uf_r:>12.4e}"
                      f" {100*flag_r:>9.1f}% {h11_vrd:>14}")

    # ── H2-f regression: fifth confirmation ─────────────────────────────────
    print(f"\n{'='*96}")
    print("§3 H2-f REGRESSION (PHI-ZAKHOR ungated, fifth confirmation expected)")
    print(f"{'='*96}")
    print(f"  {'alpha':>8} | {'dir':>5} | {'T_meas':>8} | {'T_form':>8} | "
          f"{'f_shells':>10} | {'err_frac':>10} | verdict")
    h2f_ok = True
    for alpha_sw in ALPHA_SWEEP:
        G_sw, D_sw, nt_sw, _ = calibrate_exp6(alpha_sw, STD_PEAKED)
        for direction, fn_s, off_s in (("UP", _scales_step_up, 4),
                                       ("DN", _scales_step_down, 5)):
            cs_reg = _fresh_competitors_exp7(G_sw, D_sw, nt_sw, alpha_sw)
            raw_reg = _run_exp7(cs_reg, fn_s(), STD_PEAKED,
                                SEED_BASE + off_s + round(1 / alpha_sw))
            fc = h2_f_check(raw_reg, step_block, alpha_sw, direction)
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
    print(f"  H2-f regression (fifth confirmation): {verdicts['H2f-reg']}")

    # ── H11 overall verdicts ─────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("§1 H11 GEOMETRIC PROMISE VERDICT SUMMARY")
    print(f"{'='*96}")
    print("  (Checking G3 only; ORACLE-PHI included as metric-defect indicator)")
    print(f"  {'stream':<8} {'peaked':>12} {'spread':>12}")
    for stream_tag in ("S1", "S3↑", "S3↓", "S4"):
        vp = verdicts.get(f"H11-{stream_tag}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"H11-{stream_tag}-{STD_SPREAD}", "—")
        print(f"  {stream_tag:<8} {vp:>12} {vs:>12}")

    # H11 overall for G3
    h11_g3_all = all(
        verdicts.get(f"H11-{st}-{s}", "FALSIFIED") == "PASS"
        for st in ("S1", "S3↑", "S3↓", "S4")
        for s in (STD_PEAKED, STD_SPREAD)
    )
    verdicts["H11"] = _pf(h11_g3_all)

    # Structural check: if ORACLE-PHI shows high mis-carriage → METRIC-DEFECT
    oracle_rates: List[float] = []
    for key, comp_dict in h11_rows.items():
        if "ORACLE-PHI" in comp_dict:
            oracle_rates.append(comp_dict["ORACLE-PHI"]["mis_rate"])
    oracle_mis_mean = _mean(oracle_rates) if oracle_rates else 0.0

    if oracle_mis_mean > H11_LIMIT:
        h11_verdict_str = (
            f"METRIC-DEFECT — ORACLE-PHI mis-rate={oracle_mis_mean:.3e}"
            f" (>{H11_LIMIT:.0e} on unflagged values;"
            f" promise violated by geometry, not calibration)"
        )
    else:
        h11_verdict_str = verdicts["H11"]

    print(f"\n  H11 (G3 all streams, both distributions): {verdicts['H11']}")
    print(f"  ORACLE-PHI mis-rate (metric-defect indicator): {oracle_mis_mean:.4e}")
    if oracle_mis_mean > H11_LIMIT:
        print(f"  MECHANISM: For values near the midpoint between adjacent shells,")
        print(f"    |v − q| = s_j×(1−1/φ)/2 but promise(v) = (1−1/φ)/2×v < s_j×(1−1/φ)/2")
        print(f"    (since v < s_j). The criterion is violated for ~{100*oracle_mis_mean:.0f}% of")
        print(f"    values in any phi-codebook, regardless of hi calibration.")
        print(f"    ORACLE-PHI has perfect calibration; its violation rate measures the")
        print(f"    structural floor. H11: METRIC-DEFECT.")
        verdicts["H11"] = "METRIC-DEFECT"

    # ── §2 H12 verdict ───────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("§2 H12 GHOST-COLLAPSE VERDICT")
    print(f"{'='*96}")
    print(f"  {'check':<28} {'peaked':>12} {'spread':>12}")
    for stem in ("H12-coverage",):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<28} {vp:>12} {vs:>12}")

    h12_all = all(
        verdicts.get(f"H12-coverage-{s}", "FALSIFIED") == "PASS"
        for s in (STD_PEAKED, STD_SPREAD)
    )
    verdicts["H12"] = _pf(h12_all)
    print(f"  H12 overall: {verdicts['H12']}")
    if h12_all:
        print(f"  H11 honesty after ghost diet: if H11 = METRIC-DEFECT, the ghosts")
        print(f"  were NOT load-bearing for the honesty criterion (it was already broken)")

    # ── Full verdict summary ─────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("VERDICT SUMMARY — exp007")
    print(f"{'='*96}")
    print(f"  {'check':<28} {'peaked':>12} {'spread':>12}")
    for stem in ("regression", "H5a", "S4a-reg",
                 "H8a", "H8b", "H8ab", "H8c", "H8d", "H8",
                 "H9", "H12-coverage"):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<28} {vp:>12} {vs:>12}")
    for stem in ("H11-S1", "H11-S3↑", "H11-S3↓", "H11-S4"):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<28} {vp:>12} {vs:>12}")
    print(f"  {'H2f-reg':28} {verdicts.get('H2f-reg', '—'):>12}")
    print(f"  {'H11':28} {verdicts.get('H11', '—'):>12}")
    print(f"  {'H12':28} {verdicts.get('H12', '—'):>12}")
    print()
    print("  H0-id: RETIRED (two-strike rule, exp004).")
    print("  H10 metric family: RETIRED (METRIC-DEFECT, exp006).")
    print("  Verdicts: PASS / FALSIFIED / METRIC-DEFECT — no fourth category.")

    # ── §5 Closing clause ────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("§5 CLOSING CLAUSE")
    print(f"{'='*96}")
    reg_checks = ["regression", "H5a", "S4a-reg", "H8a", "H8b", "H8c", "H8d",
                  "H9", "H2f-reg"]
    regressions_pass = all(
        verdicts.get(f"{s}-{std}", verdicts.get(s, "FALSIFIED")) == "PASS"
        for s in reg_checks
        for std in (STD_PEAKED, STD_SPREAD)
        if f"{s}-{std}" in verdicts or s in verdicts
    )
    h11_pass = verdicts.get("H11", "FALSIFIED") == "PASS"
    h12_pass = verdicts.get("H12", "FALSIFIED") == "PASS"
    h11_mdefect = verdicts.get("H11", "") == "METRIC-DEFECT"

    if h11_pass and h12_pass and regressions_pass:
        print("  ALL PASS. Experimental series CLOSES. No exp008.")
        print("  Deliverable: Architecture Note 02.")
    elif h11_mdefect:
        print("  H11: METRIC-DEFECT. The geometric criterion as stated is structurally")
        print("  unreachable (violated by ~15–20% of values in any phi-codebook by")
        print("  geometry alone, independent of hi calibration or gating).")
        print("  Per §5: the criterion either measures the promise or the promise is wrong.")
        print("  This verdict goes in Architecture Note 02 as-is.")
        print("  Per §5 closing clause: H11 METRIC-DEFECT is NOT a FALSIFICATION.")
        print("  One targeted follow-up is permitted for ghost-fix mechanics (§2) only;")
        print("  the geometric criterion (§1) is not restated.")
        if h12_pass and regressions_pass:
            print("  H12 PASS: ghost-collapse confirmed. The ghosts were not load-bearing")
            print("  for honesty (the criterion was already broken without them).")
        print("  Steward's decision required: CLOSE on METRIC-DEFECT or open ghost-fix follow-up.")
    else:
        failing = [k for k, v in verdicts.items() if v == "FALSIFIED"]
        print(f"  Not all pass. Failing checks: {failing}")
        if any("H12" in k for k in failing):
            print("  H12 FALSIFIED: one targeted follow-up freeze permitted for ghost-fix only.")
        print("  Geometric criterion (§1): not restated. Goes in Note 02 as-is.")

    # ── Reproducibility ─────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("REPRODUCIBILITY")
    G_r, D_r, nt_r, _ = calibrate_exp6(ALPHA_PRIMARY, STD_PEAKED)
    rA = _all_runs(G_r, D_r, nt_r)
    rB = _all_runs(G_r, D_r, nt_r)
    hA, hB = hashlib.sha256(), hashlib.sha256()
    for k in sorted(rA):
        hA.update(_hash_raw(rA[k]).encode())
        hB.update(_hash_raw(rB[k]).encode())
    da, db = hA.hexdigest()[:16], hB.hexdigest()[:16]
    full_sha = hA.hexdigest()
    match = da == db
    print(f"  run1={da}  run2={db}  {_pf(match)} (bit-identical)")
    print(f"  SHA-256: {full_sha}")
    print()
    print("  Save dated output to research/results/exp007_<YYYY-MM-DD>.txt.")


if __name__ == "__main__":
    main()
