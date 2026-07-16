"""exp004_guard_and_return.py — The Guard Band, the Formula, and the Last Statement of H0-id.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Pre-registered: hypotheses and thresholds frozen on 2026-07-11 before any code
was written. See docs/exp004-pre-registration.md. The shamor discipline applies:
falsified stays falsified; no fourth verdict category.

Addresses exp003's root-cause: state tracks block-max mean, placing the codebook
ceiling at the median of arrivals. Fix: guard band G raises hi_effective by G
shells above the state. G and theta (mid-return threshold) are derived from the
calibration window, not swept.

New in this experiment:
  §1  Guard band G (derived, not tuned)
  §2  Recovery formula T(Δ) = (1/α)·ln(Δ/f)  — H2-f
  §3  Mid-return self-declaration (theta)
  §4  Bounded return theorem — H0-id final statement (two-strike retirement rule)
  H4  Headroom claim (S4c + overflow rate)
  H3-r Keeping claim retested with corrected geometry

Run from repository root:

    python3 research/exp004_guard_and_return.py

Bit-identical re-run asserted inline (SHA-256 prefix recorded).
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
sys.path.insert(0, _HERE)   # research/
sys.path.insert(0, _ROOT)   # repo root

from exp002_scale_memory import (  # noqa: E402
    N_BLOCKS, BLOCK_SIZE, LEVELS, ALPHA_PRIMARY, ALPHA_SWEEP,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    STEP_SHELLS, SPIKE_SHELLS, SPIKE_PERIOD, WARM_UP_BLOCKS,
    _LOG_PHI_INV, shell_coord, hi_from_state,
    _phi_codebook, _uniform_codebook, _snap, _block_stats,
    ZakhorScale, PhiZakhor, PhiStatic, GridZakhor, GridStatic, OraclePhi,
    _scales_stationary, _scales_drift_up, _scales_drift_down,
    _scales_step_up, _scales_step_down, _scales_spike,
    _mean, _phi_shell_exp, _consistency_fraction,
)
from exp003_identity_recovery import (  # noqa: E402
    ZakhorScaleLogged, safe_radius,
    h2_r_recovery, s4a_state_integrity, s4b_spike_fidelity, s4c_collateral,
    SPIKE_TRUE_FRAC,
    H3_SILENT_THRESHOLD, H3_MAX_DECL_MULTIPLE, S4C_MAX_R_RATIO,
    _stream_summary_6, _print_summary_6, _pf, _NAMES_6,
)
from core.phi_theory import PHI, PHI_INV, GOLDEN_ANGLE_TURNS
from core.phi_theory import _clipped_gauss, _lcg

# ── exp004 constants ──────────────────────────────────────────────────────────

CAL_BLOCKS: int = 256                    # calibration window length
CAL_SEED: int = SEED_BASE ^ 0x4CA1      # dedicated calibration seed
H2F_TOLERANCE: float = 0.25             # ±25% formula tolerance
H4_OVERFLOW_LIMIT: float = 0.015        # S1 overflow ≤ 1.5%
S4A_REGRESSION_TOLERANCE: float = 0.02  # ±0.02 shells vs exp003 0.188
EXP003_S4A_PEAK_PEAKED: float = 0.1880  # exp003 reference (peaked)
EXP003_S4A_PEAK_SPREAD: float = 0.1656  # exp003 reference (spread)
MAX_J: int = LEVELS - 9                 # 7 for LEVELS=16: shells j=0..7 positive side
H3R_SILENT_LIMIT: float = 0.001         # < 0.1%
H3R_DECL_LIMIT: float = H3_MAX_DECL_MULTIPLE * SPIKE_TRUE_FRAC

_NAMES_6_EXP4: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G", "PHI-STATIC",
    "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI",
)

# Compute MAX_J from the actual codebook structure (LEVELS=16 → 8 positive shells)
def _max_shell_idx(levels: int = LEVELS) -> int:
    """Number of distinct positive φ-shells in the codebook - 1 (max j index)."""
    book = _phi_codebook(1.0, levels)
    positives = sorted(set(v for v in book if v > 0), reverse=True)
    return len(positives) - 1

_MAX_J: int = _max_shell_idx()   # 7 for LEVELS=16


# ─────────────────────────────────────────────────────────────────────────────
# 1. Calibration: derive G and theta from stationary window
# ─────────────────────────────────────────────────────────────────────────────

def _percentile(data: List[float], q: float) -> float:
    """Linear-interpolation percentile, q ∈ [0, 1]."""
    if not data:
        return 0.0
    s = sorted(data)
    n = len(s)
    idx = q * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def calibrate(alpha: float = ALPHA_PRIMARY, std: float = STD_PEAKED) -> Tuple[float, float]:
    """Derive G (guard band) and theta (mid-return threshold) from S1 window.

    G = max(1, ceil(p99(d+)))  where d+ = max(0, obs - pre_state) [shell units]
    theta = 4 × p95(|delta|)   where delta = obs - pre_state

    The calibration runs CAL_BLOCKS=256 i.i.d. stationary blocks; this is the
    same regime as every stream's first 256 blocks by construction.
    """
    zs = ZakhorScale(alpha)
    rnd = _lcg(CAL_SEED)

    d_plus: List[float] = []
    abs_delta: List[float] = []

    for t in range(CAL_BLOCKS):
        block = [_clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        max_mag = max(abs(v) for v in block)
        obs = shell_coord(max_mag) if max_mag > 1e-300 else 0.0
        pre = zs.observe(block)  # pre-update state; state is updated inside

        if t == 0:
            # cold start: obs == pre == post; delta = 0, skip
            continue

        delta = obs - pre
        d_plus.append(max(0.0, delta))
        abs_delta.append(abs(delta))

    G_raw = _percentile(d_plus, 0.99)
    G = max(1.0, math.ceil(G_raw))
    theta = 4.0 * _percentile(abs_delta, 0.95)
    return G, theta


# ─────────────────────────────────────────────────────────────────────────────
# 2. PHI-ZAKHOR-KEEP-G: guarded + mid-return competitor
# ─────────────────────────────────────────────────────────────────────────────

class PhiZakhorKeepG:
    """PHI-ZAKHOR with guard band G, stranger declaration, and mid-return flag.

    State update: unchanged from PHI-ZAKHOR (normal alpha integration).
    hi_effective = hi_from_state(pre_state - G): ceiling raised G shells above state.
    Stranger: |v| > hi_effective → declared, not quantized, logged.
    Mid-return: |obs - pre_state| > theta → block flagged MID-RETURN (low-confidence).
    """

    name = "PHI-ZAKHOR-KEEP-G"
    is_phi = True

    def __init__(self, G: float, theta: float, alpha: float = ALPHA_PRIMARY) -> None:
        self._zs = ZakhorScaleLogged(alpha)
        self.G = G
        self.theta = theta
        self._block_idx: int = 0
        self.stranger_log: List[Tuple[int, float, float]] = []
        self.mid_return_log: List[int] = []       # block indices flagged
        self._mid_return_flags: List[bool] = []   # per block (for honesty)
        self._total_values: int = 0
        self._declared_count: int = 0

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        self._block_idx += 1
        max_mag = max(abs(v) for v in block) if block else 0.0
        obs = shell_coord(max_mag) if max_mag > 1e-300 else 0.0
        pre = self._zs.observe(block)   # causal; state updated inside

        # Mid-return flag
        is_mid = abs(obs - pre) > self.theta
        self._mid_return_flags.append(is_mid)
        if is_mid:
            self.mid_return_log.append(self._block_idx)

        # Guarded hi: subtracting G from exponent raises ceiling by G shells
        hi = hi_from_state(pre - self.G)
        book = _phi_codebook(hi, LEVELS)

        normal: List[float] = []
        for v in block:
            self._total_values += 1
            if abs(v) > hi:
                self._declared_count += 1
                sc = shell_coord(abs(v))
                overshoot = abs(v) / hi - 1.0
                self.stranger_log.append((self._block_idx, sc, overshoot))
            else:
                normal.append(v)

        mse, under, over = _block_stats(normal, book) if normal else (0.0, 0.0, 0.0)
        return mse, under, over, hi

    @property
    def declared_rate(self) -> float:
        return self._declared_count / self._total_values if self._total_values else 0.0

    @property
    def state_log(self) -> List[Tuple[float, float]]:
        return self._zs.state_log


def _fresh_competitors_exp4(G: float, theta: float, alpha: float = ALPHA_PRIMARY) -> List:
    return [
        PhiZakhor(alpha),
        PhiZakhorKeepG(G, theta, alpha),
        PhiStatic(),
        GridZakhor(alpha),
        GridStatic(),
        OraclePhi(),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stream runner (mirrors exp003._run_exp003 but with exp4 competitors)
# ─────────────────────────────────────────────────────────────────────────────

def _run_exp4(
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


def _hash_raw_exp4(raw: Dict) -> str:
    h = hashlib.sha256()
    for name in sorted(raw.keys()):
        for mse, under, over, _ in raw[name]:
            h.update(f"{mse:.15e}{under:.15e}{over:.15e}".encode())
    return h.hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# 4. H4: overflow rate measurement (§1b)
# ─────────────────────────────────────────────────────────────────────────────

def h4_overflow_rate(
    raw_s1: Dict[str, List[Tuple[float, float, float, float]]],
    G: float,
    std: float,
    seed: int,
) -> Dict[str, float]:
    """Fraction of S1 values with |v| > hi_guarded, per competitor.

    Re-runs the stream value-by-value to compute the overflow rate directly.
    """
    rnd = _lcg(seed)
    counts: Dict[str, int] = {}
    total = 0

    for t in range(N_BLOCKS):
        block = [_clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        total += len(block)
        for name in raw_s1:
            hi_c = raw_s1[name][t][3]
            overflow = sum(1 for v in block if abs(v) > hi_c)
            counts[name] = counts.get(name, 0) + overflow

    return {name: counts.get(name, 0) / total for name in raw_s1}


# ─────────────────────────────────────────────────────────────────────────────
# 5. H2-f: recovery formula check T(Δ) = (1/alpha) × ln(Δ/f)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_state_trace(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    name: str = "PHI-ZAKHOR",
) -> List[float]:
    """Pre-update state per block from raw results for a PHI-ZAKHOR variant.

    pre_state[t] = shell_coord(hi_returned[t]) because hi_from_state(pre) = hi
    → shell_coord(hi) = pre.
    """
    return [shell_coord(raw[name][t][3]) for t in range(N_BLOCKS)]


def h2_f_check(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    step_block: int,
    alpha: float,
    direction: str = "UP",
) -> Dict[str, object]:
    """Formula check: T_measured vs T_formula = (1/alpha) × ln(Δ/f).

    f = |pre_state(t_rec) - equilibrium_new| (state deviation at R-crossing).
    Δ = STEP_SHELLS (step size in shells).
    T_measured = first block where R(t) ≤ 2 × R̄ for 8 consecutive blocks.

    Checks |T_formula - T_measured| / T_measured ≤ H2F_TOLERANCE.
    """
    # R(t) crossing via h2_r_recovery
    rec_data = h2_r_recovery(raw, step_block, pre_window=256)
    pz = rec_data.get("PHI-ZAKHOR", {})
    T_measured = pz.get("recovery_blocks")
    if T_measured is None or T_measured == 0:
        return {"T_measured": T_measured, "T_formula": None, "f": None,
                "error_frac": None, "pass": False}

    # State trace
    pre_states = _extract_state_trace(raw, "PHI-ZAKHOR")
    t_rec = step_block + T_measured

    # New equilibrium: mean of last 256 pre-states (fully converged)
    eq_new = _mean(pre_states[max(0, N_BLOCKS - 256):])

    f = abs(pre_states[t_rec] - eq_new) if t_rec < N_BLOCKS else None
    if f is None or f < 1e-6:
        # Too small to measure — formula degenerates (f→0 iff T→∞)
        return {"T_measured": T_measured, "T_formula": None, "f": f,
                "error_frac": None, "pass": None, "note": "f≈0 (T→∞ limit)"}

    T_formula = (1.0 / alpha) * math.log(STEP_SHELLS / f)
    error_frac = abs(T_formula - T_measured) / T_measured
    return {
        "T_measured": T_measured,
        "T_formula": round(T_formula, 1),
        "f": round(f, 4),
        "error_frac": round(error_frac, 4),
        "pass": error_frac <= H2F_TOLERANCE,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. H0-id bounded: interior return correctness + edge declaration
# ─────────────────────────────────────────────────────────────────────────────

def h0_id_interior(m: int, n_samples: int = 4096) -> Dict[str, object]:
    """Bounded return theorem metrics at static drift of m shells.

    Interior shells: j_old ∈ [m, _MAX_J] (both j and j-m exist in codebook).
    Edge shells:     j_old ∈ [0, m-1]    (drift-image j_old-m would fall out).

    Frozen metrics:
      interior_correctness (φ) ≥ 0.99 (PASS threshold)
      edge_declaration_rate: reported, not thresholded
      interior_feasibility: fraction of interior values with consistent shift

    METRIC-DEFECT if no interior shells exist.
    """
    if _MAX_J < m:
        return {
            "defect": True,
            "reason": f"MAX_J={_MAX_J} < m={m}: no interior shells exist",
        }

    hi_old = 1.0
    hi_new = PHI_INV ** m
    book_phi_old = _phi_codebook(hi_old, LEVELS)
    book_phi_new = _phi_codebook(hi_new, LEVELS)
    book_uni_old = _uniform_codebook(hi_old, LEVELS)
    book_uni_new = _uniform_codebook(hi_new, LEVELS)

    rnd = _lcg(SEED_BASE ^ 0x4004)
    values = [_clipped_gauss(rnd, std=STD_PEAKED) for _ in range(n_samples)]

    # φ: interior correctness and edge declaration
    phi_int_correct = phi_int_feas = phi_int_total = 0
    phi_edge = phi_all = 0
    for v in values:
        _, rv_old = _snap(v, book_phi_old)
        _, rv_new = _snap(v, book_phi_new)
        j_old = _phi_shell_exp(rv_old, hi_old)
        j_new = _phi_shell_exp(rv_new, hi_new)
        if j_old is None or j_old < 0:
            continue
        phi_all += 1
        if j_old < m:          # edge shell
            phi_edge += 1
        else:                  # interior shell
            phi_int_total += 1
            if j_new is not None and j_new >= 0:
                # Return correctness: j_new + m should equal j_old
                if j_new + m == j_old:
                    phi_int_correct += 1
                    phi_int_feas += 1  # consistent shift ↔ feasible interior

    phi_int_correctness = phi_int_correct / phi_int_total if phi_int_total else 0.0
    phi_int_feasibility = phi_int_feas / phi_int_total if phi_int_total else 0.0
    phi_edge_rate = phi_edge / phi_all if phi_all else 0.0

    # Uniform: interior metrics (reference, no threshold)
    uni_int_correct = uni_int_feas = uni_int_total = 0
    uni_edge = uni_all = 0
    for v in values:
        _, rv_old = _snap(v, book_uni_old)
        _, rv_new = _snap(v, book_uni_new)
        j_old_u = _phi_shell_exp(rv_old, hi_old)
        j_new_u = _phi_shell_exp(rv_new, hi_new)
        if j_old_u is None or j_old_u < 0:
            continue
        uni_all += 1
        if j_old_u < m:
            uni_edge += 1
        else:
            uni_int_total += 1
            if j_new_u is not None and j_new_u + m == j_old_u:
                uni_int_correct += 1
                uni_int_feas += 1

    return {
        "defect": False,
        "phi_int_correctness": phi_int_correctness,
        "phi_int_feasibility": phi_int_feasibility,
        "phi_edge_rate": phi_edge_rate,
        "phi_int_n": phi_int_total,
        "uni_int_correctness": uni_int_correct / uni_int_total if uni_int_total else 0.0,
        "uni_int_feasibility": uni_int_feas / uni_int_total if uni_int_total else 0.0,
        "uni_edge_rate": uni_edge / uni_all if uni_all else 0.0,
        "pass_correctness": phi_int_correctness >= 0.99,
        "phi_specific": (
            abs(phi_int_correctness - (uni_int_correct / max(uni_int_total, 1))) > 0.05
            or abs(phi_int_feasibility - (uni_int_feas / max(uni_int_total, 1))) > 0.05
        ),
    }


def h0_id_interior_s2_feasibility(
    raw_s2: Dict[str, List[Tuple[float, float, float, float]]],
    m_int: int = 1,
) -> Dict[str, float]:
    """Interior feasibility averaged over S2↑ blocks for a given interior-m floor.

    At each block, values with j_old ≥ m_effective_floor (interior) are tested.
    We use m=1 as the floor so all non-outermost shells are interior.
    """
    rnd = _lcg(SEED_BASE ^ 0x5247)
    test_vals = [_clipped_gauss(rnd, std=STD_PEAKED) for _ in range(512)]

    phi_feas_blocks: List[float] = []
    uni_feas_blocks: List[float] = []

    for t in range(N_BLOCKS):
        hi_phi = raw_s2["PHI-ZAKHOR"][t][3]
        hi_uni = raw_s2["GRID-ZAKHOR"][t][3]
        hi_oracle = raw_s2["ORACLE-PHI"][t][3]
        if hi_oracle < 1e-300:
            continue

        # Effective drift from oracle (which sees true block max)
        m_eff = max(1, abs(round(shell_coord(hi_phi) - shell_coord(hi_oracle))))

        book_phi_now = _phi_codebook(hi_phi, LEVELS)
        book_phi_or = _phi_codebook(hi_oracle, LEVELS)
        book_uni_now = _uniform_codebook(hi_uni, LEVELS)
        book_uni_or = _uniform_codebook(hi_oracle, LEVELS)

        def _int_feas(vals, bk_now, hi_now, bk_or, hi_or, m):
            ok = tot = 0
            for v in vals:
                _, rv_n = _snap(v, bk_now)
                _, rv_o = _snap(v, bk_or)
                j_n = _phi_shell_exp(rv_n, hi_now)
                j_o = _phi_shell_exp(rv_o, hi_or)
                if j_n is None or j_o is None or j_n < 0 or j_o < 0:
                    continue
                if j_n < m:     # edge: skip
                    continue
                tot += 1
                if j_o + m == j_n:  # consistent interior return
                    ok += 1
            return ok / tot if tot else 0.0

        phi_feas_blocks.append(_int_feas(
            test_vals, book_phi_now, hi_phi, book_phi_or, hi_oracle, m_eff
        ))
        uni_feas_blocks.append(_int_feas(
            test_vals, book_uni_now, hi_uni, book_uni_or, hi_oracle, m_eff
        ))

    return {
        "phi_int_feas_s2": _mean(phi_feas_blocks),
        "uni_int_feas_s2": _mean(uni_feas_blocks),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Honesty v2: declared + mid-return + silent-error
# ─────────────────────────────────────────────────────────────────────────────

def honesty_v2(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> Dict[str, Dict[str, float]]:
    """Per-competitor declared-loss, mid-return, and silent-error rates.

    Silent-error (revised): err > 10× oracle AND NOT (declared OR mid-return).
    Mid-return applies only to PHI-ZAKHOR-KEEP-G; other competitors have 0.
    """
    keep_g = next((c for c in competitors if c.name == "PHI-ZAKHOR-KEEP-G"), None)

    rnd = _lcg(seed)
    declared: Dict[str, int] = {c.name: 0 for c in competitors}
    mid_return: Dict[str, int] = {c.name: 0 for c in competitors}
    silent: Dict[str, int] = {c.name: 0 for c in competitors}
    total_values = 0

    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)

        oracle_hi = raw["ORACLE-PHI"][t][3]
        oracle_book = _phi_codebook(max(oracle_hi, 1e-300), LEVELS)

        is_mid_block = (keep_g is not None
                        and t < len(keep_g._mid_return_flags)
                        and keep_g._mid_return_flags[t])

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
                is_decl = (c.name == "PHI-ZAKHOR-KEEP-G" and abs(v) > hi_c)
                is_mr = (c.name == "PHI-ZAKHOR-KEEP-G" and is_mid_block)

                if is_decl:
                    declared[c.name] += 1
                else:
                    _, rv = _snap(v, book_c)
                    err = (v - rv) ** 2
                    if err > H3_SILENT_THRESHOLD * oracle_err + 1e-30:
                        if not is_mr:
                            silent[c.name] += 1
                if is_mr and not is_decl:
                    mid_return[c.name] += 1

    n = total_values
    return {
        c.name: {
            "declared_rate": declared[c.name] / n,
            "mid_return_rate": mid_return[c.name] / n,
            "silent_error_rate": silent[c.name] / n,
        }
        for c in competitors
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. Helpers: print and verdicts
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary_exp4(label: str, raw: Dict) -> None:
    summary = _stream_summary_6(raw)
    print(f"\n{label}")
    print("-" * 82)
    print(f"  {'competitor':<24} {'MSE':>14} {'underflow':>12} {'overflow':>12}")
    for name in _NAMES_6_EXP4:
        if name not in summary:
            continue
        s = summary[name]
        print(f"  {name:<24} {s['mse']:>14.4e} {s['underflow']:>12.4e} {s['overflow']:>12.4e}")


def _all_runs_exp4(G: float, theta: float, alpha: float = ALPHA_PRIMARY) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for std in (STD_PEAKED, STD_SPREAD):
        for tag, fn, off, spike in (
            (f"S1-{std}",   _scales_stationary,  1, False),
            (f"S2up-{std}", _scales_drift_up,     2, False),
            (f"S2dn-{std}", _scales_drift_down,   3, False),
            (f"S3up-{std}", _scales_step_up,      4, False),
            (f"S3dn-{std}", _scales_step_down,    5, False),
            (f"S4-{std}",   _scales_spike,        6, True),
        ):
            cs = _fresh_competitors_exp4(G, theta, alpha)
            out[tag] = _run_exp4(cs, fn(), std, SEED_BASE + off, is_spike=spike)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 9. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 004 — The Guard Band, the Formula, and the Last Statement of H0-id")
    print("=" * 100)
    print(f"  Pre-registered thresholds frozen 2026-07-11. See docs/exp004-pre-registration.md.")
    print(f"  Two-strike retirement rule: H0-id is on its third and final operationalization.")

    step_block = N_BLOCKS // 2
    verdicts: Dict[str, str] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                           (STD_SPREAD,  f"spread(std={STD_SPREAD})")):

        # ── Calibration ────────────────────────────────────────────────────
        G, theta = calibrate(ALPHA_PRIMARY, std)
        print(f"\n{'━'*100}")
        print(f"  Distribution: {std_label}")
        print(f"  Calibration (CAL_BLOCKS={CAL_BLOCKS}, alpha=1/{round(1/ALPHA_PRIMARY)}): "
              f"G={G:.1f} shells  theta={theta:.4f}")
        print("━" * 100)

        # ── §5 Regression gate: S1 stationary ──────────────────────────────
        cs_s1 = _fresh_competitors_exp4(G, theta)
        raw_s1 = _run_exp4(cs_1 := cs_s1, _scales_stationary(), std, SEED_BASE + 1)
        keep_g_s1: PhiZakhorKeepG = next(c for c in cs_1 if c.name == "PHI-ZAKHOR-KEEP-G")
        _print_summary_exp4(f"§5 S1 STATIONARY ({std_label})", raw_s1)

        # Regression: KEEP-G MSE vs exp003 PHI-ZAKHOR (ref: 4.41e-4 peaked, 1.73e-3 spread)
        pz_mse = _mean([raw_s1["PHI-ZAKHOR"][t][0] for t in range(N_BLOCKS)])
        kg_mse = _mean([raw_s1["PHI-ZAKHOR-KEEP-G"][t][0] for t in range(N_BLOCKS)])
        reg_ok = kg_mse <= pz_mse * 1.05
        verdicts[f"regression-{std}"] = _pf(reg_ok)
        print(f"  Regression gate: PHI-ZAKHOR {pz_mse:.4e}  PHI-ZAKHOR-KEEP-G {kg_mse:.4e} — {verdicts[f'regression-{std}']}")
        if not reg_ok:
            print(f"  *** REGRESSION FAIL: guard band degrades S1 by >5%. Halting.")
            return

        # S1 oracle-relative R (for S4c baseline)
        oracle_mse_s1 = [raw_s1["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]
        R_s1: Dict[str, float] = {}
        for name in _NAMES_6_EXP4:
            if name in raw_s1 and name != "ORACLE-PHI":
                R_s1[name] = _mean([
                    raw_s1[name][t][0] / max(oracle_mse_s1[t], 1e-30)
                    for t in range(N_BLOCKS)
                ])

        # §1b: overflow rate on S1 with guard band
        ovfl = h4_overflow_rate(raw_s1, G, std, SEED_BASE + 1)
        print(f"  §1b Overflow rates on S1 (threshold ≤ {H4_OVERFLOW_LIMIT:.1%}):")
        for name in ("PHI-ZAKHOR-KEEP-G", "PHI-ZAKHOR"):
            if name in ovfl:
                print(f"    {name:<24} {ovfl[name]:.4%}")
        kg_overflow_ok = ovfl.get("PHI-ZAKHOR-KEEP-G", 1.0) <= H4_OVERFLOW_LIMIT
        verdicts[f"H4-overflow-{std}"] = _pf(kg_overflow_ok)

        # ── §4 H0-id bounded: interior return correctness ───────────────────
        print(f"\n§4 H0-id BOUNDED RETURN ({std_label})  [MAX_J={_MAX_J}, two-strike retirement rule]")
        print("-" * 100)
        print(f"  {'m':>4} | {'φ-int-corr':>12} | {'φ-int-feas':>12} | {'φ-edge-rate':>12} "
              f"| {'uni-int-corr':>13} | {'uni-edge-rate':>13} | verdict")
        h0_pass = True
        h0_phi_specific = True
        for m in (1, 2, 4):
            r = h0_id_interior(m)
            if r.get("defect"):
                v = "METRIC-DEFECT"
                verdicts[f"H0id-m{m}-{std}"] = v
                print(f"  {m:>4} | METRIC-DEFECT: {r['reason']}")
                continue
            corr_ok = r["pass_correctness"]
            h0_pass = h0_pass and corr_ok
            h0_phi_specific = h0_phi_specific and r["phi_specific"]
            v = _pf(corr_ok and r["phi_specific"])
            verdicts[f"H0id-m{m}-{std}"] = v
            print(f"  {m:>4} | {r['phi_int_correctness']:>12.4f} | {r['phi_int_feasibility']:>12.4f} "
                  f"| {r['phi_edge_rate']:>12.4f} | {r['uni_int_correctness']:>13.4f} "
                  f"| {r['uni_edge_rate']:>13.4f} | {v}")

        # S2 interior feasibility
        cs_s2 = _fresh_competitors_exp4(G, theta)
        raw_s2 = _run_exp4(cs_s2, _scales_drift_up(), std, SEED_BASE + 2)
        s2_feas = h0_id_interior_s2_feasibility(raw_s2, m_int=1)
        s2_int_feas_ok = s2_feas["phi_int_feas_s2"] >= 0.80
        verdicts[f"H0id-feas-int-{std}"] = _pf(s2_int_feas_ok)
        print(f"\n  Interior feasibility on S2↑: φ={s2_feas['phi_int_feas_s2']:.4f} "
              f"uni={s2_feas['uni_int_feas_s2']:.4f}  (threshold φ≥0.80) — "
              f"{verdicts[f'H0id-feas-int-{std}']}")

        all_corr_pass = all(
            verdicts.get(f"H0id-m{m}-{std}") == "PASS"
            for m in (1, 2, 4)
            if verdicts.get(f"H0id-m{m}-{std}") != "METRIC-DEFECT"
        )
        h0_final = "PASS" if all_corr_pass and s2_int_feas_ok and h0_phi_specific else "FALSIFIED"
        verdicts[f"H0id-bounded-{std}"] = h0_final
        print(f"  H0-id bounded overall: {h0_final}")
        if h0_final == "FALSIFIED":
            print("  *** TWO-STRIKE RETIREMENT: H0-id FALSIFIED under three operationalizations.")
            print("      Shell automorphism (0.91 vs 0.22) stands as a descriptive property.")
            print("      No further H0-id restatement permitted.")

        # ── §2 H2-f: formula check ──────────────────────────────────────────
        print(f"\n§2 H2-f RECOVERY FORMULA T(Δ)=(1/α)·ln(Δ/f), ±25% ({std_label})")
        print(f"  {'alpha':>8} | {'dir':>5} | {'T_meas':>8} | {'T_form':>8} | "
              f"{'f_shells':>10} | {'err_frac':>10} | verdict")
        h2f_all_ok = True
        for alpha_sw in ALPHA_SWEEP:
            for direction, fn_s, off_s in (("UP", _scales_step_up, 4),
                                           ("DN", _scales_step_down, 5)):
                cs_f = _fresh_competitors_exp4(G, theta, alpha_sw)
                raw_f = _run_exp4(cs_f, fn_s(), std, SEED_BASE + off_s + round(1/alpha_sw))
                fc = h2_f_check(raw_f, step_block, alpha_sw, direction)
                T_m = fc.get("T_measured")
                T_f = fc.get("T_formula")
                f_v = fc.get("f")
                ef = fc.get("error_frac")
                p = fc.get("pass")
                T_m_s = f"{T_m}" if T_m is not None else ">N"
                T_f_s = f"{T_f:.1f}" if T_f is not None else "—"
                f_s = f"{f_v:.4f}" if f_v is not None else "—"
                ef_s = f"{ef:.3f}" if ef is not None else "—"
                v = _pf(p) if p is not None else "METRIC-DEFECT"
                if p is False:
                    h2f_all_ok = False
                print(f"  {alpha_sw:>8.4f} | {direction:>5} | {T_m_s:>8} | {T_f_s:>8} "
                      f"| {f_s:>10} | {ef_s:>10} | {v}")
        verdicts[f"H2f-{std}"] = _pf(h2f_all_ok)
        print(f"  H2-f overall: {verdicts[f'H2f-{std}']}")
        print(f"  Asymmetry: exp003 found UP=156 DOWN=55 (both ~1/alpha, now expected symmetric)")

        # S3 streams
        _print_summary_exp4(f"S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})",
                            _run_exp4(_fresh_competitors_exp4(G, theta),
                                      _scales_step_up(), std, SEED_BASE + 4))

        # ── §3/§1 H4 + H3-r: S4 spike streams ─────────────────────────────
        cs_s4 = _fresh_competitors_exp4(G, theta)
        raw_s4 = _run_exp4(cs_s4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        keep_g_s4: PhiZakhorKeepG = next(c for c in cs_s4 if c.name == "PHI-ZAKHOR-KEEP-G")
        _print_summary_exp4(
            f"§1/§3 S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            raw_s4,
        )

        # S4a regression
        s4a = s4a_state_integrity(raw_s4, "PHI-ZAKHOR")
        exp003_ref = EXP003_S4A_PEAK_PEAKED if std == STD_PEAKED else EXP003_S4A_PEAK_SPREAD
        s4a_reg_ok = abs(s4a["peak_displacement"] - exp003_ref) <= S4A_REGRESSION_TOLERANCE
        verdicts[f"S4a-reg-{std}"] = _pf(s4a_reg_ok)
        print(f"\n  S4a regression: peak_disp={s4a['peak_displacement']:.4f} "
              f"(exp003 ref={exp003_ref:.4f}, tol=±{S4A_REGRESSION_TOLERANCE}) — "
              f"{verdicts[f'S4a-reg-{std}']}")
        if not s4a_reg_ok:
            print("  *** S4a REGRESSION: guard band leaked into state path. Halt interpretation.")
            return

        # H4: S4c collateral
        s4c = s4c_collateral(raw_s4, R_s1)
        pz_s4c_ok = s4c.get("PHI-ZAKHOR", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        kg_s4c_ok = s4c.get("PHI-ZAKHOR-KEEP-G", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        h4_s4c_ok = pz_s4c_ok and kg_s4c_ok
        verdicts[f"H4-S4c-{std}"] = _pf(h4_s4c_ok)
        print(f"  §1 H4 — S4c collateral (normal-block R / S1 R, threshold ≤{S4C_MAX_R_RATIO}):")
        for name in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP-G", "GRID-ZAKHOR"):
            if name in s4c:
                d = s4c[name]
                print(f"    {name:<24} R_normal={d['R_normal']:.3f}  R_s1={d['R_s1']:.3f}  ratio={d['ratio']:.3f}")
        verdicts[f"H4-{std}"] = _pf(h4_s4c_ok and kg_overflow_ok)
        print(f"  H4 (S4c + overflow): {verdicts[f'H4-{std}']}")

        # S4b spike fidelity
        s4b = s4b_spike_fidelity(raw_s4, std)
        print(f"  S4b spike fidelity (spike-MSE / normal-MSE):")
        for name in _NAMES_6_EXP4:
            if name in s4b:
                print(f"    {name:<24} {s4b[name]:>10.2f}×")

        # §3 Honesty v2
        cs_hv2 = _fresh_competitors_exp4(G, theta)
        raw_hv2 = _run_exp4(cs_hv2, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        keep_g_hv2: PhiZakhorKeepG = next(c for c in cs_hv2 if c.name == "PHI-ZAKHOR-KEEP-G")
        hm = honesty_v2(raw_hv2, cs_hv2, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        print(f"\n  §3 Honesty v2 ({std_label}) — spike fraction: {SPIKE_TRUE_FRAC:.2e}, "
              f"H3-r decl limit: {H3R_DECL_LIMIT:.2e}")
        print(f"  {'competitor':<24} {'decl_rate':>12} {'mid_ret_rate':>14} {'silent_err':>12}")
        for name in _NAMES_6_EXP4:
            if name not in hm:
                continue
            d = hm[name]
            print(f"  {name:<24} {d['declared_rate']:>12.4e} "
                  f"{d['mid_return_rate']:>14.4e} {d['silent_error_rate']:>12.4e}")

        kg_hm = hm.get("PHI-ZAKHOR-KEEP-G", {})
        h3r_silent_ok = kg_hm.get("silent_error_rate", 1.0) < H3R_SILENT_LIMIT
        h3r_decl_ok = kg_hm.get("declared_rate", 1.0) <= H3R_DECL_LIMIT
        h3r_collat_ok = s4c.get("PHI-ZAKHOR-KEEP-G", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        verdicts[f"H3r-{std}"] = _pf(h3r_silent_ok and h3r_decl_ok and h3r_collat_ok)
        print(f"\n  H3-r: silent_err {_pf(h3r_silent_ok)} | "
              f"over-declare {_pf(h3r_decl_ok)} | "
              f"collateral {_pf(h3r_collat_ok)} | "
              f"OVERALL {verdicts[f'H3r-{std}']}")

        # Stranger and mid-return logs
        slog = keep_g_hv2.stranger_log
        mrlog = keep_g_hv2.mid_return_log
        print(f"\n  Stranger log v2: {len(slog)} entries. "
              f"Mid-return log: {len(mrlog)} blocks flagged.")
        print(f"  First 3 strangers:")
        for entry in slog[:3]:
            print(f"    block={entry[0]:>5}  shell_coord={entry[1]:>8.3f}  overshoot={entry[2]:.3f}×")
        print(f"  First 3 mid-return blocks: {mrlog[:3]}")

    # ── Alpha sweep (H2-f formula across alphas) ────────────────────────────
    print(f"\n{'='*100}")
    print("ALPHA SWEEP — H2-f formula check (peaked distribution only)")
    print(f"{'='*100}")
    G_pk, theta_pk = calibrate(ALPHA_PRIMARY, STD_PEAKED)
    print(f"  Guard G={G_pk:.1f} theta={theta_pk:.4f} (peaked, already derived above)")
    print(f"  {'alpha':>8} | {'dir':>5} | {'T_meas':>8} | {'T_form':>8} | "
          f"{'f_shells':>10} | {'err_frac':>10} | {'pred_T':>8}")
    for alpha_sw in ALPHA_SWEEP:
        G_sw, theta_sw = calibrate(alpha_sw, STD_PEAKED)
        for direction, fn_s, off_s in (("UP", _scales_step_up, 4),
                                       ("DN", _scales_step_down, 5)):
            cs_sw = _fresh_competitors_exp4(G_sw, theta_sw, alpha_sw)
            raw_sw = _run_exp4(cs_sw, fn_s(), STD_PEAKED, SEED_BASE + off_s + round(1/alpha_sw))
            fc = h2_f_check(raw_sw, step_block, alpha_sw, direction)
            T_m = fc.get("T_measured")
            T_f = fc.get("T_formula")
            ef = fc.get("error_frac")
            pred = round(1.0 / alpha_sw) if T_m else "—"
            T_m_s = f"{T_m}" if T_m is not None else ">N"
            T_f_s = f"{T_f:.1f}" if T_f is not None else "—"
            ef_s = f"{ef:.3f}" if ef is not None else "—"
            v = _pf(fc.get("pass")) if fc.get("pass") is not None else "METRIC-DEFECT"
            print(f"  {alpha_sw:>8.4f} | {direction:>5} | {T_m_s:>8} | {T_f_s:>8} "
                  f"| {fc.get('f', 0):>10.4f} | {ef_s:>10} | {pred:>8}  {v}")

    # ── Verdict summary ─────────────────────────────────────────────────────
    print(f"\n{'='*100}")
    print("VERDICT SUMMARY")
    print(f"{'='*100}")
    print(f"  {'check':<30} {'peaked':>12} {'spread':>12}")
    for stem in ("regression", "H4-overflow", "H4-S4c", "H4",
                 "H0id-m1", "H0id-m2", "H0id-m4", "H0id-feas-int", "H0id-bounded",
                 "H2f", "H3r", "S4a-reg"):
        vp = verdicts.get(f"{stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{stem}-{STD_SPREAD}", "—")
        print(f"  {stem:<30} {vp:>12} {vs:>12}")

    print()
    h0_peaked = verdicts.get(f"H0id-bounded-{STD_PEAKED}", "—")
    h0_spread = verdicts.get(f"H0id-bounded-{STD_SPREAD}", "—")
    if h0_peaked == "FALSIFIED" or h0_spread == "FALSIFIED":
        print("  ═══════════════════════════════════════════════════════════════════")
        print("  H0-id RETIRED after three falsifications (exp002 MSE form;")
        print("  exp003 edge-conflation form; exp004 bounded interior form).")
        print("  The shell automorphism (0.91 vs 0.22 at m=1) stands as a")
        print("  descriptive geometric property of the φ-codebook, with no")
        print("  load-bearing role in the architecture. No exp005 restatement.")
        print("  ═══════════════════════════════════════════════════════════════════")
    else:
        print("  H0-id PASSES its final operationalization. Shell automorphism")
        print("  confirmed as a load-bearing property of the bounded return theorem.")

    print()
    print("  Verdicts: PASS / FALSIFIED / METRIC-DEFECT — no fourth category.")
    print("  All prior experiment verdicts stand as recorded.")

    # ── Reproducibility ─────────────────────────────────────────────────────
    print(f"\n{'='*100}")
    print("REPRODUCIBILITY")
    G_rep, th_rep = calibrate(ALPHA_PRIMARY, STD_PEAKED)
    run_A = _all_runs_exp4(G_rep, th_rep)
    run_B = _all_runs_exp4(G_rep, th_rep)
    ha = hashlib.sha256()
    hb = hashlib.sha256()
    for k in sorted(run_A):
        ha.update(_hash_raw_exp4(run_A[k]).encode())
        hb.update(_hash_raw_exp4(run_B[k]).encode())
    da, db = ha.hexdigest()[:16], hb.hexdigest()[:16]
    match = da == db
    print(f"  run1={da}  run2={db}  {_pf(match)} (bit-identical)")
    if not match:
        print("  *** REPRODUCIBILITY FAIL")
    print()
    print("  Log dated output to research/results/exp004_<YYYY-MM-DD>.txt.")


if __name__ == "__main__":
    main()
