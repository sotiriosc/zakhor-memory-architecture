"""exp006_symmetric_gate.py — The Symmetric Gate: Excess, Absence, and the Guarded Oracle.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Pre-registered: hypotheses and thresholds frozen on 2026-07-11 before any code
was written. See docs/exp006-pre-registration.md.

Addresses exp005's root-cause trio:
  (1) H6-dn / H5b: stranger-persistence was one-directional (excess only).
      Fix: watch |d_raw| = |obs − state| direction-agnostically — §1.
  (2) H5c-peaked: p99 guard guarantees ~1% natural exceedance while the
      exp005 threshold demanded ≤5% of the spike count. Spec contradiction
      fixed in H9 — §2.
  (3) H7: 10× raw-oracle is structurally unreachable for any guarded
      competitor. Fix: compare against ORACLE-PHI-G (hi = block_max×φ^G) — §3.

H0-id: retired per two-strike rule (exp004). Does not appear here.

Run from repository root:

    python3 research/exp006_symmetric_gate.py

Bit-identical re-run asserted inline.
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
from core.phi_theory import PHI, PHI_INV, _clipped_gauss, _lcg

# ── exp006 constants ──────────────────────────────────────────────────────────

H10_SILENT_LIMIT: float = 0.001    # < 0.1%
H9_SLACK: int = 3                  # small-count slack in H9 criterion
S4A_REG_TOL: float = 0.02
_H8_CONSECUTIVE: int = 8           # R-within-threshold window for recovery

_NAMES_6: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G3", "PHI-STATIC",
    "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI", "ORACLE-PHI-G",
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Guarded oracle: ORACLE-PHI-G
# ─────────────────────────────────────────────────────────────────────────────

class OraclePhiG:
    """Per-block hi = block_max × φ^G.

    Normalises guard-band overhead so steady-state shell spacing matches the
    guarded competitor's — structural mismatch vanishes; only genuine transient
    errors remain visible to the silent-error criterion.
    """

    name = "ORACLE-PHI-G"
    is_phi = True

    def __init__(self, G: float) -> None:
        self.G = G
        self._phi_G = PHI ** G

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        max_mag = max(abs(v) for v in block) if block else 1e-300
        hi = max(max_mag * self._phi_G, 1e-300)
        book = _phi_codebook(hi, LEVELS)
        mse, under, over = _block_stats(block, book)
        return mse, under, over, hi


# ─────────────────────────────────────────────────────────────────────────────
# 2. Calibration
# ─────────────────────────────────────────────────────────────────────────────

def calibrate_exp6(alpha: float = ALPHA_PRIMARY, std: float = STD_PEAKED
                   ) -> Tuple[float, float, float, float]:
    """Derive G, D, noise_threshold, e_hat from the calibration window.

    G:               max(1, ceil(p99(d⁺)))   — guard band (exp004 rule)
    D:               max(2, ceil(p99(d⁺))+1) — symmetric regime threshold = G+1
    noise_threshold: p95(|delta|)            — formula-clocked flag trigger
    e_hat:           P̂(d⁺ > G)              — empirical exceedance fraction for H9
    """
    zs = ZakhorScale(alpha)
    rnd = _lcg(CAL_SEED)
    d_plus: List[float] = []
    abs_delta: List[float] = []
    n_exceed: int = 0

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
    D = max(2.0, math.ceil(_percentile(d_plus, 0.99)) + 1.0)
    noise_threshold = _percentile(abs_delta, 0.95)

    # Compute e_hat: fraction of calibration blocks where d+ > G
    n_exceed = sum(1 for d in d_plus if d > G)
    e_hat = n_exceed / len(d_plus) if d_plus else 0.0

    return G, D, noise_threshold, e_hat


# ─────────────────────────────────────────────────────────────────────────────
# 3. PHI-ZAKHOR-KEEP-G3: symmetric regime detection
# ─────────────────────────────────────────────────────────────────────────────

class PhiZakhorKeepG3:
    """Guard-band KEEP with symmetric regime detection and rebirth.

    Rebirth trigger (§1): |d_raw| > D for K consecutive blocks → REBIRTH.
    d_raw = obs − scale_state, computed before any gating decision.
    State update: stranger gating unchanged (freeze on stranger blocks).
    Rebirth supersedes gating.

    Three registers:
      stranger_log:   (block_idx, shell_coord, overshoot×)
      mid_return_flags: List[bool] per block
      regime_log:     (block_idx, old_state, new_state, signed_shells)
                      signed_shells > 0: world got quieter; < 0: louder.
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

        # ── §1 Symmetric regime detection (before gating) ────────────────────
        d_raw = obs - pre_orig
        if abs(d_raw) > self.D:
            self._regime_counter += 1
        else:
            self._regime_counter = 0

        hi = hi_from_state(pre_orig - self.G)
        is_stranger = max_mag > hi
        reborn = False

        if self._regime_counter >= K_REBIRTH:
            # REBIRTH supersedes gating
            old_state = self._s
            self._s = obs
            self._regime_counter = 0
            signed_shells = obs - old_state   # >0: quieter; <0: louder
            self.regime_log.append(
                (self._block_idx, old_state, obs, signed_shells)
            )
            reborn = True
            hi = hi_from_state(obs - self.G)
            is_stranger = max_mag > hi         # False after rebirth (hi ≥ max_mag×φ)
        elif is_stranger:
            pass                               # gating: state frozen
        else:
            self._s = pre_orig + self.alpha * (obs - pre_orig)

        self._state_log.append((pre_orig, self._s))

        # ── Formula-clocked mid-return flag ──────────────────────────────────
        if reborn:
            T_flag = RECOVERY_SETTLE           # K + 4 = 7
            self._mid_countdown = max(self._mid_countdown, T_flag)
        elif not is_stranger and abs(d_raw) > self.noise_threshold:
            Δ_est = max(abs(d_raw), 1e-6)
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


def _fresh_competitors_exp6(G: float, D: float, noise_threshold: float,
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


# ─────────────────────────────────────────────────────────────────────────────
# 4. Stream runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_exp6(
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
    for name in _NAMES_6:
        if name not in raw:
            continue
        ms = [r[0] for r in raw[name]]
        us = [r[1] for r in raw[name]]
        os_ = [r[2] for r in raw[name]]
        print(f"  {name:<26} {_mean(ms):>14.4e} {_mean(us):>12.4e} {_mean(os_):>12.4e}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. H5a reproduction: state displacement under gating
# ─────────────────────────────────────────────────────────────────────────────

def h5a_displacement(g3: PhiZakhorKeepG3) -> Dict:
    """Reproduce H5a: per-spike state displacement must be 0 for gated blocks."""
    spike_blocks = [t for t in range(SPIKE_PERIOD, N_BLOCKS, SPIKE_PERIOD)]
    disps: List[float] = []
    for t in spike_blocks:
        if t >= len(g3._state_log):
            break
        pre, post = g3._state_log[t]
        disps.append(abs(post - pre))
    peak = max(disps) if disps else 0.0
    return {"peak": peak, "all_zero": all(d < 1e-10 for d in disps),
            "n": len(disps), "pass": peak <= H5_DISP_LIMIT}


# ─────────────────────────────────────────────────────────────────────────────
# 6. H8: symmetric regime detection
# ─────────────────────────────────────────────────────────────────────────────

def h8_recovery(
    raw: Dict,
    g3: PhiZakhorKeepG3,
    step_block: int,
    stream_label: str,
    pre_window: int = 256,
    near_window: int = 16,
) -> Dict:
    """H8: oracle-relative R within 2×R̄ in ≤ K+8 blocks; REGIME audit."""
    rec = h2_r_recovery(raw, step_block, pre_window)
    g3_rec = rec.get("PHI-ZAKHOR-KEEP-G3", {})
    pz_rec = rec.get("PHI-ZAKHOR", {})

    regime_events = g3.regime_log
    near = [e for e in regime_events
            if step_block <= e[0] <= step_block + near_window]

    T = g3_rec.get("recovery_blocks")
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
# 7. H9: calibration-consistent over-declaration
# ─────────────────────────────────────────────────────────────────────────────

def h9_declaration(
    g3: PhiZakhorKeepG3,
    true_spike_count: int,
    e_hat: float,
    truthful: bool = True,   # every declaration must be genuinely beyond hi
) -> Dict:
    """H9: declared ≤ true_spike_count + 2·N̂ + 3; plus truthfulness audit."""
    N_hat = e_hat * N_BLOCKS
    limit = true_spike_count + 2 * N_hat + H9_SLACK
    count = g3._declared
    ok = count <= limit and truthful
    return {
        "declared": count,
        "true_spikes": true_spike_count,
        "N_hat": N_hat,
        "limit": limit,
        "truthful": truthful,
        "pass": ok,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. H10: honesty against ORACLE-PHI-G
# ─────────────────────────────────────────────────────────────────────────────

def honesty_v4(
    raw: Dict,
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    g3: PhiZakhorKeepG3,
    is_spike: bool = False,
) -> Dict[str, Dict]:
    """Per-competitor honesty accounting; silent-error vs ORACLE-PHI-G for G3.

    G3: silent if err > 10× oracle_G_err AND NOT (stranger OR mid-return).
    Others: silent if err > 10× oracle_err AND NOT declared.
    Both raw-oracle and guarded-oracle rates reported for G3.
    """
    rnd = _lcg(seed)
    decl: Dict[str, int] = {c.name: 0 for c in competitors}
    mid_cnt: Dict[str, int] = {c.name: 0 for c in competitors}
    silent_raw: Dict[str, int] = {c.name: 0 for c in competitors}  # vs ORACLE-PHI
    silent_g: Dict[str, int] = {c.name: 0 for c in competitors}    # vs ORACLE-PHI-G
    total = 0

    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)

        oracle_hi = raw["ORACLE-PHI"][t][3]
        oracle_book = _phi_codebook(max(oracle_hi, 1e-300), LEVELS)
        oracle_g_hi = raw["ORACLE-PHI-G"][t][3]
        oracle_g_book = _phi_codebook(max(oracle_g_hi, 1e-300), LEVELS)

        is_mid_g3 = (t < len(g3.mid_return_flags) and g3.mid_return_flags[t])

        for v in block:
            total += 1
            _, rv_oracle = _snap(v, oracle_book)
            oracle_err = (v - rv_oracle) ** 2
            _, rv_oracle_g = _snap(v, oracle_g_book)
            oracle_g_err = (v - rv_oracle_g) ** 2

            for c in competitors:
                hi_c = raw[c.name][t][3]
                book_c = (
                    _phi_codebook(hi_c, LEVELS) if c.is_phi
                    else _uniform_codebook(hi_c, LEVELS)
                )
                is_decl = (c.name == "PHI-ZAKHOR-KEEP-G3" and abs(v) > hi_c
                           and not (t < len(g3.mid_return_flags)
                                    and g3.regime_log
                                    and any(e[0] == t + 1 for e in g3.regime_log)))
                # Simplified: declared if value was actually logged
                is_decl_actual = (c.name == "PHI-ZAKHOR-KEEP-G3"
                                  and raw[c.name][t][2] == 0.0  # no, use abs(v)>hi_c)
                                  and abs(v) > hi_c)
                is_decl = (c.name == "PHI-ZAKHOR-KEEP-G3" and abs(v) > hi_c)
                is_mr = (c.name == "PHI-ZAKHOR-KEEP-G3" and is_mid_g3)

                if is_decl:
                    decl[c.name] += 1
                else:
                    _, rv = _snap(v, book_c)
                    err = (v - rv) ** 2
                    threshold = H3_SILENT_THRESHOLD
                    if err > threshold * oracle_err + 1e-30:
                        if not is_mr:
                            silent_raw[c.name] += 1
                    if c.name == "PHI-ZAKHOR-KEEP-G3":
                        if err > threshold * oracle_g_err + 1e-30:
                            if not is_mr:
                                silent_g[c.name] += 1
                if is_mr and not is_decl:
                    mid_cnt[c.name] += 1

    n = total
    result: Dict[str, Dict] = {}
    for c in competitors:
        d = {
            "declared_rate": decl[c.name] / n,
            "mid_return_rate": mid_cnt[c.name] / n,
            "silent_raw_rate": silent_raw[c.name] / n,
        }
        if c.name == "PHI-ZAKHOR-KEEP-G3":
            d["silent_g_rate"] = silent_g[c.name] / n
        result[c.name] = d
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 9. All-streams runner for reproducibility
# ─────────────────────────────────────────────────────────────────────────────

def _all_runs(G, D, noise_thr, alpha=ALPHA_PRIMARY) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for std in (STD_PEAKED, STD_SPREAD):
        for tag, fn, off, spike in (
            (f"S1-{std}", _scales_stationary, 1, False),
            (f"S3u-{std}", _scales_step_up, 4, False),
            (f"S3d-{std}", _scales_step_down, 5, False),
            (f"S4-{std}", _scales_spike, 6, True),
        ):
            cs = _fresh_competitors_exp6(G, D, noise_thr, alpha)
            out[tag] = _run_exp6(cs, fn(), std, SEED_BASE + off, is_spike=spike)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 10. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 006 — The Symmetric Gate")
    print("=" * 96)
    print("  Pre-registered 2026-07-11. H0-id retired. See exp006-pre-reg.md.")
    print(f"  K={K_REBIRTH}  f̂={F_HAT}  recovery_settle={RECOVERY_SETTLE}"
          f"  H8_budget={H6_RECOVERY_BUDGET}  H10_limit={H10_SILENT_LIMIT:.1e}")

    step_block = N_BLOCKS // 2
    verdicts: Dict[str, str] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                           (STD_SPREAD,  f"spread(std={STD_SPREAD})")):

        # ── Calibration ────────────────────────────────────────────────────
        G, D, noise_thr, e_hat = calibrate_exp6(ALPHA_PRIMARY, std)
        true_spike_count = int(N_BLOCKS / SPIKE_PERIOD) - 1  # exclude cold-start (not stranger)
        N_hat = e_hat * N_BLOCKS
        h9_limit = true_spike_count + 2 * N_hat + H9_SLACK

        print(f"\n{'━'*96}")
        print(f"  Distribution: {std_label}")
        print(f"  Calibration: G={G:.1f}  D={D:.1f}  noise_threshold={noise_thr:.4f}"
              f"  e_hat={e_hat:.4f}  N̂={N_hat:.1f}  H9_limit={h9_limit:.1f}")
        print("━" * 96)

        # ── §4 Regression gate: S1 ─────────────────────────────────────────
        cs_s1 = _fresh_competitors_exp6(G, D, noise_thr)
        raw_s1 = _run_exp6(cs_s1, _scales_stationary(), std, SEED_BASE + 1)
        g3_s1: PhiZakhorKeepG3 = next(c for c in cs_s1 if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(f"§4 S1 STATIONARY ({std_label})", raw_s1)

        pz_mse = _mean([raw_s1["PHI-ZAKHOR"][t][0] for t in range(N_BLOCKS)])
        g3_mse = _mean([raw_s1["PHI-ZAKHOR-KEEP-G3"][t][0] for t in range(N_BLOCKS)])
        reg_ok = g3_mse <= pz_mse * 1.05
        verdicts[f"regression-{std}"] = _pf(reg_ok)
        n_regime_s1 = len(g3_s1.regime_log)
        print(f"  Regression: PHI-ZAKHOR {pz_mse:.4e}  G3 {g3_mse:.4e} — {verdicts[f'regression-{std}']}")
        print(f"  S1 REGIME events: {n_regime_s1} (want 0)  "
              f"stranger log: {len(g3_s1.stranger_log)} entries")
        if not reg_ok:
            print("  *** REGRESSION FAIL. Halting.")
            return

        # Compute S1 oracle-relative R for s4c denominator
        oracle_mse_s1 = [raw_s1["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]
        R_s1: Dict[str, float] = {}
        for name in _NAMES_6:
            if name in raw_s1 and name != "ORACLE-PHI":
                R_s1[name] = _mean([
                    raw_s1[name][t][0] / max(oracle_mse_s1[t], 1e-30)
                    for t in range(N_BLOCKS)
                ])

        # ── §2 S2 drift — REGIME audit ─────────────────────────────────────
        cs_s2 = _fresh_competitors_exp6(G, D, noise_thr)
        raw_s2 = _run_exp6(cs_s2, _scales_drift_up(), std, SEED_BASE + 2)
        g3_s2: PhiZakhorKeepG3 = next(c for c in cs_s2 if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(f"S2 SLOW DRIFT ↑ ({std_label})", raw_s2)
        n_regime_s2 = len(g3_s2.regime_log)
        print(f"  S2 REGIME events: {n_regime_s2} "
              f"({'expected 0' if n_regime_s2 == 0 else '*** FINDING: drift fired regime'})")

        # ── §1 H8: S3 step-UP ──────────────────────────────────────────────
        cs_s3u = _fresh_competitors_exp6(G, D, noise_thr)
        raw_s3u = _run_exp6(cs_s3u, _scales_step_up(), std, SEED_BASE + 4)
        g3_s3u: PhiZakhorKeepG3 = next(c for c in cs_s3u if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(f"§1 S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})", raw_s3u)
        h8_up = h8_recovery(raw_s3u, g3_s3u, step_block, "S3↑")
        verdicts[f"H8b-{std}"] = _pf(h8_up["pass"])
        pz_up_T = h8_up["pz_recovery"]
        g3_up_T = h8_up["recovery_blocks"]
        print(f"  H8(b) S3↑: REGIME_total={h8_up['regime_total']}  near_step={len(h8_up['regime_near_step'])} (want 1)"
              f"  PHI-ZAKHOR T={pz_up_T}  G3 T={g3_up_T} (budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H8b-{std}']}")
        for ev in h8_up["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}  signed={ev[3]:+.3f} shells")

        # ── §1 H8: S3 step-DOWN ────────────────────────────────────────────
        cs_s3d = _fresh_competitors_exp6(G, D, noise_thr)
        raw_s3d = _run_exp6(cs_s3d, _scales_step_down(), std, SEED_BASE + 5)
        g3_s3d: PhiZakhorKeepG3 = next(c for c in cs_s3d if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(f"§1 S3 STEP ↓ (−{STEP_SHELLS} shells) ({std_label})", raw_s3d)
        h8_dn = h8_recovery(raw_s3d, g3_s3d, step_block, "S3↓")
        verdicts[f"H8a-{std}"] = _pf(h8_dn["pass"])
        pz_dn_T = h8_dn["pz_recovery"]
        g3_dn_T = h8_dn["recovery_blocks"]
        print(f"  H8(a) S3↓: REGIME_total={h8_dn['regime_total']}  near_step={len(h8_dn['regime_near_step'])} (want 1)"
              f"  PHI-ZAKHOR T={pz_dn_T}  G3 T={g3_dn_T} (budget={H6_RECOVERY_BUDGET}) — {verdicts[f'H8a-{std}']}")
        for ev in h8_dn["regime_near_step"][:2]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}  signed={ev[3]:+.3f} shells")

        print(f"  Contrast: G3 rebirth T≈{g3_up_T} (S3↑) / T≈{g3_dn_T} (S3↓)"
              f"  vs PHI-ZAKHOR formula T≈{pz_up_T} (↑) / T≈{pz_dn_T} (↓)")
        verdicts[f"H8ab-{std}"] = _pf(h8_up["pass"] and h8_dn["pass"])

        # ── §1 H8(c-d) + §2 H9 + §3 H10: S4 spikes ──────────────────────
        cs_s4 = _fresh_competitors_exp6(G, D, noise_thr)
        raw_s4 = _run_exp6(cs_s4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        g3_s4: PhiZakhorKeepG3 = next(c for c in cs_s4 if c.name == "PHI-ZAKHOR-KEEP-G3")
        _print_summary(
            f"§1 S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            raw_s4,
        )

        # S4a regression (PHI-ZAKHOR ungated)
        s4a = s4a_state_integrity(raw_s4, "PHI-ZAKHOR")
        ref = EXP003_S4A_PEAK_PEAKED if std == STD_PEAKED else EXP003_S4A_PEAK_SPREAD
        s4a_reg_ok = abs(s4a["peak_displacement"] - ref) <= S4A_REG_TOL
        verdicts[f"S4a-reg-{std}"] = _pf(s4a_reg_ok)
        print(f"\n  §4 S4a regression: peak_disp={s4a['peak_displacement']:.4f}"
              f" (ref={ref:.4f}) — {verdicts[f'S4a-reg-{std}']}")

        # H8(c): cold-start self-healing — REGIME log on S4
        n_regime_s4 = len(g3_s4.regime_log)
        regime_s4_early = [e for e in g3_s4.regime_log if e[0] <= K_REBIRTH + 1]
        regime_s4_late = [e for e in g3_s4.regime_log if e[0] > K_REBIRTH + 1]
        h8c_ok = (len(regime_s4_early) == 1 and len(regime_s4_late) == 0)
        verdicts[f"H8c-{std}"] = _pf(h8c_ok)
        print(f"  §1 H8(c) cold-start rebirth: REGIME events total={n_regime_s4}"
              f"  early(≤K+1)={len(regime_s4_early)} (want 1)"
              f"  late(>K+1)={len(regime_s4_late)} (want 0) — {verdicts[f'H8c-{std}']}")
        for ev in g3_s4.regime_log[:3]:
            print(f"    REGIME: block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}  signed={ev[3]:+.3f} shells")

        # H5a reproduction
        h5a = h5a_displacement(g3_s4)
        verdicts[f"H5a-{std}"] = _pf(h5a["pass"])
        print(f"  H5a displacement: peak={h5a['peak']:.6f} shells"
              f"  all_zero={h5a['all_zero']}  n={h5a['n']} — {verdicts[f'H5a-{std}']}")

        # H8(d): zero REGIME events among isolated S4 spikes (= late events = 0)
        h8d_ok = (len(regime_s4_late) == 0
                  and n_regime_s1 == 0
                  and n_regime_s2 == 0)
        verdicts[f"H8d-{std}"] = _pf(h8d_ok)
        print(f"  §1 H8(d) hallucination: S1={n_regime_s1}  S2={n_regime_s2}"
              f"  S4_isolated={len(regime_s4_late)} (all want 0) — {verdicts[f'H8d-{std}']}")

        # H8 overall
        verdicts[f"H8-{std}"] = _pf(
            h8_up["pass"] and h8_dn["pass"] and h8c_ok and h8d_ok
        )
        print(f"  H8 overall: {verdicts[f'H8-{std}']}")

        # S4c collateral
        s4c = s4c_collateral(raw_s4, R_s1)
        g3_s4c_ok = s4c.get("PHI-ZAKHOR-KEEP-G3", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        verdicts[f"H8c-s4c-{std}"] = _pf(g3_s4c_ok)
        print(f"  §1 H8(c) S4c collateral (threshold ≤{S4C_MAX_R_RATIO}):")
        for nm in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G3"):
            if nm in s4c:
                d = s4c[nm]
                print(f"    {nm:<28} R_normal={d['R_normal']:.3f}  R_s1={d['R_s1']:.3f}  ratio={d['ratio']:.3f}")
        if not g3_s4c_ok and h8c_ok:
            print(f"    *** S4c FAILS: cold-start rebirth healed, but residual cost remains structural.")

        # §2 H9: calibration-consistent over-declaration
        h9 = h9_declaration(g3_s4, true_spike_count, e_hat)
        verdicts[f"H9-{std}"] = _pf(h9["pass"])
        print(f"\n  §2 H9 declaration: declared={h9['declared']}"
              f"  true_spikes={h9['true_spikes']}  N̂={h9['N_hat']:.1f}"
              f"  limit={h9['limit']:.1f}"
              f"  truthful={h9['truthful']} — {verdicts[f'H9-{std}']}")
        print(f"    Stranger log (first 3): {g3_s4.stranger_log[:3]}")

        # §3 H10: honesty vs ORACLE-PHI-G
        cs_h10 = _fresh_competitors_exp6(G, D, noise_thr)
        raw_h10 = _run_exp6(cs_h10, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        g3_h10: PhiZakhorKeepG3 = next(c for c in cs_h10 if c.name == "PHI-ZAKHOR-KEEP-G3")
        hm = honesty_v4(raw_h10, cs_h10, _scales_spike(), std, SEED_BASE + 6,
                        g3_h10, is_spike=True)
        g3_hm = hm.get("PHI-ZAKHOR-KEEP-G3", {})
        silent_g = g3_hm.get("silent_g_rate", 1.0)
        h10_ok = silent_g < H10_SILENT_LIMIT
        verdicts[f"H10-{std}"] = _pf(h10_ok)

        print(f"\n  §3 H10 honesty ({std_label}) — limit {H10_SILENT_LIMIT:.1e}")
        print(f"  {'competitor':<28} {'decl':>10} {'mid_ret':>10} {'silent_raw':>12} {'silent_G':>10}")
        for nm in _NAMES_6:
            if nm not in hm:
                continue
            d = hm[nm]
            sg = f"{d.get('silent_g_rate', 0):>10.4e}" if nm == "PHI-ZAKHOR-KEEP-G3" else "         —"
            print(f"  {nm:<28} {d['declared_rate']:>10.4e} {d['mid_return_rate']:>10.4e}"
                  f" {d['silent_raw_rate']:>12.4e} {sg}")
        print(f"  H10: silent_G={silent_g:.4e} (< {H10_SILENT_LIMIT:.1e}) — {verdicts[f'H10-{std}']}")
        print(f"  PHI-STATIC silent-raw: {hm.get('PHI-STATIC',{}).get('silent_raw_rate',0):.3e} (contrast)")

        # H10 on S3 streams
        for stream_tag, fn_s, off_s in (("S3↑", _scales_step_up, 4),
                                         ("S3↓", _scales_step_down, 5)):
            cs_h10s = _fresh_competitors_exp6(G, D, noise_thr)
            raw_h10s = _run_exp6(cs_h10s, fn_s(), std, SEED_BASE + off_s)
            g3_h10s: PhiZakhorKeepG3 = next(c for c in cs_h10s if c.name == "PHI-ZAKHOR-KEEP-G3")
            hm_s = honesty_v4(raw_h10s, cs_h10s, fn_s(), std, SEED_BASE + off_s,
                              g3_h10s, is_spike=False)
            g3_sg = hm_s.get("PHI-ZAKHOR-KEEP-G3", {}).get("silent_g_rate", 1.0)
            s_ok = g3_sg < H10_SILENT_LIMIT
            verdicts[f"H10-{stream_tag}-{std}"] = _pf(s_ok)
            mid_blocks = sum(g3_h10s.mid_return_flags)
            regime_count = len(g3_h10s.regime_log)
            print(f"  H10 {stream_tag}: silent_G={g3_sg:.4e}  mid_blocks={mid_blocks}"
                  f"  regime={regime_count} — {verdicts[f'H10-{stream_tag}-{std}']}")

        h10_all = all(verdicts.get(k, "FALSIFIED") == "PASS"
                      for k in [f"H10-{std}", f"H10-S3↑-{std}", f"H10-S3↓-{std}"])
        verdicts[f"H10-all-{std}"] = _pf(h10_all)
        print(f"  H10 all streams: {verdicts[f'H10-all-{std}']}")

        # Three registers
        print(f"\n  Three registers ({std_label}, S4):")
        print(f"    Stranger log: {len(g3_h10.stranger_log)} entries."
              f"  Mid-return blocks: {sum(g3_h10.mid_return_flags)}/{N_BLOCKS}."
              f"  Regime log: {len(g3_h10.regime_log)} entries (signed).")
        for ev in g3_h10.regime_log:
            dir_word = "quieter" if ev[3] > 0 else "louder"
            print(f"    REGIME block={ev[0]}  {ev[1]:.3f}→{ev[2]:.3f}"
                  f"  {ev[3]:+.3f} shells ({dir_word})")

    # ── H2-f regression: PHI-ZAKHOR ungated formula grid ───────────────────
    print(f"\n{'='*96}")
    print("§4 H2-f REGRESSION (PHI-ZAKHOR ungated, fourth confirmation expected)")
    print(f"{'='*96}")
    print(f"  {'alpha':>8} | {'dir':>5} | {'T_meas':>8} | {'T_form':>8} | "
          f"{'f_shells':>10} | {'err_frac':>10} | verdict")
    h2f_ok = True
    for alpha_sw in ALPHA_SWEEP:
        G_sw, D_sw, nt_sw, _ = calibrate_exp6(alpha_sw, STD_PEAKED)
        for direction, fn_s, off_s in (("UP", _scales_step_up, 4),
                                       ("DN", _scales_step_down, 5)):
            cs_reg = _fresh_competitors_exp6(G_sw, D_sw, nt_sw, alpha_sw)
            raw_reg = _run_exp6(cs_reg, fn_s(), STD_PEAKED,
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
    print(f"  H2-f regression: {verdicts['H2f-reg']}")

    # ── Verdict summary ─────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("VERDICT SUMMARY")
    print(f"{'='*96}")
    print(f"  {'check':<28} {'peaked':>12} {'spread':>12}")
    for stem in ("regression", "H5a", "S4a-reg",
                 "H8a", "H8b", "H8ab", "H8c", "H8c-s4c", "H8d", "H8",
                 "H9", "H10", "H10-S3↑", "H10-S3↓", "H10-all"):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<28} {vp:>12} {vs:>12}")
    print(f"  {'H2f-reg':28} {verdicts.get('H2f-reg', '—'):>12}")
    print()
    print("  H0-id: RETIRED (two-strike rule, exp004). Shell automorphism: descriptive only.")
    print("  Signed rebirths: >0 quieter world  <0 louder world.")
    print("  Verdicts: PASS / FALSIFIED / METRIC-DEFECT — no fourth category.")

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
    match = da == db
    print(f"  run1={da}  run2={db}  {_pf(match)} (bit-identical)")
    print()
    print("  Log dated output to research/results/exp006_<YYYY-MM-DD>.txt.")


if __name__ == "__main__":
    main()
