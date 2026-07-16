"""exp005_gated_rebirth.py — Logged, Not Remembered — and Kept Alive.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Pre-registered: hypotheses and thresholds frozen on 2026-07-11 before any code
was written. See docs/exp005-pre-registration.md.

Addresses exp004's root cause: declared strangers still contributed their alpha
step to the state. Two fixes tested:

  §1  Stranger-gated state: no update when block max is a stranger.
  §2  Regime rebirth (K=3): K consecutive strangers → re-seed state, log REGIME.
  §3  Formula-clocked confidence: T_flag = ceil(ln(Δ_est/f̂)/alpha); f̂=0.7 frozen.

H0-id is retired per the two-strike rule executed in exp004 and does not appear.

Run from repository root:

    python3 research/exp005_gated_rebirth.py

Bit-identical re-run asserted inline.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

# ── path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

from exp002_scale_memory import (  # noqa: E402
    N_BLOCKS, BLOCK_SIZE, LEVELS, ALPHA_PRIMARY, ALPHA_SWEEP,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    STEP_SHELLS, SPIKE_SHELLS, SPIKE_PERIOD,
    _LOG_PHI_INV, shell_coord, hi_from_state,
    _phi_codebook, _uniform_codebook, _snap, _block_stats,
    ZakhorScale, PhiZakhor, PhiStatic, GridZakhor, GridStatic, OraclePhi,
    _scales_stationary, _scales_drift_up, _scales_drift_down,
    _scales_step_up, _scales_step_down, _scales_spike,
    _mean, _phi_shell_exp,
)
from exp003_identity_recovery import (  # noqa: E402
    h2_r_recovery, s4a_state_integrity, s4b_spike_fidelity, s4c_collateral,
    SPIKE_TRUE_FRAC, H3_SILENT_THRESHOLD, H3_MAX_DECL_MULTIPLE, S4C_MAX_R_RATIO,
    _pf,
)
from exp004_guard_and_return import (  # noqa: E402
    calibrate, _percentile, h2_f_check, CAL_BLOCKS, CAL_SEED,
    H2F_TOLERANCE, H4_OVERFLOW_LIMIT,
    EXP003_S4A_PEAK_PEAKED, EXP003_S4A_PEAK_SPREAD,
)
from core.phi_theory import PHI, PHI_INV
from core.phi_theory import _clipped_gauss, _lcg

# ── exp005 constants ──────────────────────────────────────────────────────────

K_REBIRTH: int = 3          # consecutive stranger blocks to trigger regime rebirth
F_HAT: float = 0.7          # fixed f̂ shell residual (exp004 measured 0.62–0.79)
RECOVERY_SETTLE: int = K_REBIRTH + 4   # = 7 mid-return blocks after REGIME rebirth
H6_RECOVERY_BUDGET: int = K_REBIRTH + 8   # = 11 blocks for H6 recovery claim
H7_SILENT_LIMIT: float = 0.001    # < 0.1%
S4A_REG_TOL: float = 0.02
H5_DISP_LIMIT: float = 0.01      # state displacement per gated spike ≤ 0.01 shells
H5_DECL_MULT: float = H3_MAX_DECL_MULTIPLE

_NAMES_5: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G2", "PHI-STATIC",
    "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI",
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Calibration (exp005 noise_threshold = p95(|delta|), no 4× multiplier)
# ─────────────────────────────────────────────────────────────────────────────

def calibrate_exp5(alpha: float = ALPHA_PRIMARY, std: float = STD_PEAKED
                   ) -> Tuple[float, float]:
    """Derive G (guard band) and noise_threshold (p95 of |delta|, no 4×).

    G: same exp004 rule — max(1, ceil(p99(d+))).
    noise_threshold: p95(|delta|) — formula-clocked flag fires when |delta| > this.
    """
    zs = ZakhorScale(alpha)
    rnd = _lcg(CAL_SEED)
    d_plus: List[float] = []
    abs_delta: List[float] = []

    for t in range(CAL_BLOCKS):
        block = [_clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        max_mag = max(abs(v) for v in block)
        obs = shell_coord(max_mag) if max_mag > 1e-300 else 0.0
        pre = zs.observe(block)
        if t == 0:
            continue
        delta = obs - pre
        d_plus.append(max(0.0, delta))
        abs_delta.append(abs(delta))

    G = max(1.0, math.ceil(_percentile(d_plus, 0.99)))
    noise_threshold = _percentile(abs_delta, 0.95)   # no 4× multiplier
    return G, noise_threshold


# ─────────────────────────────────────────────────────────────────────────────
# 2. PHI-ZAKHOR-KEEP-G2: gated state + regime rebirth + formula-clocked flags
# ─────────────────────────────────────────────────────────────────────────────

class PhiZakhorKeepG2:
    """Guard-band KEEP with stranger-gated state and regime rebirth.

    State update rule:
      - Non-stranger block: normal alpha update (causal pre-update read).
      - Stranger block (max > hi_effective): NO state update; persistence += 1.
      - K consecutive strangers: REGIME rebirth (state ← obs, counter reset, logged).

    Mid-return flag (formula-clocked):
      - Fires on non-stranger blocks where |delta| > noise_threshold, for
        T_flag = max(K, ceil(ln(Δ_est / f̂) / alpha)) blocks (minimum K).
      - After REGIME rebirth: T_flag = K + 4 (settle window).

    Three registers:
      stranger_log:  (block_idx, shell_coord, overshoot×)
      mid_return_flags: List[bool] per block
      regime_log:    (block_idx, old_state, new_state, shells_jumped)
    """

    name = "PHI-ZAKHOR-KEEP-G2"
    is_phi = True

    def __init__(self, G: float, noise_threshold: float,
                 alpha: float = ALPHA_PRIMARY) -> None:
        self.G = G
        self.noise_threshold = noise_threshold
        self.alpha = alpha

        self._s: float = 0.0
        self._ready: bool = False
        self._persistence: int = 0
        self._mid_countdown: int = 0

        self._block_idx: int = 0
        self._total_values: int = 0
        self._declared_count: int = 0

        self.stranger_log: List[Tuple[int, float, float]] = []
        self.mid_return_flags: List[bool] = []
        self.regime_log: List[Tuple[int, float, float, float]] = []
        self._state_log: List[Tuple[float, float]] = []  # (pre_original, post)

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        self._block_idx += 1
        max_mag = max(abs(v) for v in block) if block else 0.0
        obs = shell_coord(max_mag) if max_mag > 1e-300 else 0.0

        # ── Cold-start ────────────────────────────────────────────────────────
        if not self._ready:
            self._s = obs
            self._ready = True
            pre_orig = obs
        else:
            pre_orig = self._s

        hi = hi_from_state(pre_orig - self.G)
        is_stranger = max_mag > hi
        reborn = False

        # ── Gating and rebirth ────────────────────────────────────────────────
        if is_stranger:
            self._persistence += 1
            if self._persistence >= K_REBIRTH:
                old_state = self._s
                self._s = obs            # re-seed from current obs
                shells_jumped = abs(obs - old_state)
                self._persistence = 0
                self.regime_log.append(
                    (self._block_idx, old_state, obs, shells_jumped)
                )
                reborn = True
                hi = hi_from_state(obs - self.G)  # recompute with new state
                is_stranger = max_mag > hi         # always False after rebirth
            # else: state frozen
        else:
            self._persistence = 0
            self._s = pre_orig + self.alpha * (obs - pre_orig)  # normal update

        post_state = self._s
        self._state_log.append((pre_orig, post_state))

        # ── Formula-clocked mid-return flag ───────────────────────────────────
        delta = obs - pre_orig   # always vs original pre (before rebirth)
        if reborn:
            T_flag = RECOVERY_SETTLE   # K + 4 = 7
            self._mid_countdown = max(self._mid_countdown, T_flag)
        elif not is_stranger and abs(delta) > self.noise_threshold:
            Δ_est = max(abs(delta), 1e-6)
            if Δ_est > F_HAT:
                try:
                    T_flag = max(K_REBIRTH,
                                 math.ceil(math.log(Δ_est / F_HAT) / self.alpha))
                except (ValueError, OverflowError):
                    T_flag = K_REBIRTH
            else:
                T_flag = K_REBIRTH
            self._mid_countdown = max(self._mid_countdown, T_flag)

        is_mid = self._mid_countdown > 0
        if is_mid:
            self._mid_countdown -= 1
        self.mid_return_flags.append(is_mid)

        # ── Quantize ──────────────────────────────────────────────────────────
        book = _phi_codebook(hi, LEVELS)
        normal: List[float] = []
        for v in block:
            self._total_values += 1
            if is_stranger and abs(v) > hi:
                self._declared_count += 1
                self.stranger_log.append(
                    (self._block_idx, shell_coord(abs(v)), abs(v) / hi - 1.0)
                )
            else:
                normal.append(v)

        mse, under, over = _block_stats(normal, book) if normal else (0.0, 0.0, 0.0)
        return mse, under, over, hi

    @property
    def declared_rate(self) -> float:
        return self._declared_count / self._total_values if self._total_values else 0.0


def _fresh_competitors_exp5(G: float, noise_threshold: float,
                            alpha: float = ALPHA_PRIMARY) -> List:
    return [
        PhiZakhor(alpha),
        PhiZakhorKeepG2(G, noise_threshold, alpha),
        PhiStatic(),
        GridZakhor(alpha),
        GridStatic(),
        OraclePhi(),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stream runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_exp5(
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


def _hash_raw_exp5(raw: Dict) -> str:
    h = hashlib.sha256()
    for name in sorted(raw.keys()):
        for mse, under, over, _ in raw[name]:
            h.update(f"{mse:.15e}{under:.15e}{over:.15e}".encode())
    return h.hexdigest()[:16]


def _print_summary_exp5(label: str,
                        raw: Dict[str, List[Tuple[float, float, float, float]]]) -> None:
    print(f"\n{label}")
    print("-" * 86)
    print(f"  {'competitor':<26} {'MSE':>14} {'underflow':>12} {'overflow':>12}")
    for name in _NAMES_5:
        if name not in raw:
            continue
        msvals = [r[0] for r in raw[name]]
        uvals = [r[1] for r in raw[name]]
        ovals = [r[2] for r in raw[name]]
        print(f"  {name:<26} {_mean(msvals):>14.4e} {_mean(uvals):>12.4e} {_mean(ovals):>12.4e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. H5: state displacement per spike (gated)
# ─────────────────────────────────────────────────────────────────────────────

def h5_state_displacement(g2: PhiZakhorKeepG2) -> Dict[str, object]:
    """H5(a): per-spike state displacement for G2.

    displacement = |post_state - pre_state| for each spike block.
    With gating: stranger blocks don't update state → displacement = 0.
    Skips cold-start block (t=0) since it always seeds from the spike obs.
    """
    spike_blocks = [t for t in range(SPIKE_PERIOD, N_BLOCKS, SPIKE_PERIOD)]
    disps: List[float] = []
    for t in spike_blocks:
        if t >= len(g2._state_log):
            break
        pre, post = g2._state_log[t]
        disps.append(abs(post - pre))
    peak = max(disps) if disps else 0.0
    return {
        "peak_displacement": peak,
        "n_analyzed": len(disps),
        "all_zero": all(d < 1e-10 for d in disps),
        "pass": peak <= H5_DISP_LIMIT,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. H6: regime rebirth recovery on S3
# ─────────────────────────────────────────────────────────────────────────────

def h6_rebirth_recovery(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    g2: PhiZakhorKeepG2,
    step_block: int,
    pre_window: int = 256,
) -> Dict[str, object]:
    """H6: oracle-relative R within 2× R̄ in ≤ K + 8 blocks after step.

    Recovery measured from step_block. With regime rebirth at step_block + K,
    R should drop near 1 immediately after rebirth.
    """
    rec = h2_r_recovery(raw, step_block, pre_window)
    pz_rec = rec.get("PHI-ZAKHOR", {})
    g2_rec = rec.get("PHI-ZAKHOR-KEEP-G2", {})

    regime_count = len(g2.regime_log)
    regime_at_step = [
        e for e in g2.regime_log
        if step_block <= e[0] <= step_block + N_BLOCKS // 4
    ]

    T_g2 = g2_rec.get("recovery_blocks")
    g2_ok = T_g2 is not None and T_g2 <= H6_RECOVERY_BUDGET

    return {
        "PHI-ZAKHOR": pz_rec,
        "PHI-ZAKHOR-KEEP-G2": g2_rec,
        "g2_recovery_ok": g2_ok,
        "g2_recovery_blocks": T_g2,
        "regime_events_total": regime_count,
        "regime_events_near_step": len(regime_at_step),
        "regime_near_step": regime_at_step[:3],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. H7: honesty v3 (silent-error excludes stranger + mid-return)
# ─────────────────────────────────────────────────────────────────────────────

def honesty_v3(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    g2: PhiZakhorKeepG2,
    is_spike: bool = False,
) -> Dict[str, Dict[str, float]]:
    """Per-competitor declared-loss, mid-return, and silent-error rates.

    Silent-error (G2): err > 10× oracle AND NOT (stranger OR mid-return).
    Silent-error (others): err > 10× oracle AND NOT declared (no mid-return for others).
    """
    rnd = _lcg(seed)
    declared: Dict[str, int] = {c.name: 0 for c in competitors}
    mid_return_cnt: Dict[str, int] = {c.name: 0 for c in competitors}
    silent: Dict[str, int] = {c.name: 0 for c in competitors}
    total_values = 0

    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)

        oracle_hi = raw["ORACLE-PHI"][t][3]
        oracle_book = _phi_codebook(max(oracle_hi, 1e-300), LEVELS)

        is_mid_g2 = (t < len(g2.mid_return_flags) and g2.mid_return_flags[t])

        for v in block:
            total_values += 1
            _, rv_oracle = _snap(v, oracle_book)
            oracle_err = (v - rv_oracle) ** 2

            for c in competitors:
                hi_c = raw[c.name][t][3]
                book_c = (
                    _phi_codebook(hi_c, LEVELS) if c.is_phi
                    else _uniform_codebook(hi_c, LEVELS)
                )
                is_decl = (c.name == "PHI-ZAKHOR-KEEP-G2" and abs(v) > hi_c)
                is_mr = (c.name == "PHI-ZAKHOR-KEEP-G2" and is_mid_g2)

                if is_decl:
                    declared[c.name] += 1
                else:
                    _, rv = _snap(v, book_c)
                    err = (v - rv) ** 2
                    if err > H3_SILENT_THRESHOLD * oracle_err + 1e-30:
                        if not is_mr:
                            silent[c.name] += 1
                if is_mr and not is_decl:
                    mid_return_cnt[c.name] += 1

    n = total_values
    return {
        c.name: {
            "declared_rate": declared[c.name] / n,
            "mid_return_rate": mid_return_cnt[c.name] / n,
            "silent_error_rate": silent[c.name] / n,
        }
        for c in competitors
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. All-runs for reproducibility
# ─────────────────────────────────────────────────────────────────────────────

def _all_runs_exp5(G: float, noise_threshold: float,
                   alpha: float = ALPHA_PRIMARY) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for std in (STD_PEAKED, STD_SPREAD):
        for tag, fn, off, spike in (
            (f"S1-{std}",   _scales_stationary,  1, False),
            (f"S2up-{std}", _scales_drift_up,     2, False),
            (f"S3up-{std}", _scales_step_up,      4, False),
            (f"S3dn-{std}", _scales_step_down,    5, False),
            (f"S4-{std}",   _scales_spike,        6, True),
        ):
            cs = _fresh_competitors_exp5(G, noise_threshold, alpha)
            out[tag] = _run_exp5(cs, fn(), std, SEED_BASE + off, is_spike=spike)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 8. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 005 — Logged, Not Remembered — and Kept Alive")
    print("=" * 96)
    print("  Pre-registered 2026-07-11. H0-id retired per two-strike rule (exp004). See exp005-pre-reg.md.")
    print(f"  K={K_REBIRTH}  f̂={F_HAT}  recovery_settle={RECOVERY_SETTLE}  H6_budget={H6_RECOVERY_BUDGET}")

    step_block = N_BLOCKS // 2
    verdicts: Dict[str, str] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                           (STD_SPREAD,  f"spread(std={STD_SPREAD})")):

        # ── Calibration ────────────────────────────────────────────────────
        G, noise_thr = calibrate_exp5(ALPHA_PRIMARY, std)
        print(f"\n{'━'*96}")
        print(f"  Distribution: {std_label}")
        print(f"  Calibration (CAL_BLOCKS={CAL_BLOCKS}): G={G:.1f}  noise_threshold={noise_thr:.4f} "
              f"(p95|delta|, no 4× — was {4*noise_thr:.4f} in exp004)")
        print("━" * 96)

        # ── §4 Regression gate: S1 stationary ──────────────────────────────
        cs_s1 = _fresh_competitors_exp5(G, noise_thr)
        raw_s1 = _run_exp5(cs_s1, _scales_stationary(), std, SEED_BASE + 1)
        g2_s1: PhiZakhorKeepG2 = next(c for c in cs_s1 if c.name == "PHI-ZAKHOR-KEEP-G2")
        _print_summary_exp5(f"§4 S1 STATIONARY ({std_label})", raw_s1)

        pz_mse = _mean([raw_s1["PHI-ZAKHOR"][t][0] for t in range(N_BLOCKS)])
        g2_mse = _mean([raw_s1["PHI-ZAKHOR-KEEP-G2"][t][0] for t in range(N_BLOCKS)])
        reg_ok = g2_mse <= pz_mse * 1.05
        verdicts[f"regression-{std}"] = _pf(reg_ok)
        print(f"  Regression: PHI-ZAKHOR {pz_mse:.4e}  G2 {g2_mse:.4e} — {verdicts[f'regression-{std}']}")
        print(f"  S1 REGIME events: {len(g2_s1.regime_log)} (expected 0)")
        print(f"  S1 stranger log: {len(g2_s1.stranger_log)} entries")
        if not reg_ok:
            print("  *** REGRESSION FAIL. Halting.")
            return

        # S1 oracle-relative R (for S4c / H5b)
        oracle_mse_s1 = [raw_s1["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]
        R_s1: Dict[str, float] = {}
        for name in _NAMES_5:
            if name in raw_s1 and name != "ORACLE-PHI":
                R_s1[name] = _mean([
                    raw_s1[name][t][0] / max(oracle_mse_s1[t], 1e-30)
                    for t in range(N_BLOCKS)
                ])

        # ── §2 S2 drift — REGIME audit ─────────────────────────────────────
        cs_s2 = _fresh_competitors_exp5(G, noise_thr)
        raw_s2 = _run_exp5(cs_s2, _scales_drift_up(), std, SEED_BASE + 2)
        g2_s2: PhiZakhorKeepG2 = next(c for c in cs_s2 if c.name == "PHI-ZAKHOR-KEEP-G2")
        n_regime_s2 = len(g2_s2.regime_log)
        _print_summary_exp5(f"S2 SLOW DRIFT ↑ ({std_label})", raw_s2)
        print(f"  S2 REGIME events: {n_regime_s2} "
              f"({'expected 0' if n_regime_s2 == 0 else '*** UNEXPECTED — drift exceeds guard band'})")
        if n_regime_s2 > 0:
            for ev in g2_s2.regime_log[:3]:
                print(f"    block={ev[0]}  old={ev[1]:.3f}  new={ev[2]:.3f}  Δ={ev[3]:.3f}")

        # ── §2 H6: S3 step-UP recovery + REGIME audit ──────────────────────
        cs_s3u = _fresh_competitors_exp5(G, noise_thr)
        raw_s3u = _run_exp5(cs_s3u, _scales_step_up(), std, SEED_BASE + 4)
        g2_s3u: PhiZakhorKeepG2 = next(c for c in cs_s3u if c.name == "PHI-ZAKHOR-KEEP-G2")
        _print_summary_exp5(f"§2 S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})", raw_s3u)
        h6_up = h6_rebirth_recovery(raw_s3u, g2_s3u, step_block)
        pz_up_rec = h6_up["PHI-ZAKHOR"]["recovery_blocks"]
        g2_up_rec = h6_up["g2_recovery_blocks"]
        h6_up_ok = h6_up["g2_recovery_ok"] and h6_up["regime_events_near_step"] == 1
        verdicts[f"H6-up-{std}"] = _pf(h6_up_ok)
        print(f"  H6 S3↑: REGIME events near step: {h6_up['regime_events_near_step']} (want 1)  "
              f"PHI-ZAKHOR recovery={pz_up_rec}  G2 recovery={g2_up_rec}  "
              f"(budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H6-up-{std}']}")
        for ev in h6_up["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f} shells  Δ={ev[3]:.3f}")

        # S3 step-DOWN
        cs_s3d = _fresh_competitors_exp5(G, noise_thr)
        raw_s3d = _run_exp5(cs_s3d, _scales_step_down(), std, SEED_BASE + 5)
        g2_s3d: PhiZakhorKeepG2 = next(c for c in cs_s3d if c.name == "PHI-ZAKHOR-KEEP-G2")
        _print_summary_exp5(f"S3 STEP ↓ (−{STEP_SHELLS} shells) ({std_label})", raw_s3d)
        h6_dn = h6_rebirth_recovery(raw_s3d, g2_s3d, step_block)
        g2_dn_rec = h6_dn["g2_recovery_blocks"]
        pz_dn_rec = h6_dn["PHI-ZAKHOR"]["recovery_blocks"]
        h6_dn_ok = h6_dn["g2_recovery_ok"] and h6_dn["regime_events_near_step"] == 0
        verdicts[f"H6-dn-{std}"] = _pf(h6_dn_ok)
        n_regime_s3d = len(g2_s3d.regime_log)
        print(f"  H6 S3↓: REGIME events: {n_regime_s3d} (want 0 — step-DOWN signal is not a stranger)  "
              f"PHI-ZAKHOR recovery={pz_dn_rec}  G2 recovery={g2_dn_rec}  "
              f"(budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H6-dn-{std}']}")
        print(f"  Contrast: rebirth T={g2_up_rec} (gated UP) vs T(Δ=8,f≈0.68,α=1/64)≈{pz_up_rec} (ungated)")
        verdicts[f"H6-{std}"] = _pf(h6_up_ok and h6_dn_ok)
        print(f"  H6 overall: {verdicts[f'H6-{std}']}")

        # ── §1 H5 + §3 H7: S4 spike streams ───────────────────────────────
        cs_s4 = _fresh_competitors_exp5(G, noise_thr)
        raw_s4 = _run_exp5(cs_s4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        g2_s4: PhiZakhorKeepG2 = next(c for c in cs_s4 if c.name == "PHI-ZAKHOR-KEEP-G2")
        _print_summary_exp5(
            f"§1 S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            raw_s4,
        )

        # S4a regression (PHI-ZAKHOR ungated)
        s4a = s4a_state_integrity(raw_s4, "PHI-ZAKHOR")
        ref = EXP003_S4A_PEAK_PEAKED if std == STD_PEAKED else EXP003_S4A_PEAK_SPREAD
        s4a_reg_ok = abs(s4a["peak_displacement"] - ref) <= S4A_REG_TOL
        verdicts[f"S4a-reg-{std}"] = _pf(s4a_reg_ok)
        print(f"\n  §4 S4a ungated regression: peak_disp={s4a['peak_displacement']:.4f} "
              f"(exp003 ref={ref:.4f}) — {verdicts[f'S4a-reg-{std}']}")

        # H5a: state displacement with gating
        h5d = h5_state_displacement(g2_s4)
        verdicts[f"H5a-{std}"] = _pf(h5d["pass"])
        print(f"  §1 H5(a) state displacement: peak={h5d['peak_displacement']:.6f} shells "
              f"(threshold ≤{H5_DISP_LIMIT}, analyzed {h5d['n_analyzed']} spikes, "
              f"all_zero={h5d['all_zero']}) — {verdicts[f'H5a-{std}']}")
        n_regime_s4 = len(g2_s4.regime_log)
        print(f"  S4 REGIME events: {n_regime_s4} (expected 0 — isolated spikes never reach K={K_REBIRTH})")

        # H5b: S4c collateral
        s4c = s4c_collateral(raw_s4, R_s1)
        pz_s4c_ok = s4c.get("PHI-ZAKHOR", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        g2_s4c_ok = s4c.get("PHI-ZAKHOR-KEEP-G2", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        verdicts[f"H5b-{std}"] = _pf(g2_s4c_ok)
        print(f"  §1 H5(b) S4c collateral (normal-block R / S1 R, threshold ≤{S4C_MAX_R_RATIO}):")
        for name in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G2", "GRID-ZAKHOR"):
            if name in s4c:
                d = s4c[name]
                print(f"    {name:<28} R_normal={d['R_normal']:.3f}  R_s1={d['R_s1']:.3f}  ratio={d['ratio']:.3f}")

        # S4b spike fidelity (descriptive)
        s4b = s4b_spike_fidelity(raw_s4, std)
        print(f"  S4b spike fidelity (spike-MSE / normal-MSE):")
        for name in _NAMES_5:
            if name in s4b:
                print(f"    {name:<28} {s4b[name]:>10.2f}×")

        # H5c: over-declaration
        g2_decl_rate = g2_s4.declared_rate
        h5c_ok = g2_decl_rate <= H5_DECL_MULT * SPIKE_TRUE_FRAC
        verdicts[f"H5c-{std}"] = _pf(h5c_ok)
        print(f"  §1 H5(c) over-declaration: G2 declared_rate={g2_decl_rate:.4e} "
              f"(limit={H5_DECL_MULT*SPIKE_TRUE_FRAC:.4e}) — {verdicts[f'H5c-{std}']}")
        verdicts[f"H5-{std}"] = _pf(h5d["pass"] and g2_s4c_ok and h5c_ok)
        print(f"  H5 overall: {verdicts[f'H5-{std}']}")

        # §3 H7: honesty v3
        cs_h7 = _fresh_competitors_exp5(G, noise_thr)
        raw_h7 = _run_exp5(cs_h7, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        g2_h7: PhiZakhorKeepG2 = next(c for c in cs_h7 if c.name == "PHI-ZAKHOR-KEEP-G2")
        hm = honesty_v3(raw_h7, cs_h7, _scales_spike(), std, SEED_BASE + 6, g2_h7, is_spike=True)
        print(f"\n  §3 Honesty v3 ({std_label}) — spike frac: {SPIKE_TRUE_FRAC:.2e}, "
              f"H7 silent limit: {H7_SILENT_LIMIT:.1e}")
        print(f"  {'competitor':<28} {'decl_rate':>12} {'mid_ret_rate':>14} {'silent_err':>12}")
        for name in _NAMES_5:
            if name not in hm:
                continue
            d = hm[name]
            print(f"  {name:<28} {d['declared_rate']:>12.4e} "
                  f"{d['mid_return_rate']:>14.4e} {d['silent_error_rate']:>12.4e}")
        g2_hm = hm.get("PHI-ZAKHOR-KEEP-G2", {})
        h7_ok = g2_hm.get("silent_error_rate", 1.0) < H7_SILENT_LIMIT
        verdicts[f"H7-{std}"] = _pf(h7_ok)
        print(f"  H7: silent_err={g2_hm.get('silent_error_rate', 1.0):.4e} "
              f"(< {H7_SILENT_LIMIT:.1e}) — {verdicts[f'H7-{std}']}")
        print(f"  PHI-STATIC silent-error: {hm.get('PHI-STATIC', {}).get('silent_error_rate', 0):.3e} "
              f"(standing contrast: silence is not fidelity)")

        # Three register summary
        print(f"\n  Three registers ({std_label}):")
        print(f"    Stranger log: {len(g2_h7.stranger_log)} entries.  "
              f"Mid-return blocks: {sum(g2_h7.mid_return_flags)}/{N_BLOCKS}.  "
              f"Regime log: {len(g2_h7.regime_log)} entries.")
        print(f"    First 3 strangers: {g2_h7.stranger_log[:3]}")
        print(f"    Regime events: {g2_h7.regime_log}")

        # Also test H7 on S3 streams (need silent-error across all streams)
        # Check S3 step-UP for H7
        cs_h7_s3u = _fresh_competitors_exp5(G, noise_thr)
        raw_h7_s3u = _run_exp5(cs_h7_s3u, _scales_step_up(), std, SEED_BASE + 4)
        g2_h7_s3u: PhiZakhorKeepG2 = next(c for c in cs_h7_s3u if c.name == "PHI-ZAKHOR-KEEP-G2")
        hm_s3u = honesty_v3(raw_h7_s3u, cs_h7_s3u, _scales_step_up(), std, SEED_BASE + 4,
                             g2_h7_s3u, is_spike=False)
        g2_s3u_silent = hm_s3u.get("PHI-ZAKHOR-KEEP-G2", {}).get("silent_error_rate", 1.0)
        h7_s3u_ok = g2_s3u_silent < H7_SILENT_LIMIT
        print(f"  H7 on S3↑: silent_err={g2_s3u_silent:.4e} — {_pf(h7_s3u_ok)}  "
              f"regime={len(g2_h7_s3u.regime_log)} events")

        # Check S3 step-DOWN for H7
        cs_h7_s3d = _fresh_competitors_exp5(G, noise_thr)
        raw_h7_s3d = _run_exp5(cs_h7_s3d, _scales_step_down(), std, SEED_BASE + 5)
        g2_h7_s3d: PhiZakhorKeepG2 = next(c for c in cs_h7_s3d if c.name == "PHI-ZAKHOR-KEEP-G2")
        hm_s3d = honesty_v3(raw_h7_s3d, cs_h7_s3d, _scales_step_down(), std, SEED_BASE + 5,
                             g2_h7_s3d, is_spike=False)
        g2_s3d_silent = hm_s3d.get("PHI-ZAKHOR-KEEP-G2", {}).get("silent_error_rate", 1.0)
        h7_s3d_ok = g2_s3d_silent < H7_SILENT_LIMIT
        print(f"  H7 on S3↓: silent_err={g2_s3d_silent:.4e} — {_pf(h7_s3d_ok)}  "
              f"mid_return_blocks={sum(g2_h7_s3d.mid_return_flags)}")

        h7_all_ok = h7_ok and h7_s3u_ok and h7_s3d_ok
        verdicts[f"H7-all-{std}"] = _pf(h7_all_ok)
        print(f"  H7 all streams: {verdicts[f'H7-all-{std}']}")

    # ── H2-f regression: PHI-ZAKHOR ungated formula grid ───────────────────
    print(f"\n{'='*96}")
    print("§4 H2-f REGRESSION (PHI-ZAKHOR ungated must reproduce exp004 ±8%)")
    print(f"{'='*96}")
    G_pk, _ = calibrate_exp5(ALPHA_PRIMARY, STD_PEAKED)
    print(f"  {'alpha':>8} | {'dir':>5} | {'T_meas':>8} | {'T_form':>8} | "
          f"{'f_shells':>10} | {'err_frac':>10} | verdict")
    h2f_reg_ok = True
    for alpha_sw in ALPHA_SWEEP:
        G_sw, nt_sw = calibrate_exp5(alpha_sw, STD_PEAKED)
        for direction, fn_s, off_s in (("UP", _scales_step_up, 4),
                                       ("DN", _scales_step_down, 5)):
            cs_reg = _fresh_competitors_exp5(G_sw, nt_sw, alpha_sw)
            raw_reg = _run_exp5(cs_reg, fn_s(), STD_PEAKED,
                                SEED_BASE + off_s + round(1 / alpha_sw))
            fc = h2_f_check(raw_reg, step_block, alpha_sw, direction)
            T_m = fc.get("T_measured")
            T_f = fc.get("T_formula")
            ef = fc.get("error_frac")
            p = fc.get("pass")
            if p is False:
                h2f_reg_ok = False
            print(f"  {alpha_sw:>8.4f} | {direction:>5} | "
                  f"{str(T_m) if T_m is not None else '>N':>8} | "
                  f"{f'{T_f:.1f}' if T_f is not None else '—':>8} | "
                  f"{fc.get('f', 0):>10.4f} | "
                  f"{f'{ef:.3f}' if ef is not None else '—':>10} | "
                  f"{_pf(p) if p is not None else 'METRIC-DEFECT'}")
    verdicts["H2f-reg"] = _pf(h2f_reg_ok)
    print(f"  H2-f regression: {verdicts['H2f-reg']}")

    # ── Verdict summary ─────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("VERDICT SUMMARY")
    print(f"{'='*96}")
    print(f"  {'check':<28} {'peaked':>12} {'spread':>12}")
    for stem in ("regression", "H5a", "H5b", "H5c", "H5",
                 "H6-up", "H6-dn", "H6", "H7", "H7-all", "S4a-reg"):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<28} {vp:>12} {vs:>12}")
    print(f"  {'H2f-reg':28} {verdicts.get('H2f-reg', '—'):>12}")
    print()
    print("  H0-id: RETIRED (two-strike rule, exp004). Shell automorphism: descriptive only.")
    print("  T=ln(Δ/f)/α (ungated) vs rebirth ≤ K+8 (gated): both numbers in record.")
    print("  Verdicts: PASS / FALSIFIED / METRIC-DEFECT — no fourth category.")

    # ── Reproducibility ─────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("REPRODUCIBILITY")
    G_r, nt_r = calibrate_exp5(ALPHA_PRIMARY, STD_PEAKED)
    rA = _all_runs_exp5(G_r, nt_r)
    rB = _all_runs_exp5(G_r, nt_r)
    hA = hashlib.sha256()
    hB = hashlib.sha256()
    for k in sorted(rA):
        hA.update(_hash_raw_exp5(rA[k]).encode())
        hB.update(_hash_raw_exp5(rB[k]).encode())
    da, db = hA.hexdigest()[:16], hB.hexdigest()[:16]
    match = da == db
    print(f"  run1={da}  run2={db}  {_pf(match)} (bit-identical)")
    print()
    print("  Log dated output to research/results/exp005_<YYYY-MM-DD>.txt.")


if __name__ == "__main__":
    main()
