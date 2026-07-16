"""exp003_identity_recovery.py — Identity, Recovery, and the Declared Stranger.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Pre-registered: hypotheses and thresholds frozen on 2026-07-11 before any code
was written. See docs/exp003-pre-registration.md. Metric failures record
as FALSIFIED or METRIC-DEFECT; no quiet substitution.

Corrects three metric defects from exp002:
  H0  → H0-id: shell-consistency + return feasibility/correctness
  H2  → H2-r:  oracle-relative ratio R(t) = MSE / MSE_ORACLE (removes scale bias)
  S4  → S4a/b/c: state integrity / spike fidelity / collateral damage (normal only)
  New → H3 / PHI-ZAKHOR-KEEP: declared-stranger branch + honesty metrics

Run from repository root:

    python3 research/exp003_identity_recovery.py

Bit-identical re-run is asserted inline (SHA-256 prefix recorded).
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
sys.path.insert(0, _HERE)   # research/ — for importing exp002
sys.path.insert(0, _ROOT)   # repo root — for core.phi_theory

from exp002_scale_memory import (  # noqa: E402 (path must be set first)
    N_BLOCKS, BLOCK_SIZE, LEVELS, ALPHA_PRIMARY, ALPHA_SWEEP,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    DRIFT_SHELLS, STEP_SHELLS, SPIKE_SHELLS, SPIKE_PERIOD, WARM_UP_BLOCKS,
    _LOG_PHI_INV, shell_coord, hi_from_state,
    _phi_codebook, _uniform_codebook, _snap, _block_stats,
    ZakhorScale, PhiZakhor, PhiStatic, GridZakhor, GridStatic, OraclePhi,
    _scales_stationary, _scales_drift_up, _scales_drift_down,
    _scales_step_up, _scales_step_down, _scales_spike,
    _mean, _print_summary, _hash_raw,
    _phi_shell_exp, _consistency_fraction,
)
from core.phi_theory import PHI, PHI_INV, GOLDEN_ANGLE_TURNS
from core.phi_theory import _clipped_gauss, _lcg  # noqa: F401

# ── exp003-specific constants ─────────────────────────────────────────────────

SPIKE_TRUE_FRAC: float = 1.0 / (SPIKE_PERIOD * BLOCK_SIZE)  # 1 spike / 16384 values
H0_ID_SAMPLES: int = 4096
H2_R_RECOVERY_BUDGET_UP: int = 128    # ≤ 2/alpha = 2×64
H2_R_RECOVERY_BUDGET_DOWN: int = 8
H3_SILENT_THRESHOLD: float = 10.0     # reconstruction error > 10× oracle = silent error
H3_MAX_DECL_MULTIPLE: float = 1.05    # declared ≤ 1.05 × true spike fraction
S4A_MAX_DISPLACEMENT: float = 0.25    # shells
S4A_RECOVERY_RADIUS: float = 0.02     # shells; must recover before next spike
S4C_MAX_R_RATIO: float = 1.20         # normal-block R ≤ 1.20 × S1 stationary R
REGRESSION_TOLERANCE: float = 0.05    # S1 regression gate (5% relative)

_NAMES_6: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-ZAKHOR-KEEP", "PHI-STATIC",
    "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI",
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. New machinery: ZakhorScale with state logging
# ─────────────────────────────────────────────────────────────────────────────

class ZakhorScaleLogged(ZakhorScale):
    """ZakhorScale that records (pre_state, post_state) on every observe()."""

    __slots__ = ("_log",)

    def __init__(self, alpha: float = ALPHA_PRIMARY) -> None:
        super().__init__(alpha)
        self._log: List[Tuple[float, float]] = []

    def observe(self, block: Sequence[float]) -> float:
        pre = super().observe(block)
        self._log.append((pre, self._s))
        return pre

    @property
    def state_log(self) -> List[Tuple[float, float]]:
        return self._log


# ─────────────────────────────────────────────────────────────────────────────
# 2. PHI-ZAKHOR-KEEP: the declared-stranger competitor
# ─────────────────────────────────────────────────────────────────────────────

class PhiZakhorKeep:
    """PHI-ZAKHOR + declare-loss branch.

    Any value with |v| > hi (beyond the outermost shell) is declared a
    stranger: not quantized (no silent garbage), not super-integrated (state
    update unchanged — normal alpha step using block max including stranger),
    and logged with (block_index, observed_shell_coord, overshoot ratio).

    MSE is computed over non-stranger values only.
    """

    name = "PHI-ZAKHOR-KEEP"
    is_phi = True

    def __init__(self, alpha: float = ALPHA_PRIMARY) -> None:
        self._zs = ZakhorScaleLogged(alpha)
        self._block_idx: int = 0
        self.stranger_log: List[Tuple[int, float, float]] = []
        self._total_values: int = 0
        self._declared_count: int = 0

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        self._block_idx += 1
        pre = self._zs.observe(block)   # causal pre-update read; state updated inside
        hi = hi_from_state(pre)
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

        if normal:
            mse, under, over = _block_stats(normal, book)
        else:
            mse, under, over = 0.0, 0.0, 0.0

        return mse, under, over, hi

    @property
    def declared_rate(self) -> float:
        return self._declared_count / self._total_values if self._total_values else 0.0

    @property
    def state_log(self) -> List[Tuple[float, float]]:
        return self._zs.state_log


def _fresh_competitors_6(alpha: float = ALPHA_PRIMARY) -> List:
    """All six exp003 competitors in canonical order."""
    return [
        PhiZakhor(alpha),
        PhiZakhorKeep(alpha),
        PhiStatic(),
        GridZakhor(alpha),
        GridStatic(),
        OraclePhi(),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Three-distance theorem: safe radius for the active prefix
# ─────────────────────────────────────────────────────────────────────────────

def _phi_seq_gaps(n: int) -> List[float]:
    """All gap sizes for the first n points of the phi-addressing sequence."""
    pts = sorted((k * PHI_INV) % 1.0 for k in range(n))
    gaps = [pts[i + 1] - pts[i] for i in range(n - 1)]
    gaps.append(1.0 + pts[0] - pts[-1])   # wrap-around
    return gaps


def safe_radius(n: int) -> float:
    """Half the minimum three-distance gap for n phi-sequence points."""
    return min(_phi_seq_gaps(n)) / 2.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Stream runner with oracle + state tracking
# ─────────────────────────────────────────────────────────────────────────────

def _run_exp003(
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> Dict[str, List[Tuple[float, float, float, float]]]:
    """Same contract as exp002._run, extended to accept 6-competitor lists."""
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


# ─────────────────────────────────────────────────────────────────────────────
# 5. H0-id: shell consistency + return feasibility + return correctness
# ─────────────────────────────────────────────────────────────────────────────

def h0_id_static(m: int, n_samples: int = H0_ID_SAMPLES) -> Dict[str, float]:
    """H0-id metrics for a static drift of m shells.

    Shell consistency: fraction shifting by exactly −m (same metric as exp002).
    Return feasibility: fraction where j_old ≥ m (the return j_old = j_new + m
    is in valid range) AND the shift was consistent.
    Return correctness: among feasible, fraction where j_new + m = j_old exactly.
    Safe radius is the half-min-gap for LEVELS-point phi-prefix.
    """
    hi_old = 1.0
    hi_new = PHI_INV ** m   # hi shrinks by m shells
    book_phi_old = _phi_codebook(hi_old, LEVELS)
    book_phi_new = _phi_codebook(hi_new, LEVELS)
    book_uni_old = _uniform_codebook(hi_old, LEVELS)
    book_uni_new = _uniform_codebook(hi_new, LEVELS)

    sr = safe_radius(LEVELS)

    rnd = _lcg(SEED_BASE ^ 0xB00C)
    values = [_clipped_gauss(rnd, std=STD_PEAKED) for _ in range(n_samples)]

    # Phi competitor metrics
    phi_feas = phi_correct = 0
    phi_total_feas_eligible = 0
    for v in values:
        _, rv_old = _snap(v, book_phi_old)
        _, rv_new = _snap(v, book_phi_new)
        j_old = _phi_shell_exp(rv_old, hi_old)
        j_new = _phi_shell_exp(rv_new, hi_new)
        if j_old is None or j_new is None:
            continue
        phi_total_feas_eligible += 1
        if j_old >= m:                    # return would land in valid range
            phi_feas += 1
            if j_new + m == j_old:        # return correctness
                phi_correct += 1

    phi_consistency = _consistency_fraction(
        values, book_phi_old, hi_old, book_phi_new, hi_new, -m
    )
    uni_consistency = _consistency_fraction(
        values, book_uni_old, hi_old, book_uni_new, hi_new, -m
    )

    phi_feasibility = phi_feas / phi_total_feas_eligible if phi_total_feas_eligible else 0.0
    phi_correctness = phi_correct / phi_feas if phi_feas > 0 else 0.0

    # Uniform feasibility (reference, no threshold)
    uni_feas = 0
    uni_total = 0
    for v in values:
        _, rv_old = _snap(v, book_uni_old)
        _, rv_new = _snap(v, book_uni_new)
        j_old = _phi_shell_exp(rv_old, hi_old)
        j_new = _phi_shell_exp(rv_new, hi_new)
        if j_old is None:
            continue
        uni_total += 1
        if j_new is not None and j_new + m == j_old:
            uni_feas += 1

    return {
        "phi_consistency": phi_consistency,
        "phi_feasibility": phi_feasibility,
        "phi_correctness": phi_correctness,
        "uni_consistency": uni_consistency,
        "uni_feasibility": uni_feas / uni_total if uni_total else 0.0,
        "safe_radius": sr,
    }


def h0_id_s2_feasibility(
    raw_s2: Dict[str, List[Tuple[float, float, float, float]]],
) -> Dict[str, float]:
    """Return feasibility averaged across all S2↑ blocks (varying m_effective).

    At block t, hi_pz = raw['PHI-ZAKHOR'][t][3] (zakhor-tracked hi).
    hi_oracle = raw['ORACLE-PHI'][t][3] (per-block true max).
    m_effective ≈ L(hi_oracle_initial) - L(hi_oracle(t)) (cumulative drift).

    A value is 'feasible' if the phi-codebook can guarantee its return:
    i.e. quantizing it in both old and new codebooks gives a consistent shift.
    We measure this empirically per block across a fixed test set.
    """
    rnd = _lcg(SEED_BASE ^ 0xFEED)
    test_values = [_clipped_gauss(rnd, std=STD_PEAKED) for _ in range(512)]

    feas_phi_per_block: List[float] = []
    feas_uni_per_block: List[float] = []

    hi_base_phi = hi_from_state(
        shell_coord(max(raw_s2["PHI-ZAKHOR"][0][3], 1e-300))
    )
    hi_base_uni = hi_from_state(
        shell_coord(max(raw_s2["GRID-ZAKHOR"][0][3], 1e-300))
    )

    for t in range(N_BLOCKS):
        hi_phi = raw_s2["PHI-ZAKHOR"][t][3]
        hi_uni = raw_s2["GRID-ZAKHOR"][t][3]
        hi_oracle = raw_s2["ORACLE-PHI"][t][3]
        if hi_oracle < 1e-300:
            continue

        # approximate m_eff: drift from base to oracle
        m_eff_phi = max(0, round(shell_coord(hi_phi / hi_oracle)))
        m_eff_uni = max(0, round(shell_coord(hi_uni / hi_oracle)))

        book_phi_now = _phi_codebook(hi_phi, LEVELS)
        book_phi_oracle = _phi_codebook(hi_oracle, LEVELS)
        book_uni_now = _uniform_codebook(hi_uni, LEVELS)
        book_uni_oracle = _uniform_codebook(hi_oracle, LEVELS)

        def _feas(vals, bk_now, hi_now, bk_oracle, hi_oracle_val, m):
            feas = total = 0
            for v in vals:
                _, rv_now = _snap(v, bk_now)
                _, rv_or = _snap(v, bk_oracle)
                j_now = _phi_shell_exp(rv_now, hi_now)
                j_or = _phi_shell_exp(rv_or, hi_oracle_val)
                if j_now is None or j_or is None:
                    continue
                total += 1
                if j_now >= m and (j_or + m == j_now or m == 0):
                    feas += 1
            return feas / total if total else 0.0

        feas_phi_per_block.append(_feas(
            test_values, book_phi_now, hi_phi, book_phi_oracle, hi_oracle, m_eff_phi
        ))
        feas_uni_per_block.append(_feas(
            test_values, book_uni_now, hi_uni, book_uni_oracle, hi_oracle, m_eff_uni
        ))

    return {
        "phi_feasibility_s2": _mean(feas_phi_per_block),
        "uni_feasibility_s2": _mean(feas_uni_per_block),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. H2-r: oracle-relative recovery ratio
# ─────────────────────────────────────────────────────────────────────────────

def h2_r_recovery(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    step_block: int,
    pre_window: int = 256,
) -> Dict[str, Dict]:
    """Per-competitor oracle-relative recovery.

    R(t) = competitor_mse(t) / oracle_mse(t). Pre-step R̄ = mean R over last
    pre_window blocks before step. Recovery = first block ≥ step_block where
    R(t) ≤ 2 × R̄, then remains ≤ 2 × R̄ for 8 consecutive blocks.
    """
    oracle_mses = [raw["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]

    def _ratios(name: str) -> List[float]:
        return [
            raw[name][t][0] / max(oracle_mses[t], 1e-30)
            for t in range(N_BLOCKS)
        ]

    out: Dict[str, Dict] = {}
    for name in raw:
        if name == "ORACLE-PHI":
            continue
        R = _ratios(name)
        R_bar = _mean(R[max(0, step_block - pre_window): step_block])
        threshold = 2.0 * R_bar
        rec: Optional[int] = None
        for t in range(step_block, N_BLOCKS - 7):
            if all(R[t + k] <= threshold for k in range(8)):
                rec = t - step_block
                break
        out[name] = {
            "R_bar": R_bar,
            "recovery_blocks": rec,
            "max_R_post": max(R[step_block:]) if step_block < N_BLOCKS else 0.0,
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 7. S4 decomposed
# ─────────────────────────────────────────────────────────────────────────────

def s4a_state_integrity(
    raw_s4: Dict[str, List[Tuple[float, float, float, float]]],
    zakhor_name: str = "PHI-ZAKHOR",
) -> Dict[str, object]:
    """S4a: per-spike state displacement and recovery.

    pre_state[t] = shell_coord(hi_returned[t]) (causal pre-update state).
    Displacement at spike block t_s = |pre_state[t_s+1] - pre_state[t_s]|.
    Recovery = blocks until |pre_state[t] - pre_state[t_s]| < S4A_RECOVERY_RADIUS,
    measured over blocks t_s+1 .. t_s+255 (before next spike).
    """
    pre_states = [shell_coord(raw_s4[zakhor_name][t][3]) for t in range(N_BLOCKS)]

    spike_blocks = [t for t in range(SPIKE_PERIOD, N_BLOCKS, SPIKE_PERIOD)]

    displacements: List[float] = []
    recoveries: List[Optional[int]] = []

    for t_s in spike_blocks:
        if t_s + 1 >= N_BLOCKS:
            break
        disp = abs(pre_states[t_s + 1] - pre_states[t_s])
        displacements.append(disp)

        # Find recovery within next 255 blocks
        baseline = pre_states[t_s]
        rec: Optional[int] = None
        end = min(t_s + SPIKE_PERIOD, N_BLOCKS)
        for t in range(t_s + 1, end):
            if abs(pre_states[t] - baseline) < S4A_RECOVERY_RADIUS:
                rec = t - t_s
                break
        recoveries.append(rec)

    peak_disp = max(displacements) if displacements else 0.0
    all_recovered = all(r is not None for r in recoveries)
    max_recovery = max((r for r in recoveries if r is not None), default=None)

    return {
        "peak_displacement": peak_disp,
        "all_recovered": all_recovered,
        "max_recovery_blocks": max_recovery,
        "n_spikes_analyzed": len(spike_blocks),
    }


def s4b_spike_fidelity(
    raw_s4: Dict[str, List[Tuple[float, float, float, float]]],
    std: float,
) -> Dict[str, float]:
    """S4b: spike-value reconstruction error per competitor (descriptive).

    Spike blocks: t where t % SPIKE_PERIOD == 0. Block MSE is dominated by
    the one spike value (|v| ≈ φ^10 ≈ 123). Reporting spike-block MSE ÷
    normal-block MSE captures fidelity without thresholding.
    """
    spike_ts = [t for t in range(N_BLOCKS) if t % SPIKE_PERIOD == 0]
    normal_ts = [t for t in range(N_BLOCKS) if t % SPIKE_PERIOD != 0]

    out: Dict[str, float] = {}
    for name in raw_s4:
        spike_mse = _mean([raw_s4[name][t][0] for t in spike_ts])
        norm_mse = _mean([raw_s4[name][t][0] for t in normal_ts]) or 1e-30
        out[name] = spike_mse / norm_mse   # ratio; lower = spike well-represented
    return out


def s4c_collateral(
    raw_s4: Dict[str, List[Tuple[float, float, float, float]]],
    R_s1: Dict[str, float],
) -> Dict[str, Dict]:
    """S4c: normal-block oracle-relative R, compared to S1 stationary R.

    Normal blocks: t % SPIKE_PERIOD != 0.
    PASS: PHI-ZAKHOR normal-block R ≤ S4C_MAX_R_RATIO × S1 R.
    """
    normal_ts = [t for t in range(N_BLOCKS) if t % SPIKE_PERIOD != 0]
    oracle_mses = [raw_s4["ORACLE-PHI"][t][0] for t in normal_ts]

    out: Dict[str, Dict] = {}
    for name in raw_s4:
        if name == "ORACLE-PHI":
            continue
        comp_mses = [raw_s4[name][t][0] for t in normal_ts]
        R_normal = _mean([
            c / max(o, 1e-30) for c, o in zip(comp_mses, oracle_mses)
        ])
        R_s1_val = R_s1.get(name, 1.0)
        out[name] = {
            "R_normal": R_normal,
            "R_s1": R_s1_val,
            "ratio": R_normal / max(R_s1_val, 1e-30),
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 8. Honesty metrics (all six competitors)
# ─────────────────────────────────────────────────────────────────────────────

def honesty_metrics(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> Dict[str, Dict[str, float]]:
    """Declared-loss rate and silent-error rate per competitor.

    Re-runs the stream to get per-value access.
    declared: |v| > hi  (only PHI-ZAKHOR-KEEP by design)
    silent error: err > H3_SILENT_THRESHOLD × oracle_err AND NOT declared
    """
    rnd = _lcg(seed)
    declared_counts: Dict[str, int] = {c.name: 0 for c in competitors}
    silent_counts: Dict[str, int] = {c.name: 0 for c in competitors}
    total_values = 0

    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)

        # Oracle hi and codebook for this block
        oracle_hi = raw["ORACLE-PHI"][t][3]
        if oracle_hi < 1e-300:
            oracle_hi = 1e-300
        oracle_book = _phi_codebook(oracle_hi, LEVELS)

        for v in block:
            total_values += 1
            _, rv_oracle = _snap(v, oracle_book)
            oracle_err = (v - rv_oracle) ** 2

            for c in competitors:
                hi_c = raw[c.name][t][3]
                is_declared = (c.name == "PHI-ZAKHOR-KEEP" and abs(v) > hi_c)
                if is_declared:
                    declared_counts[c.name] += 1
                else:
                    # Build codebook for this competitor
                    if c.is_phi:
                        bk = _phi_codebook(hi_c, LEVELS)
                    else:
                        bk = _uniform_codebook(hi_c, LEVELS)
                    _, rv = _snap(v, bk)
                    err = (v - rv) ** 2
                    if err > H3_SILENT_THRESHOLD * oracle_err + 1e-30:
                        silent_counts[c.name] += 1

    return {
        c.name: {
            "declared_rate": declared_counts[c.name] / total_values,
            "silent_error_rate": silent_counts[c.name] / total_values,
        }
        for c in competitors
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. Print / verdict helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pf(cond: bool) -> str:
    return "PASS" if cond else "FALSIFIED"


def _metric_defect(label: str) -> None:
    print(f"  [METRIC-DEFECT] {label}")


def _stream_summary_6(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
) -> Dict[str, Dict[str, float]]:
    return {
        name: {
            "mse": _mean([r[0] for r in blks]),
            "underflow": _mean([r[1] for r in blks]),
            "overflow": _mean([r[2] for r in blks]),
        }
        for name, blks in raw.items()
    }


def _print_summary_6(label: str, summary: Dict[str, Dict[str, float]]) -> None:
    print(f"\n{label}")
    print("-" * 78)
    print(f"  {'competitor':<20} {'MSE':>14} {'underflow':>12} {'overflow':>12}")
    for name in _NAMES_6:
        if name not in summary:
            continue
        s = summary[name]
        print(f"  {name:<20} {s['mse']:>14.4e} {s['underflow']:>12.4e} {s['overflow']:>12.4e}")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Reproducibility hash
# ─────────────────────────────────────────────────────────────────────────────

def _hash_raw_6(raw: Dict) -> str:
    h = hashlib.sha256()
    for name in sorted(raw.keys()):
        for mse, under, over, _ in raw[name]:
            h.update(f"{mse:.15e}{under:.15e}{over:.15e}".encode())
    return h.hexdigest()[:16]


def _all_runs(alpha: float = ALPHA_PRIMARY) -> Dict[str, Dict]:
    all_raw: Dict[str, Dict] = {}
    for std in (STD_PEAKED, STD_SPREAD):
        _stream_defs = [
            (f"S1-{std}",   _scales_stationary,  1, False),
            (f"S2up-{std}", _scales_drift_up,     2, False),
            (f"S2dn-{std}", _scales_drift_down,   3, False),
            (f"S3up-{std}", _scales_step_up,      4, False),
            (f"S3dn-{std}", _scales_step_down,    5, False),
            (f"S4-{std}",   _scales_spike,        6, True),
        ]
        for tag, fn, off, spike in _stream_defs:
            cs = _fresh_competitors_6(alpha)
            all_raw[tag] = _run_exp003(
                cs, fn(), std, SEED_BASE + off, is_spike=spike
            )
    return all_raw


# ─────────────────────────────────────────────────────────────────────────────
# 11. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 003 — Identity, Recovery, and the Declared Stranger")
    print("=" * 90)
    print(f"  Pre-registered thresholds frozen 2026-07-11. See docs/exp003-pre-registration.md.")
    print(f"  Carried-over: {N_BLOCKS}×{BLOCK_SIZE} blocks, {LEVELS} levels, alpha=1/{round(1/ALPHA_PRIMARY)}, seed={SEED_BASE}")
    print(f"  New: PHI-ZAKHOR-KEEP | H0-id | H2-r | S4a/b/c | honesty metrics")

    verdicts: Dict[str, str] = {}
    step_block = N_BLOCKS // 2

    for std, std_label in (
        (STD_PEAKED, f"peaked (std={STD_PEAKED})"),
        (STD_SPREAD, f"spread (std={STD_SPREAD})"),
    ):
        sep = "━" * 90
        print(f"\n{sep}")
        print(f"  Distribution: {std_label}")
        print(sep)

        # ── §5 Regression gate: S1 stationary ────────────────────────────────
        cs_s1 = _fresh_competitors_6()
        raw_s1 = _run_exp003(cs_s1, _scales_stationary(), std, SEED_BASE + 1)
        _print_summary_6(f"§5 S1 STATIONARY ({std_label})", _stream_summary_6(raw_s1))

        # S1 oracle-relative R for each competitor (baseline for S4c)
        oracle_mse_s1 = [raw_s1["ORACLE-PHI"][t][0] for t in range(N_BLOCKS)]
        R_s1: Dict[str, float] = {}
        for name in _NAMES_6:
            if name == "ORACLE-PHI" or name not in raw_s1:
                continue
            R_s1[name] = _mean([
                raw_s1[name][t][0] / max(oracle_mse_s1[t], 1e-30)
                for t in range(N_BLOCKS)
            ])

        # Regression check: KEEP must not be MORE than REGRESSION_TOLERANCE worse
        # than PHI-ZAKHOR. It may be better (it excludes overflow values from MSE).
        pz_s1 = _mean([raw_s1["PHI-ZAKHOR"][t][0] for t in range(N_BLOCKS)])
        pk_s1 = _mean([raw_s1["PHI-ZAKHOR-KEEP"][t][0] for t in range(N_BLOCKS)])
        keep_ok = pk_s1 <= pz_s1 * (1.0 + REGRESSION_TOLERANCE)
        print(f"  Regression gate: PHI-ZAKHOR {pz_s1:.4e}  PHI-ZAKHOR-KEEP {pk_s1:.4e} "
              f"(KEEP≤PHI-ZAKHOR+{REGRESSION_TOLERANCE:.0%}) — {_pf(keep_ok)}")
        if not keep_ok:
            # KEEP is genuinely worse than PHI-ZAKHOR on stationary data.
            print("  *** REGRESSION FAIL: KEEP MSE exceeds PHI-ZAKHOR by >"
                  f" {REGRESSION_TOLERANCE:.0%}. Halting per pre-registration §5.")
            verdicts[f"regression-{std}"] = "FALSIFIED"
            return
        verdicts[f"regression-{std}"] = "PASS"

        # ── §1 H0-id: static drift tests ─────────────────────────────────────
        print(f"\n§1 H0-id SHELL IDENTITY ({std_label})")
        print("-" * 90)
        print(f"  {'m':>4} | {'φ-consist':>10} | {'φ-feas':>8} | {'φ-correct':>10} "
              f"| {'uni-consist':>12} | {'uni-feas':>10} | safe_r | verdict")
        h0_id_pass = True
        for m in (1, 2, 4):
            r = h0_id_static(m)
            sc_pass = r["phi_consistency"] >= (0.85 if m == 1 else 0.75 if m == 4 else 0.80)
            feas_ok = True  # feasibility threshold tested on S2 below
            corr_ok = r["phi_correctness"] >= 0.99
            grid_close = (abs(r["phi_consistency"] - r["uni_consistency"]) < 0.05 and
                          abs(r["phi_feasibility"] - r["uni_feasibility"]) < 0.05)
            v = _pf(sc_pass and corr_ok and not grid_close)
            h0_id_pass = h0_id_pass and sc_pass and corr_ok and not grid_close
            print(f"  {m:>4} | {r['phi_consistency']:>10.4f} | {r['phi_feasibility']:>8.4f}"
                  f" | {r['phi_correctness']:>10.4f} | {r['uni_consistency']:>12.4f}"
                  f" | {r['uni_feasibility']:>10.4f} | {r['safe_radius']:.4f} | {v}")
        verdicts[f"H0id-{std}"] = _pf(h0_id_pass)

        # H0-id S2 feasibility
        cs_s2f = _fresh_competitors_6()
        raw_s2u_id = _run_exp003(cs_s2f, _scales_drift_up(), std, SEED_BASE + 2)
        s2_feas = h0_id_s2_feasibility(raw_s2u_id)
        s2_feas_ok = s2_feas["phi_feasibility_s2"] >= 0.80
        verdicts[f"H0id-feas-{std}"] = _pf(s2_feas_ok)
        print(f"\n  Return feasibility on S2↑: φ={s2_feas['phi_feasibility_s2']:.4f} "
              f"uni={s2_feas['uni_feasibility_s2']:.4f}  (threshold φ≥0.80) "
              f"— {_pf(s2_feas_ok)}")
        print(f"  H0-id overall: {verdicts[f'H0id-{std}']}  "
              f"(FALSIFIED if φ fails any threshold or grid matches φ within 0.05)")

        # ── S2 slow drift (for context + H1) ─────────────────────────────────
        cs_s2 = _fresh_competitors_6()
        raw_s2 = _run_exp003(cs_s2, _scales_drift_up(), std, SEED_BASE + 2)
        _print_summary_6(f"S2 SLOW DRIFT ↑ (φ^+{DRIFT_SHELLS}) ({std_label})",
                         _stream_summary_6(raw_s2))

        # ── §2 H2-r: oracle-relative step recovery ────────────────────────────
        print(f"\n§2 H2-r ORACLE-RELATIVE RECOVERY ({std_label})")

        # Step UP
        cs_s3u = _fresh_competitors_6()
        raw_s3u = _run_exp003(cs_s3u, _scales_step_up(), std, SEED_BASE + 4)
        _print_summary_6(f"S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})",
                         _stream_summary_6(raw_s3u))
        rec_up = h2_r_recovery(raw_s3u, step_block)
        print(f"  Recovery (budget {H2_R_RECOVERY_BUDGET_UP} blocks):")
        pz_rec_up = rec_up.get("PHI-ZAKHOR", {}).get("recovery_blocks")
        print(f"    {'competitor':<22} {'R_bar':>8} {'recovery':>10} {'max_R_post':>12}")
        for name in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP", "GRID-ZAKHOR"):
            if name not in rec_up:
                continue
            d = rec_up[name]
            rv = d["recovery_blocks"]
            rv_str = str(rv) if rv is not None else ">N"
            print(f"    {name:<22} {d['R_bar']:>8.3f} {rv_str:>10} {d['max_R_post']:>12.2f}")
        h2_up_ok = pz_rec_up is not None and pz_rec_up <= H2_R_RECOVERY_BUDGET_UP
        verdicts[f"H2r-up-{std}"] = _pf(h2_up_ok)
        print(f"  H2-r step-UP: {verdicts[f'H2r-up-{std}']} "
              f"(PHI-ZAKHOR recovery={pz_rec_up}, budget={H2_R_RECOVERY_BUDGET_UP})")

        # Step DOWN
        cs_s3d = _fresh_competitors_6()
        raw_s3d = _run_exp003(cs_s3d, _scales_step_down(), std, SEED_BASE + 5)
        _print_summary_6(f"S3 STEP ↓ (−{STEP_SHELLS} shells) ({std_label})",
                         _stream_summary_6(raw_s3d))
        rec_dn = h2_r_recovery(raw_s3d, step_block)
        pz_rec_dn = rec_dn.get("PHI-ZAKHOR", {}).get("recovery_blocks")
        print(f"  Recovery (budget {H2_R_RECOVERY_BUDGET_DOWN} blocks, "
              f"pred ~0):")
        for name in ("PHI-ZAKHOR", "GRID-ZAKHOR"):
            if name not in rec_dn:
                continue
            d = rec_dn[name]
            rv = d["recovery_blocks"]
            rv_str = str(rv) if rv is not None else ">N"
            print(f"    {name:<22} {d['R_bar']:>8.3f} {rv_str:>10}")
        h2_dn_ok = pz_rec_dn is not None and pz_rec_dn <= H2_R_RECOVERY_BUDGET_DOWN
        verdicts[f"H2r-dn-{std}"] = _pf(h2_dn_ok)
        print(f"  H2-r step-DOWN: {verdicts[f'H2r-dn-{std}']} "
              f"(recovery={pz_rec_dn}, budget={H2_R_RECOVERY_BUDGET_DOWN})")
        print(f"  Asymmetry: step-UP recovery={pz_rec_up}, step-DOWN recovery={pz_rec_dn} "
              f"(prediction on record: DOWN~0, UP~1/alpha={round(1/ALPHA_PRIMARY)})")

        # ── §3 S4 decomposed ──────────────────────────────────────────────────
        cs_s4 = _fresh_competitors_6()
        raw_s4 = _run_exp003(cs_s4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        _print_summary_6(
            f"§3 S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            _stream_summary_6(raw_s4),
        )

        # S4a: state integrity
        s4a = s4a_state_integrity(raw_s4, "PHI-ZAKHOR")
        s4a_ok = (s4a["peak_displacement"] <= S4A_MAX_DISPLACEMENT and s4a["all_recovered"])
        verdicts[f"S4a-{std}"] = _pf(s4a_ok)
        print(f"\n  S4a state integrity: peak_disp={s4a['peak_displacement']:.4f} "
              f"(≤{S4A_MAX_DISPLACEMENT}), all_recovered={s4a['all_recovered']}, "
              f"max_recovery={s4a['max_recovery_blocks']} — {verdicts[f'S4a-{std}']}")

        # S4b: spike fidelity (descriptive)
        s4b = s4b_spike_fidelity(raw_s4, std)
        print(f"  S4b spike fidelity (spike-block-MSE / normal-block-MSE, lower = spike well-handled):")
        for name in _NAMES_6:
            if name in s4b:
                print(f"    {name:<22} {s4b[name]:>10.2f}×")

        # S4c: collateral damage (normal blocks only)
        s4c = s4c_collateral(raw_s4, R_s1)
        s4c_ok = s4c.get("PHI-ZAKHOR", {}).get("ratio", 999) <= S4C_MAX_R_RATIO
        verdicts[f"S4c-{std}"] = _pf(s4c_ok)
        print(f"  S4c collateral (normal-block R / S1 R, threshold ≤{S4C_MAX_R_RATIO}):")
        for name in ("PHI-ZAKHOR", "PHI-ZAKHOR-KEEP", "GRID-ZAKHOR"):
            if name in s4c:
                d = s4c[name]
                print(f"    {name:<22} R_normal={d['R_normal']:.3f}  "
                      f"R_s1={d['R_s1']:.3f}  ratio={d['ratio']:.3f}")
        print(f"  S4c verdict: {verdicts[f'S4c-{std}']}")

        # ── §4 Honesty metrics ────────────────────────────────────────────────
        print(f"\n§4 HONESTY METRICS ({std_label})")
        cs_h4 = _fresh_competitors_6()
        raw_h4 = _run_exp003(cs_h4, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        hm = honesty_metrics(
            raw_h4, cs_h4,
            _scales_spike(), std, SEED_BASE + 6, is_spike=True,
        )
        print(f"  true spike fraction: {SPIKE_TRUE_FRAC:.2e}  "
              f"H3 max declared: {H3_MAX_DECL_MULTIPLE}×true = {H3_MAX_DECL_MULTIPLE*SPIKE_TRUE_FRAC:.2e}")
        print(f"  {'competitor':<22} {'decl_rate':>12} {'silent_err_rate':>16}")
        for name in _NAMES_6:
            if name not in hm:
                continue
            d = hm[name]
            print(f"  {name:<22} {d['declared_rate']:>12.4e} {d['silent_error_rate']:>16.4e}")

        # H3 verdict
        keep_hm = hm.get("PHI-ZAKHOR-KEEP", {})
        h3_silent_ok = keep_hm.get("silent_error_rate", 1.0) < 0.001
        h3_decl_ok = keep_hm.get("declared_rate", 1.0) <= H3_MAX_DECL_MULTIPLE * SPIKE_TRUE_FRAC
        # S4c KEEP collateral
        keep_s4c_ratio = s4c.get("PHI-ZAKHOR-KEEP", {}).get("ratio", 999)
        h3_collateral_ok = keep_s4c_ratio <= S4C_MAX_R_RATIO
        h3_ok = h3_silent_ok and h3_decl_ok and h3_collateral_ok
        verdicts[f"H3-{std}"] = _pf(h3_ok)
        print(f"\n  H3: silent_err {_pf(h3_silent_ok)} | "
              f"over-declare {_pf(h3_decl_ok)} | "
              f"collateral {_pf(h3_collateral_ok)} | "
              f"OVERALL {verdicts[f'H3-{std}']}")
        print(f"  Note: PHI-STATIC silent_error_rate expected catastrophic "
              f"({hm.get('PHI-STATIC', {}).get('silent_error_rate', 0):.3e}) "
              f"— this is the metric doing its job.")

        # Stranger log summary
        keep_c = next(c for c in cs_h4 if c.name == "PHI-ZAKHOR-KEEP")
        slog = keep_c.stranger_log
        print(f"\n  Stranger log: {len(slog)} entries. First 3:")
        for entry in slog[:3]:
            print(f"    block={entry[0]:>5}  shell_coord={entry[1]:>8.3f}  overshoot={entry[2]:.2f}×")
        if not slog:
            print("    (empty — no strangers declared)")

    # ── Alpha sweep (S2↑ + S3↑, H2-r recovery) ───────────────────────────────
    print(f"\n{'='*90}")
    print("ALPHA SWEEP (H2-r recovery on S3↑ — peaked distribution only)")
    print(f"{'='*90}")
    print(f"  {'alpha':>8} | {'competitor':<22} | {'S2 MSE':>12} | {'S3 R_bar':>10} | {'recovery':>10}")
    for alpha in ALPHA_SWEEP:
        for name_filter in ("PHI-ZAKHOR", "GRID-ZAKHOR"):
            cs_a = _fresh_competitors_6(alpha)
            raw_a2 = _run_exp003(cs_a, _scales_drift_up(), STD_PEAKED, SEED_BASE + 20)
            cs_b = _fresh_competitors_6(alpha)
            raw_a3 = _run_exp003(cs_b, _scales_step_up(), STD_PEAKED, SEED_BASE + 30)
            rec_a = h2_r_recovery(raw_a3, step_block)
            s2_mse = _mean([raw_a2[name_filter][t][0] for t in range(N_BLOCKS)])
            d = rec_a.get(name_filter, {})
            rv = d.get("recovery_blocks")
            rv_str = f"{rv}" if rv is not None else ">N"
            print(f"  {alpha:>8.4f} | {name_filter:<22} | {s2_mse:>12.4e} "
                  f"| {d.get('R_bar', 0):>10.3f} | {rv_str:>10}")

    # ── Verdict summary ───────────────────────────────────────────────────────
    print(f"\n{'='*90}")
    print("VERDICT SUMMARY")
    print(f"{'='*90}")
    print(f"  {'check':<24} {'peaked':>10} {'spread':>10}")
    for key_stem in ("regression", "H0id", "H0id-feas", "H2r-up", "H2r-dn", "S4a", "S4c", "H3"):
        vp = verdicts.get(f"{key_stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{key_stem}-{STD_SPREAD}", "—")
        print(f"  {key_stem:<24} {vp:>10} {vs:>10}")

    print()
    print("  Verdicts are PASS / FALSIFIED / METRIC-DEFECT (no fourth category).")
    print("  All exp002 verdicts stand as recorded.")
    print("  Preserve falsified results in research/results/ per project convention.")

    # ── Reproducibility assertion ─────────────────────────────────────────────
    print(f"\n{'='*90}")
    print("REPRODUCIBILITY")
    raw_A = _all_runs()
    raw_B = _all_runs()
    dA = hashlib.sha256()
    dB = hashlib.sha256()
    for k in sorted(raw_A):
        dA.update(_hash_raw_6(raw_A[k]).encode())
        dB.update(_hash_raw_6(raw_B[k]).encode())
    d_A, d_B = dA.hexdigest()[:16], dB.hexdigest()[:16]
    match = d_A == d_B
    print(f"  run1={d_A}  run2={d_B}  {_pf(match)} (bit-identical)")
    if not match:
        print("  *** REPRODUCIBILITY FAIL: non-determinism detected.")

    print()
    print("  Log dated output to research/results/exp003_<YYYY-MM-DD>.txt.")


if __name__ == "__main__":
    main()
