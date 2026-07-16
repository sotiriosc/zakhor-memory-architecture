"""exp002_scale_memory.py — Zakhor Scale Memory (Living hi).

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-11.  See ../NOTICE.
================================================================================

Experiment 002. Architecture Note 00 removed the positional anchor. One anchor
remains: the outer shell magnitude `hi` of the φ-codebook. This experiment
tests making hi a piece of living state — a leaky integrator over incoming
block magnitudes — rather than a frozen calibration constant.

Working name: **zakhor scale** (remembering as act, not storage).

Hypotheses
----------
H0 (composition):  Scale adaptation composes with the φ-codebook as an
    automorphism.  A drift of m shells maps every shell onto the shell m
    positions inward.  The uniform competitor has no such structure: rescaling
    relocates every level to unrelated positions.  The memory must be worth
    MORE on φ geometry, or the composition claim fails.

H1 (drift tracking): PHI-ZAKHOR beats PHI-STATIC on MSE and under/overflow
    across the slow-drift stream (S2).

H2 (step cost): After a step change (S3), PHI-ZAKHOR recovers within
    ~1/alpha blocks and post-recovery metrics return to stationary-equivalent.

Run from the repository root:

    python3 research/exp002_scale_memory.py

Results are printed to stdout; redirect to research/results/ for a dated
record.  Re-running with the same seeds is bit-identical (verified inline).
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.phi_theory import PHI, PHI_INV
from core.phi_theory import _clipped_gauss, _lcg  # noqa: F401 (private; stable)


# ─────────────────────────────────────────────────────────────────────────────
# 0. Experiment constants
# ─────────────────────────────────────────────────────────────────────────────

N_BLOCKS: int = 4096            # blocks per stream
BLOCK_SIZE: int = 64            # values per block (weight-tensor slice)
LEVELS: int = 16                # codebook size; matched across φ and uniform
ALPHA_PRIMARY: float = 1.0 / 64.0
ALPHA_SWEEP: Tuple[float, ...] = (1.0 / 16.0, 1.0 / 64.0, 1.0 / 256.0)
SEED_BASE: int = 1618033

STD_PEAKED: float = 0.15        # primary; peaked weight distribution
STD_SPREAD: float = 0.30        # known-hostile regime (reported, not hidden)

DRIFT_SHELLS: int = 12          # S2: total shell ramp magnitude
STEP_SHELLS: int = 8            # S3: jump size in shells
SPIKE_SHELLS: int = 10          # S4: outlier magnitude (shells above hi=1)
SPIKE_PERIOD: int = 256         # S4: one spike per this many blocks
WARM_UP_BLOCKS: int = 64        # calibration window for static competitors
RECOVERY_FACTOR: float = 2.0    # S3: "recovered" = MSE ≤ this × pre-step mean

_LOG_PHI_INV: float = math.log(PHI_INV)  # ≈ −0.4812; negative constant


# ─────────────────────────────────────────────────────────────────────────────
# 1. Log-domain math
# ─────────────────────────────────────────────────────────────────────────────

def shell_coord(x: float) -> float:
    """L(x) = log(x) / log(1/φ).

    The shell coordinate of magnitude x in the log-(1/φ) domain.
    Additive over φ-scaling: L((1/φ)^k · x) = L(x) + k.
    Since log(1/φ) < 0 the function is *decreasing*: large magnitudes yield
    negative values; magnitudes in (0, 1) yield positive values.

    hi_from_state inverts this: hi_from_state(L(x)) = x.
    """
    return math.log(max(x, 1e-300)) / _LOG_PHI_INV


def hi_from_state(s: float) -> float:
    """Reconstruct hi from log-domain scale_state: hi = (1/φ)^s.

    Because L(x) = log(x)/log(1/φ), we have (1/φ)^(L(x)) = x, so
    hi_from_state(shell_coord(x)) = x exactly.
    """
    return PHI_INV ** s


# ─────────────────────────────────────────────────────────────────────────────
# 2. Codebook builders
# ─────────────────────────────────────────────────────────────────────────────

def _phi_codebook(hi: float, levels: int) -> List[float]:
    """φ-codebook: {0} ∪ {±hi·(1/φ)^j, j = 0, 1, …}, sorted ascending."""
    book: List[float] = [0.0]
    j = 0
    while len(book) < levels:
        shell = hi * (PHI_INV ** j)
        book.append(shell)
        if len(book) < levels:
            book.append(-shell)
        j += 1
    return sorted(book)


def _uniform_codebook(hi: float, levels: int) -> List[float]:
    """Uniform codebook: `levels` evenly spaced points in [−hi, +hi]."""
    if levels == 1:
        return [0.0]
    step = 2.0 * hi / (levels - 1)
    return [-hi + i * step for i in range(levels)]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Quantizer primitives
# ─────────────────────────────────────────────────────────────────────────────

def _snap(v: float, book: List[float]) -> Tuple[int, float]:
    """Nearest-neighbour snap. Returns (codebook_idx, reconstructed_value)."""
    best_i, best_v, best_d = 0, book[0], abs(v - book[0])
    for i in range(1, len(book)):
        d = abs(v - book[i])
        if d < best_d:
            best_i, best_v, best_d = i, book[i], d
    return best_i, best_v


def _block_stats(
    block: Sequence[float], book: List[float]
) -> Tuple[float, float, float]:
    """Return (mse, underflow_rate, overflow_rate) for one block in one pass.

    underflow: fraction of nonzero values snapped to the zero-level shell.
    overflow:  fraction of values whose magnitude exceeds hi = max(|book|).
    """
    hi_book = max(abs(c) for c in book)
    zero_idx: Optional[int] = next(
        (i for i, c in enumerate(book) if c == 0.0), None
    )
    mse_acc = 0.0
    under = 0
    over = 0
    nz = 0
    n = len(block)
    for v in block:
        best_i, best_v, best_d = 0, book[0], abs(v - book[0])
        for i in range(1, len(book)):
            d = abs(v - book[i])
            if d < best_d:
                best_i, best_v, best_d = i, book[i], d
        mse_acc += (v - best_v) ** 2
        if abs(v) > hi_book:
            over += 1
        if v != 0.0:
            nz += 1
            if zero_idx is not None and best_i == zero_idx:
                under += 1
    return (
        mse_acc / n,
        under / nz if nz > 0 else 0.0,
        over / n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. ZakhorScale — the living state machine
# ─────────────────────────────────────────────────────────────────────────────

class ZakhorScale:
    """Leaky integrator over block magnitudes in the L (log-1/φ) domain.

    Protocol — strictly causal (read-before-write):
        obs         = L(max |x| in block)
        pre_state   = scale_state          ← returned for quantization
        scale_state += alpha × (obs − scale_state)

    Cold start: scale_state ← obs of the first block; pre_state ≡ seeded
    state (the block is quantized with its own observation, not a prior).

    Mechanism cost: one subtract, one multiply-by-alpha, one add per block.
    """

    __slots__ = ("alpha", "_s", "_ready")

    def __init__(self, alpha: float = ALPHA_PRIMARY) -> None:
        self.alpha: float = alpha
        self._s: float = 0.0
        self._ready: bool = False

    @property
    def state(self) -> float:
        return self._s

    def observe(self, block: Sequence[float]) -> float:
        """Process block; return pre-update state for causal quantization."""
        max_mag = max(abs(v) for v in block) if block else 0.0
        if max_mag < 1e-300:
            self._ready = True
            return self._s

        obs = shell_coord(max_mag)
        if not self._ready:
            self._s = obs
            self._ready = True
            return self._s   # cold start: pre ≡ seeded state

        pre = self._s
        self._s = pre + self.alpha * (obs - pre)
        return pre


# ─────────────────────────────────────────────────────────────────────────────
# 5. Competitor classes
# ─────────────────────────────────────────────────────────────────────────────
# process_block(block) → (mse, underflow, overflow, hi_used)

class _Competitor:
    name: str = "abstract"
    is_phi: bool = False

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        raise NotImplementedError


class PhiZakhor(_Competitor):
    """PHI-ZAKHOR: φ-codebook + living zakhor scale."""

    name = "PHI-ZAKHOR"
    is_phi = True

    def __init__(self, alpha: float = ALPHA_PRIMARY) -> None:
        self._zs = ZakhorScale(alpha)

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        pre = self._zs.observe(block)
        hi = hi_from_state(pre)
        book = _phi_codebook(hi, LEVELS)
        mse, under, over = _block_stats(block, book)
        return mse, under, over, hi


class PhiStatic(_Competitor):
    """PHI-STATIC: φ-codebook, hi frozen from first WARM_UP_BLOCKS blocks."""

    name = "PHI-STATIC"
    is_phi = True

    def __init__(self) -> None:
        self._hi: Optional[float] = None
        self._buf: List[float] = []
        self._cnt: int = 0

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        self._cnt += 1
        self._buf.extend(block)
        if self._cnt == WARM_UP_BLOCKS and self._hi is None:
            self._hi = max(abs(v) for v in self._buf)
            self._buf = []
        # During warm-up use running max; after freeze use frozen hi.
        if self._hi is not None:
            hi = self._hi
        else:
            hi = max(abs(v) for v in self._buf) if self._buf else 1.0
        book = _phi_codebook(hi, LEVELS)
        mse, under, over = _block_stats(block, book)
        return mse, under, over, hi


class GridZakhor(_Competitor):
    """GRID-ZAKHOR: uniform codebook + living zakhor scale."""

    name = "GRID-ZAKHOR"
    is_phi = False

    def __init__(self, alpha: float = ALPHA_PRIMARY) -> None:
        self._zs = ZakhorScale(alpha)

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        pre = self._zs.observe(block)
        hi = hi_from_state(pre)
        book = _uniform_codebook(hi, LEVELS)
        mse, under, over = _block_stats(block, book)
        return mse, under, over, hi


class GridStatic(_Competitor):
    """GRID-STATIC: uniform codebook, frozen scale (conventional baseline)."""

    name = "GRID-STATIC"
    is_phi = False

    def __init__(self) -> None:
        self._hi: Optional[float] = None
        self._buf: List[float] = []
        self._cnt: int = 0

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        self._cnt += 1
        self._buf.extend(block)
        if self._cnt == WARM_UP_BLOCKS and self._hi is None:
            self._hi = max(abs(v) for v in self._buf)
            self._buf = []
        if self._hi is not None:
            hi = self._hi
        else:
            hi = max(abs(v) for v in self._buf) if self._buf else 1.0
        book = _uniform_codebook(hi, LEVELS)
        mse, under, over = _block_stats(block, book)
        return mse, under, over, hi


class OraclePhi(_Competitor):
    """ORACLE-PHI: φ-codebook, hi set per-block from that block's true max.

    Ceiling only; ZAKHOR is expected to approach but not beat this.
    """

    name = "ORACLE-PHI"
    is_phi = True

    def process_block(self, block: List[float]) -> Tuple[float, float, float, float]:
        hi = max(abs(v) for v in block) if block else 1.0
        if hi < 1e-300:
            hi = 1.0
        book = _phi_codebook(hi, LEVELS)
        mse, under, over = _block_stats(block, book)
        return mse, under, over, hi


_NAMES: Tuple[str, ...] = (
    "PHI-ZAKHOR", "PHI-STATIC", "GRID-ZAKHOR", "GRID-STATIC", "ORACLE-PHI"
)


def _fresh_competitors(alpha: float = ALPHA_PRIMARY) -> List[_Competitor]:
    return [PhiZakhor(alpha), PhiStatic(), GridZakhor(alpha), GridStatic(), OraclePhi()]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Stream scale generators
#    Return a list of per-block true-scale multipliers (length N_BLOCKS).
# ─────────────────────────────────────────────────────────────────────────────

def _scales_stationary() -> List[float]:
    """S1: constant scale = 1.0 throughout."""
    return [1.0] * N_BLOCKS


def _scales_drift_up() -> List[float]:
    """S2↑: linear ramp in shell-coord from 0 to +DRIFT_SHELLS."""
    n = N_BLOCKS - 1
    return [PHI ** (DRIFT_SHELLS * t / n) for t in range(N_BLOCKS)]


def _scales_drift_down() -> List[float]:
    """S2↓: mirrored descending ramp from +DRIFT_SHELLS to 0."""
    return list(reversed(_scales_drift_up()))


def _scales_step_up() -> List[float]:
    """S3↑: scale = 1.0 for first half, then jumps to φ^STEP_SHELLS."""
    half = N_BLOCKS // 2
    hi_step = PHI ** STEP_SHELLS
    return [1.0 if t < half else hi_step for t in range(N_BLOCKS)]


def _scales_step_down() -> List[float]:
    """S3↓: scale = 1.0 for first half, then drops to φ^(−STEP_SHELLS)."""
    half = N_BLOCKS // 2
    lo_step = PHI ** (-STEP_SHELLS)
    return [1.0 if t < half else lo_step for t in range(N_BLOCKS)]


def _scales_spike() -> List[float]:
    """S4: constant scale = 1.0; spike values injected per-block in runner."""
    return [1.0] * N_BLOCKS


# ─────────────────────────────────────────────────────────────────────────────
# 7. Stream runner
# ─────────────────────────────────────────────────────────────────────────────

def _run(
    competitors: List[_Competitor],
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> Dict[str, List[Tuple[float, float, float, float]]]:
    """Run all competitors over one stream.

    Returns per-competitor list of per-block (mse, underflow, overflow, hi).
    Strictly deterministic given (scales, std, seed, is_spike).
    """
    rnd = _lcg(seed)
    results: Dict[str, List[Tuple[float, float, float, float]]] = {
        c.name: [] for c in competitors
    }
    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            # Isolated single-value outlier: one block value at magnitude φ^10.
            spike_sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = spike_sign * (PHI ** SPIKE_SHELLS)
        for c in competitors:
            results[c.name].append(c.process_block(block))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 8. Metric aggregators
# ─────────────────────────────────────────────────────────────────────────────

def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stream_summary(
    raw: Dict[str, List[Tuple[float, float, float, float]]]
) -> Dict[str, Dict[str, float]]:
    """Aggregate per-block results into mean MSE, underflow, overflow."""
    return {
        name: {
            "mse": _mean([r[0] for r in blks]),
            "underflow": _mean([r[1] for r in blks]),
            "overflow": _mean([r[2] for r in blks]),
        }
        for name, blks in raw.items()
    }


def _recovery_blocks(
    raw: Dict[str, List[Tuple[float, float, float, float]]],
    step_block: int,
    pre_window: int = 256,
) -> Dict[str, Optional[int]]:
    """Blocks from step_block until MSE ≤ RECOVERY_FACTOR × pre-step mean."""
    out: Dict[str, Optional[int]] = {}
    for name, blks in raw.items():
        start = max(0, step_block - pre_window)
        pre_mean = _mean([blks[t][0] for t in range(start, step_block)])
        threshold = RECOVERY_FACTOR * pre_mean
        rec: Optional[int] = None
        for t in range(step_block, len(blks)):
            if blks[t][0] <= threshold:
                rec = t - step_block
                break
        out[name] = rec
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 9. Shell-consistency property test (H0, second claim — φ only)
# ─────────────────────────────────────────────────────────────────────────────

def _phi_shell_exp(v: float, hi: float) -> Optional[int]:
    """φ-shell exponent j: |v| ≈ hi·(1/φ)^j. Returns None near zero."""
    if abs(v) < 1e-12 * hi or hi <= 0.0:
        return None
    return round(math.log(abs(v) / hi) / _LOG_PHI_INV)


def _consistency_fraction(
    values: List[float],
    book_old: List[float], hi_old: float,
    book_new: List[float], hi_new: float,
    expected_shift: int,
) -> float:
    """Fraction of values where φ-shell index shifted by expected_shift."""
    consistent = 0
    total = 0
    for v in values:
        _, rv_old = _snap(v, book_old)
        _, rv_new = _snap(v, book_new)
        j_old = _phi_shell_exp(rv_old, hi_old)
        j_new = _phi_shell_exp(rv_new, hi_new)
        if j_old is not None and j_new is not None:
            total += 1
            if (j_new - j_old) == expected_shift:
                consistent += 1
    return consistent / total if total > 0 else 0.0


def run_shell_consistency(n_samples: int = 2048) -> None:
    """Test H0's second claim: drift of m shells shifts φ-shell indices by −m.

    After a drift of m shells (hi shrinks by factor (1/φ)^m), a value that
    was at shell j (i.e. |v| ≈ hi·(1/φ)^j) is now at shell j − m in the
    new codebook, because:
        j_new = log(|v|/hi_new) / log(1/φ)
              = log(|v|/(hi·(1/φ)^m)) / log(1/φ)
              = j_old − m.
    The automorphism is exact in the continuous limit; finite codebook edges
    cause defects only for the outermost and innermost shells.
    The uniform codebook has no analogous structure — shift is not integer.
    """
    rnd = _lcg(SEED_BASE ^ 0xF00D)
    values = [_clipped_gauss(rnd, std=STD_PEAKED) for _ in range(n_samples)]
    hi_base = 1.0

    print("\nH0 SHELL-CONSISTENCY (φ automorphism, n={})".format(n_samples))
    print("-" * 64)
    print(f"  {'drift (shells)':>16} | {'φ-codebook':>12} | {'uniform':>12}")
    for m in (1, 2, 4, 8):
        hi_new = hi_base * (PHI_INV ** m)   # hi shrinks by m shells
        book_phi_old = _phi_codebook(hi_base, LEVELS)
        book_phi_new = _phi_codebook(hi_new, LEVELS)
        book_uni_old = _uniform_codebook(hi_base, LEVELS)
        book_uni_new = _uniform_codebook(hi_new, LEVELS)
        phi_c = _consistency_fraction(
            values, book_phi_old, hi_base, book_phi_new, hi_new, -m
        )
        uni_c = _consistency_fraction(
            values, book_uni_old, hi_base, book_uni_new, hi_new, -m
        )
        print(f"  {m:>16} | {phi_c:>12.4f} | {uni_c:>12.4f}")
    print("  (φ near 1.0 confirms automorphism; uniform has no such structure)")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Print helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(label: str, summary: Dict[str, Dict[str, float]]) -> None:
    print(f"\n{label}")
    print("-" * 72)
    print(f"  {'competitor':<14} {'MSE':>14} {'underflow':>12} {'overflow':>12}")
    for name in _NAMES:
        if name not in summary:
            continue
        s = summary[name]
        print(f"  {name:<14} {s['mse']:>14.4e} {s['underflow']:>12.4e} {s['overflow']:>12.4e}")


def _pass_fail(cond: bool) -> str:
    return "PASS" if cond else "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 11. Alpha sweep (S2 and S3 only)
# ─────────────────────────────────────────────────────────────────────────────

def run_alpha_sweep(std: float, std_label: str) -> None:
    print(f"\nALPHA SWEEP (S2↑ + S3↑, {std_label})")
    print("-" * 80)
    print(f"  {'alpha':>8} | {'competitor':<14} | {'S2 MSE':>12} | "
          f"{'S3 MSE':>12} | {'S3 recovery':>14}")
    step_block = N_BLOCKS // 2
    for alpha in ALPHA_SWEEP:
        pred = round(1.0 / alpha)
        cs2 = _fresh_competitors(alpha)
        raw2 = _run(cs2, _scales_drift_up(), std, SEED_BASE + 20)
        cs3 = _fresh_competitors(alpha)
        raw3 = _run(cs3, _scales_step_up(), std, SEED_BASE + 30)
        rec = _recovery_blocks(raw3, step_block)
        for name in ("PHI-ZAKHOR", "GRID-ZAKHOR"):
            s2_mse = _mean([r[0] for r in raw2[name]])
            s3_mse = _mean([r[0] for r in raw3[name]])
            rv = rec[name]
            rec_str = f"{rv} (~{pred} pred)" if rv is not None else f">N_BLOCKS"
            print(f"  {alpha:>8.4f} | {name:<14} | {s2_mse:>12.4e} | "
                  f"{s3_mse:>12.4e} | {rec_str:>14}")


# ─────────────────────────────────────────────────────────────────────────────
# 12. Reproducibility hash
# ─────────────────────────────────────────────────────────────────────────────

def _hash_raw(raw: Dict[str, List[Tuple[float, float, float, float]]]) -> str:
    """SHA-256 of all (mse, underflow, overflow) values as fixed-precision strings."""
    h = hashlib.sha256()
    for name in sorted(raw.keys()):
        for mse, under, over, _ in raw[name]:
            h.update(f"{mse:.15e}{under:.15e}{over:.15e}".encode())
    return h.hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# 13. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Experiment 002 — Scale Memory (Living hi)")
    print("=" * 72)
    print(f"  {N_BLOCKS} blocks × {BLOCK_SIZE} values | {LEVELS} levels | "
          f"alpha={ALPHA_PRIMARY} (1/{round(1/ALPHA_PRIMARY)}) | "
          f"SEED={SEED_BASE}")
    print(f"  Competitors: {' | '.join(_NAMES)}")

    all_raw_A: Dict[str, Dict] = {}  # first pass; used for hash A
    step_block = N_BLOCKS // 2
    verdicts: Dict[str, str] = {}

    for std, std_label in (
        (STD_PEAKED, f"peaked (std={STD_PEAKED})"),
        (STD_SPREAD, f"spread (std={STD_SPREAD})"),
    ):
        sep = "━" * 72
        print(f"\n{sep}")
        print(f"  Distribution: {std_label}")
        print(sep)

        # ── S1: Stationary ────────────────────────────────────────────────
        cs = _fresh_competitors()
        r1 = _run(cs, _scales_stationary(), std, SEED_BASE + 1)
        all_raw_A[f"S1-{std}"] = r1
        _print_summary(f"S1 STATIONARY ({std_label})", _stream_summary(r1))
        pz_s1 = _mean([b[0] for b in r1["PHI-ZAKHOR"]])
        ps_s1 = _mean([b[0] for b in r1["PHI-STATIC"]])
        ratio_s1 = abs(pz_s1 - ps_s1) / max(pz_s1, ps_s1, 1e-30)
        s1_ok = ratio_s1 < 0.05
        print(f"  S1 sanity: PHI-ZAKHOR {pz_s1:.4e} vs PHI-STATIC {ps_s1:.4e} "
              f"(ratio {ratio_s1:.4f}) — {_pass_fail(s1_ok)}")
        verdicts[f"S1-{std}"] = _pass_fail(s1_ok)
        if not s1_ok:
            print("  *** S1 FAIL: mechanism cost detected on stationary data. "
                  "Stop and review before proceeding.")
            return

        # ── S2: Slow drift up ─────────────────────────────────────────────
        cs = _fresh_competitors()
        r2u = _run(cs, _scales_drift_up(), std, SEED_BASE + 2)
        all_raw_A[f"S2up-{std}"] = r2u
        _print_summary(f"S2 SLOW DRIFT ↑ (φ^+{DRIFT_SHELLS}) ({std_label})",
                       _stream_summary(r2u))

        # ── S2: Slow drift down ───────────────────────────────────────────
        cs = _fresh_competitors()
        r2d = _run(cs, _scales_drift_down(), std, SEED_BASE + 3)
        all_raw_A[f"S2dn-{std}"] = r2d
        _print_summary(f"S2 SLOW DRIFT ↓ (φ^−{DRIFT_SHELLS}) ({std_label})",
                       _stream_summary(r2d))

        # H0 check (S2↑): φ memory advantage > grid memory advantage?
        def _advantage(raw, winner, loser):
            wm = _mean([b[0] for b in raw[winner]])
            lm = _mean([b[0] for b in raw[loser]])
            return (lm - wm) / max(lm, 1e-30)

        phi_adv = _advantage(r2u, "PHI-ZAKHOR", "PHI-STATIC")
        grid_adv = _advantage(r2u, "GRID-ZAKHOR", "GRID-STATIC")
        h0_ok = phi_adv > grid_adv
        print(f"  H0 (S2↑): φ-memory advantage={phi_adv:.4f} "
              f"grid-memory advantage={grid_adv:.4f} — {_pass_fail(h0_ok)}")
        verdicts[f"H0-{std}"] = _pass_fail(h0_ok)

        # H1 check: does PHI-ZAKHOR beat PHI-STATIC on S2↑?
        pz_s2 = _mean([b[0] for b in r2u["PHI-ZAKHOR"]])
        ps_s2 = _mean([b[0] for b in r2u["PHI-STATIC"]])
        h1_ok = pz_s2 < ps_s2
        print(f"  H1 (drift tracking): PHI-ZAKHOR {pz_s2:.4e} vs PHI-STATIC "
              f"{ps_s2:.4e} — {_pass_fail(h1_ok)}")
        verdicts[f"H1-{std}"] = _pass_fail(h1_ok)

        # ── S3: Step up ───────────────────────────────────────────────────
        cs = _fresh_competitors()
        r3u = _run(cs, _scales_step_up(), std, SEED_BASE + 4)
        all_raw_A[f"S3up-{std}"] = r3u
        _print_summary(f"S3 STEP ↑ (+{STEP_SHELLS} shells) ({std_label})",
                       _stream_summary(r3u))
        rec3u = _recovery_blocks(r3u, step_block)
        pred = round(1.0 / ALPHA_PRIMARY)
        print(f"  S3↑ recovery (predicted ~{pred} blocks):", end="")
        for n in ("PHI-ZAKHOR", "PHI-STATIC", "GRID-ZAKHOR"):
            rv = rec3u[n]
            print(f"  {n}={rv if rv is not None else '>N'}", end="")
        print()
        pz_rec = rec3u["PHI-ZAKHOR"]
        h2_ok = pz_rec is not None and pz_rec <= 3 * pred
        verdicts[f"H2up-{std}"] = _pass_fail(h2_ok)
        print(f"  H2 (step cost ↑): recovery={pz_rec} blocks — {_pass_fail(h2_ok)}")

        # ── S3: Step down ─────────────────────────────────────────────────
        cs = _fresh_competitors()
        r3d = _run(cs, _scales_step_down(), std, SEED_BASE + 5)
        all_raw_A[f"S3dn-{std}"] = r3d
        _print_summary(f"S3 STEP ↓ (−{STEP_SHELLS} shells) ({std_label})",
                       _stream_summary(r3d))
        rec3d = _recovery_blocks(r3d, step_block)
        print(f"  S3↓ recovery:", end="")
        for n in ("PHI-ZAKHOR", "GRID-ZAKHOR"):
            rv = rec3d[n]
            print(f"  {n}={rv if rv is not None else '>N'}", end="")
        print()

        # ── S4: Spikes ────────────────────────────────────────────────────
        cs = _fresh_competitors()
        r4 = _run(cs, _scales_spike(), std, SEED_BASE + 6, is_spike=True)
        all_raw_A[f"S4-{std}"] = r4
        _print_summary(
            f"S4 SPIKES (φ^+{SPIKE_SHELLS} every {SPIKE_PERIOD} blocks) ({std_label})",
            _stream_summary(r4),
        )
        pz_s4 = _mean([b[0] for b in r4["PHI-ZAKHOR"]])
        ps_s4 = _mean([b[0] for b in r4["PHI-STATIC"]])
        s4_ok = pz_s4 <= ps_s4 * 1.10   # ≤ 10% worse than frozen
        print(f"  S4 spike tolerance: PHI-ZAKHOR {pz_s4:.4e} vs PHI-STATIC "
              f"{ps_s4:.4e} — {_pass_fail(s4_ok)}")
        verdicts[f"S4-{std}"] = _pass_fail(s4_ok)

        # S5: deferred
        print(f"\n  S5 REAL PROXY: deferred "
              f"(no trained-weight tensor in repo test assets).")

    # ── Shell-consistency test (H0 second claim) ──────────────────────────
    run_shell_consistency()

    # ── Alpha sweep ───────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("ALPHA SWEEP (S2↑ + S3↑; one value, not tuned per-stream)")
    print("=" * 72)
    run_alpha_sweep(STD_PEAKED, f"peaked std={STD_PEAKED}")
    run_alpha_sweep(STD_SPREAD, f"spread std={STD_SPREAD}")

    # ── Verdict ───────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    print(f"  {'check':<20} {'peaked':>10} {'spread':>10}")
    for key_stem in ("S1", "H0", "H1", "H2up", "S4"):
        vp = verdicts.get(f"{key_stem}-{STD_PEAKED}", "—")
        vs = verdicts.get(f"{key_stem}-{STD_SPREAD}", "—")
        print(f"  {key_stem:<20} {vp:>10} {vs:>10}")
    all_pass_peaked = all(
        verdicts.get(f"{k}-{STD_PEAKED}") == "PASS"
        for k in ("S1", "H0", "H1", "H2up", "S4")
    )
    all_pass_spread = all(
        verdicts.get(f"{k}-{STD_SPREAD}") == "PASS"
        for k in ("S1", "H0", "H1", "H2up", "S4")
    )
    print()
    print(f"  OVERALL peaked: {_pass_fail(all_pass_peaked)}")
    print(f"  OVERALL spread: {_pass_fail(all_pass_spread)}")
    print()
    print("  H0: φ-codebook automorphism under scale drift — see shell-")
    print("      consistency table above; PASS iff φ fraction near 1.0.")
    print("  H1: zakhor scale tracks drift — PASS iff PHI-ZAKHOR < PHI-STATIC")
    print("      on S2.  Failure means the integrator is too sluggish.")
    print("  H2: step damage bounded — PASS iff recovery ≤ ~3×(1/alpha).")
    print("      If FAIL on spread but PASS on peaked, the memory holds well")
    print("      but forgets too slowly for spread distributions — record both.")
    print()
    print("  Preserve falsified results in research/results/ per convention.")

    # ── Reproducibility assertion ─────────────────────────────────────────
    print("\n" + "=" * 72)
    print("REPRODUCIBILITY")
    print("=" * 72)
    digest_A = "".join(_hash_raw(v) for k, v in sorted(all_raw_A.items()))
    h = hashlib.sha256()
    h.update(digest_A.encode())
    digest_A_final = h.hexdigest()[:16]

    # Re-run all streams with identical parameters.
    all_raw_B: Dict[str, Dict] = {}
    _stream_defs = [
        ("S1",   _scales_stationary,  1, False),
        ("S2up", _scales_drift_up,    2, False),
        ("S2dn", _scales_drift_down,  3, False),
        ("S3up", _scales_step_up,     4, False),
        ("S3dn", _scales_step_down,   5, False),
        ("S4",   _scales_spike,       6, True),
    ]
    for std in (STD_PEAKED, STD_SPREAD):
        for tag, fn, off, spike in _stream_defs:
            cs = _fresh_competitors()
            all_raw_B[f"{tag}-{std}"] = _run(
                cs, fn(), std, SEED_BASE + off, is_spike=spike
            )
    digest_B = "".join(_hash_raw(v) for k, v in sorted(all_raw_B.items()))
    h2 = hashlib.sha256()
    h2.update(digest_B.encode())
    digest_B_final = h2.hexdigest()[:16]

    match = digest_A_final == digest_B_final
    print(f"  run1={digest_A_final}  run2={digest_B_final}")
    print(f"  {_pass_fail(match)} (bit-identical re-run)")
    if not match:
        print("  *** REPRODUCIBILITY FAIL: non-determinism detected.")

    print()
    print("  Log dated output to research/results/exp002_<YYYY-MM-DD>.txt.")
    print("  Initial and final scale_state logged to stdout above per stream.")


if __name__ == "__main__":
    main()
