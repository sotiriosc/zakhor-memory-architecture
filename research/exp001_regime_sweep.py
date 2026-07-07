"""exp001_regime_sweep.py — Where does the phi-codebook win, and where does it lose?

================================================================================
 HORUS-NFE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-07.  See ../NOTICE.
================================================================================

Experiment 001. The manifesto commits to instrumented claims, so the first
experiment maps the *regime boundary* of the phi-quantized codebook:

  1. Quantization: sweep the weight-distribution spread (Gaussian std) and
     record MSE for the phi-codebook vs. a uniform linear codebook at equal
     level budgets. Hypothesis: phi wins for peaked distributions and the
     uniform grid overtakes as the distribution spreads.

  2. Addressing: sweep the point budget n and record mean prefix discrepancy
     for phi-handshake vs. pre-committed linear grid. Hypothesis: the phi
     map's extensibility advantage holds across budgets.

Run from the repository root:

    python3 research/exp001_regime_sweep.py

Results are printed and appended-safe: redirect to research/results/ to keep
a dated record.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.phi_theory import (  # noqa: E402
    PhiAddressing,
    PhiQuantizedWeights,
    star_discrepancy_1d,
)
from core.phi_theory import _clipped_gauss, _lcg, _prefix_grid  # noqa: E402

SEED = 1618033
SAMPLES = 8192
LEVELS = 16


def uniform_codebook(levels: int) -> PhiQuantizedWeights:
    """Baseline quantizer: same machinery, linear-grid codebook."""
    wq = PhiQuantizedWeights(levels=levels)
    wq._codebook = [-1.0 + 2.0 * i / (levels - 1) for i in range(levels)]
    return wq


def sweep_quantization() -> None:
    print(f"[exp001a] Quantization MSE vs. weight spread ({LEVELS} levels, "
          f"{SAMPLES} samples, lower is better)")
    print(f"{'std':>6} | {'linear MSE':>12} | {'phi MSE':>12} | winner")
    print("-" * 56)
    phi_wq = PhiQuantizedWeights(levels=LEVELS)
    lin_wq = uniform_codebook(LEVELS)
    for std in (0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        rnd = _lcg(seed=SEED)
        values = [_clipped_gauss(rnd, std=std) for _ in range(SAMPLES)]
        lin = lin_wq.reconstruction_error(values)
        phi = phi_wq.reconstruction_error(values)
        winner = "phi" if phi < lin else "linear"
        ratio = (lin / phi) if phi < lin else (phi / lin)
        print(f"{std:>6.2f} | {lin:>12.4e} | {phi:>12.4e} | {winner} ({ratio:.1f}x)")
    print()


def sweep_addressing() -> None:
    print("[exp001b] Mean prefix discrepancy vs. budget (lower is better)")
    print(f"{'n':>6} | {'linear grid':>12} | {'phi map':>12} | advantage")
    print("-" * 56)
    phi_scheme = PhiAddressing()
    for n in (16, 64, 256, 1024):
        phi_points = phi_scheme.sample(n)
        phi_avg = sum(
            star_discrepancy_1d(phi_points[:k]) for k in range(1, n + 1)
        ) / n
        grid_avg = sum(
            star_discrepancy_1d(_prefix_grid(n, k)) for k in range(1, n + 1)
        ) / n
        print(f"{n:>6} | {grid_avg:>12.6f} | {phi_avg:>12.6f} | "
              f"{grid_avg / phi_avg:.1f}x")
    print()


if __name__ == "__main__":
    print("Horus-NFE :: Experiment 001 — regime sweep")
    print("=" * 56)
    sweep_quantization()
    sweep_addressing()
    print("Conclusion criteria: record the std at which the linear codebook")
    print("overtakes phi (regime boundary), and confirm the addressing")
    print("advantage grows with budget. Log dated output to research/results/.")
