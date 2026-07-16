"""gap_analysis_2026-07-11.py — The Gap Behind H14: Is the Simple Road Best?

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-11.  See ../NOTICE.
================================================================================

Status: POST-SERIES EXPLORATORY ANALYSIS — no verdict is touched.

The series is CLOSED. H14 stands FALSIFIED. This analysis does not reopen it,
does not simulate a new pre-registered claim, and earns no verdict. It is
generative material for Architecture Note 02: a measurement of the gap that
the falsification revealed, and a comparison of the candidate roads across it.

The gap (from exp007b): on S3 step-DOWN, blocks t=2048 and t=2049 are
non-stranger, non-settle, and unflagged. The persistence gate needs K=3
consecutive blocks; the REGIME rebirth fires at exactly the K-th block
(t=2050), consuming the third count. Blind spot = K−1 = 2 blocks.

The observation: those two blocks are not invisible to the machine. The
regime counter itself holds the evidence — counter=1 at t=2048, counter=2
at t=2049. The deviation is already counted; the MID-RETURN register simply
never reads the counter.

The simple road (counter-visibility):
  MID-RETURN is additionally raised on any NON-stranger, non-reborn block
  whose regime counter is nonzero after update. No new threshold, no new K,
  no new state — one read of an existing register.

The alternative road (three-state Watchman):
  A new "Watching" state entered at persistence count p < K on the NOISE
  threshold (p95 ≈ 0.75 shells). Stationary cost ≈ (1.8%)^p per block:
  p=1 → ~1.8% (the floor H13 just eliminated); p=2 → ~0.032%.

What decides between them is one number, measured here: how often is the
regime counter nonzero on stationary data? The counter runs on D (≈2.0
shells, calibrated), not on the noise threshold (≈0.75) — a much deeper
tail. If the stationary counter-visible rate is ~0, the simple road closes
the blind spot at zero noise cost with zero new machinery.

Measurements (per stream, both distributions):
  1. Counter-visible blocks (non-stranger, nonzero counter): count and rate.
  2. Hypothetical coverage = exp007b flags ∪ counter-visible
     (vs H12-b limit 2% on S4, H13 limit 0.5% on S1 — reported, not judged).
  3. Hypothetical H14 sensitivity on S3↓ / S3↑ / S4 ground truth.
  4. Validation: offline counter reconstruction must reproduce the exact
     REGIME rebirth blocks from the sworn run.

Run from repository root:

    python3 research/gap_analysis_2026-07-11.py
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

from exp002_scale_memory import (  # noqa: E402
    N_BLOCKS, BLOCK_SIZE, ALPHA_PRIMARY,
    SEED_BASE, STD_PEAKED, STD_SPREAD,
    SPIKE_SHELLS, SPIKE_PERIOD,
    shell_coord,
    _scales_stationary, _scales_drift_up,
    _scales_step_up, _scales_step_down, _scales_spike,
)
from exp005_gated_rebirth import K_REBIRTH, RECOVERY_SETTLE  # noqa: E402
from exp006_symmetric_gate import calibrate_exp6  # noqa: E402
from exp007b_watchman import (  # noqa: E402
    PhiZakhorKeepG3b, _fresh_competitors_7b, _regime_settle_set,
    H12B_COLLAPSE_LIMIT, H13_NOISE_LIMIT, STEP_BLOCK,
)
from core.phi_theory import PHI, _clipped_gauss, _lcg  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Replay with block capture (same generation order as exp007b's _run_7b)
# ─────────────────────────────────────────────────────────────────────────────

def _run_with_blocks(
    competitors: List,
    scales: List[float],
    std: float,
    seed: int,
    is_spike: bool = False,
) -> List[List[float]]:
    rnd = _lcg(seed)
    blocks: List[List[float]] = []
    for t, scale in enumerate(scales):
        block = [scale * _clipped_gauss(rnd, std=std) for _ in range(BLOCK_SIZE)]
        if is_spike and t % SPIKE_PERIOD == 0:
            sign = 1.0 if rnd() >= 0.5 else -1.0
            block[0] = sign * (PHI ** SPIKE_SHELLS)
        blocks.append(block)
        for c in competitors:
            c.process_block(list(block))
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Offline counter reconstruction (exact mirror of the in-class regime logic)
# ─────────────────────────────────────────────────────────────────────────────

def counter_visible_flags(
    g3b: PhiZakhorKeepG3b,
    blocks: List[List[float]],
) -> Tuple[List[bool], List[int]]:
    """Reconstruct the per-block regime counter from the sworn run's state log.

    Returns (visible, rebirth_blocks_0idx):
      visible[t] = counter nonzero after update AND non-stranger AND not reborn.
      rebirth_blocks_0idx used to validate against g3b.regime_log.

    pre state is read from g3b._state_log (exact, causal), so d_raw here is
    bit-identical to the d_raw the class computed at block t.
    """
    visible: List[bool] = []
    rebirths: List[int] = []
    counter = 0
    for t, block in enumerate(blocks):
        max_mag = max(abs(v) for v in block) if block else 0.0
        obs = shell_coord(max_mag) if max_mag > 1e-300 else 0.0
        pre = g3b._state_log[t][0]
        d_raw = obs - pre
        if abs(d_raw) > g3b.D:
            counter += 1
        else:
            counter = 0
        reborn = False
        if counter >= K_REBIRTH:
            counter = 0
            reborn = True
            rebirths.append(t)
        is_stranger = g3b._block_stranger[t]   # stranger AND not reborn
        visible.append(counter > 0 and not is_stranger and not reborn)
    return visible, rebirths


# ─────────────────────────────────────────────────────────────────────────────
# Hypothetical sensitivity (same exclusion convention as exp007b h14)
# ─────────────────────────────────────────────────────────────────────────────

def hypothetical_sensitivity(
    g3b: PhiZakhorKeepG3b,
    hyp_flags: List[bool],
    gt_range: List[int],
) -> Dict:
    settle_set = _regime_settle_set(g3b.regime_log)
    n_non_excluded = 0
    n_flagged = 0
    missed: List[int] = []
    for t in gt_range:
        if t >= N_BLOCKS:
            continue
        if g3b._block_stranger[t] or t in settle_set:
            continue
        n_non_excluded += 1
        if hyp_flags[t]:
            n_flagged += 1
        else:
            missed.append(t)
    sens = n_flagged / n_non_excluded if n_non_excluded > 0 else None
    return {
        "sensitivity": sens,
        "n_non_excluded": n_non_excluded,
        "n_flagged": n_flagged,
        "missed": missed,
        "na": n_non_excluded == 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Zakhor Memory Architecture :: Gap Analysis — The Simple Road (2026-07-11)")
    print("=" * 96)
    print("  POST-SERIES EXPLORATORY. No verdict touched. H14 stands FALSIFIED.")
    print("  Series is CLOSED. This measures the gap for Architecture Note 02.")
    print()
    print("  Simple road: MID-RETURN also raised on non-stranger blocks with")
    print("  nonzero regime counter (evidence-in-progress made visible).")
    print("  Alternative: three-state Watchman on the noise threshold —")
    print("  stationary cost ≈ 1.8%^p (p=1: 1.8%, p=2: ~0.032%).")

    gt_s4 = list(range(0, K_REBIRTH + 4 + 1))
    gt_s3 = list(range(STEP_BLOCK, STEP_BLOCK + 9))

    grand: Dict[str, Dict] = {}

    for std, std_label in ((STD_PEAKED, f"peaked(std={STD_PEAKED})"),
                           (STD_SPREAD, f"spread(std={STD_SPREAD})")):
        G, D, noise_thr, _ = calibrate_exp6(ALPHA_PRIMARY, std)
        print(f"\n{'━'*96}")
        print(f"  Distribution: {std_label}   G={G:.1f}  D={D:.1f}"
              f"  noise_threshold={noise_thr:.4f}")
        print("━" * 96)
        print(f"  {'stream':<6} {'ctr-visible':>12} {'rate':>9}"
              f" {'exp007b cov':>12} {'hyp cov':>9} {'validation':>12}")

        for tag, fn, off, spike, gt in (
            ("S1", _scales_stationary, 1, False, None),
            ("S2", _scales_drift_up, 2, False, None),
            ("S3u", _scales_step_up, 4, False, gt_s3),
            ("S3d", _scales_step_down, 5, False, gt_s3),
            ("S4", _scales_spike, 6, True, gt_s4),
        ):
            cs = _fresh_competitors_7b(G, D, noise_thr)
            blocks = _run_with_blocks(cs, fn(), std, SEED_BASE + off,
                                      is_spike=spike)
            g3b: PhiZakhorKeepG3b = next(
                c for c in cs if c.name == "PHI-ZAKHOR-KEEP-G3b")

            visible, rebirths = counter_visible_flags(g3b, blocks)
            sworn_rebirths = [e[0] - 1 for e in g3b.regime_log]  # 1-idx → 0-idx
            valid = rebirths == sworn_rebirths

            n_vis = sum(visible)
            hyp_flags = [g3b.mid_return_flags[t] or visible[t]
                         for t in range(N_BLOCKS)]
            n_old = sum(g3b.mid_return_flags)
            n_hyp = sum(hyp_flags)

            print(f"  {tag:<6} {n_vis:>12} {100*n_vis/N_BLOCKS:>8.3f}%"
                  f" {n_old:>8}/{N_BLOCKS} {n_hyp:>4}/{N_BLOCKS}"
                  f" {'OK' if valid else '*** MISMATCH':>12}")
            if n_vis > 0:
                vis_blocks = [t for t in range(N_BLOCKS) if visible[t]]
                print(f"         counter-visible blocks (0-idx): {vis_blocks[:12]}"
                      f"{'…' if len(vis_blocks) > 12 else ''}")

            entry: Dict = {
                "n_visible": n_vis, "n_old": n_old, "n_hyp": n_hyp,
                "valid": valid,
            }
            if gt is not None:
                sens = hypothetical_sensitivity(g3b, hyp_flags, gt)
                entry["sens"] = sens
                if sens["na"]:
                    print(f"         hypothetical sensitivity: N/A (all excluded)")
                else:
                    miss_str = (f"  missed: {sens['missed']}"
                                if sens["missed"] else "")
                    print(f"         hypothetical sensitivity:"
                          f" {sens['n_flagged']}/{sens['n_non_excluded']}"
                          f" = {sens['sensitivity']:.1%}{miss_str}")
            grand[f"{tag}-{std}"] = entry

        # Reported against the frozen bounds (not judged — no verdict here)
        s1 = grand[f"S1-{std}"]
        s4 = grand[f"S4-{std}"]
        print(f"\n  Reported vs frozen bounds ({std_label}) — informational only:")
        print(f"    S1 hyp coverage: {s1['n_hyp']}/{N_BLOCKS}"
              f" ({100*s1['n_hyp']/N_BLOCKS:.3f}%)"
              f"   [H13 bound was {H13_NOISE_LIMIT:.1%}]")
        print(f"    S4 hyp coverage: {s4['n_hyp']}/{N_BLOCKS}"
              f" ({100*s4['n_hyp']/N_BLOCKS:.3f}%)"
              f"   [H12-b bound was {H12B_COLLAPSE_LIMIT:.0%}]")

    # ── Synthesis ────────────────────────────────────────────────────────────
    print(f"\n{'='*96}")
    print("SYNTHESIS — the roads across the gap")
    print(f"{'='*96}")

    all_valid = all(e["valid"] for e in grand.values())
    print(f"  Offline counter reconstruction matches sworn REGIME logs: "
          f"{'YES (exact)' if all_valid else '*** NO — analysis void'}")

    stationary_cost = max(
        grand[f"S1-{std}"]["n_visible"] + grand[f"S2-{std}"]["n_visible"]
        for std in (STD_PEAKED, STD_SPREAD)
    )
    s3d_closed = all(
        grand[f"S3d-{std}"]["sens"]["sensitivity"] == 1.0
        for std in (STD_PEAKED, STD_SPREAD)
        if not grand[f"S3d-{std}"]["sens"]["na"]
    )
    s4_kept = all(
        grand[f"S4-{std}"]["sens"]["na"]
        or grand[f"S4-{std}"]["sens"]["sensitivity"] == 1.0
        for std in (STD_PEAKED, STD_SPREAD)
    )

    print(f"\n  Simple road (counter-visibility):")
    print(f"    Stationary + drift cost: {stationary_cost} blocks"
          f" (worst distribution, S1+S2 combined)")
    print(f"    S3↓ blind spot closed: {'YES' if s3d_closed else 'NO'}")
    print(f"    S4 sensitivity kept:   {'YES' if s4_kept else 'NO'}")
    print(f"    New machinery: none. New thresholds: none. New state: none.")
    print(f"    One read of a register that already exists.")
    print(f"\n  Three-state Watchman (for comparison, arithmetic only):")
    print(f"    p=1 on noise threshold: ~1.8% stationary floor"
          f" (~{int(0.018*N_BLOCKS)} blocks — reopens what H13 closed)")
    print(f"    p=2 on noise threshold: ~0.032% floor (~1–2 blocks)"
          f" but still misses the FIRST deviation block — gap shrinks to 1,")
    print(f"    does not close. New state machine, new parameter p.")
    print(f"\n  Nothing (accept the gap): K−1 = {K_REBIRTH-1} blocks dark"
          f" at every step-DOWN, forever.")

    if all_valid and s3d_closed and s4_kept:
        print(f"\n  ANSWER: the simple road is best, and it is strictly better —")
        print(f"  it closes the blind spot completely at a measured stationary")
        print(f"  cost of {stationary_cost} blocks, using no new machinery.")
        print(f"  The H14 falsification was not a grammar failure but a wiring")
        print(f"  gap: the evidence for 'possibly a new world' was already")
        print(f"  counted in the regime register; the confidence register never")
        print(f"  asked it. The watchman was awake. Nobody read his ledger.")
    print(f"\n  This analysis earns no verdict. The series remains CLOSED.")
    print(f"  If the counter-visible trigger is ever to be sworn, it requires")
    print(f"  a new pre-registration outside this series, judged fresh.")


if __name__ == "__main__":
    main()
