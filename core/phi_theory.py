"""phi_theory.py — The Phi-Handshake: self-similar, anchorless weight mapping.

================================================================================
 HORUS-NFE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-07.

 This file and the concepts it embodies (the anchorless, phi-based
 computational framework and self-similarity as a "handshake") are proprietary
 and confidential. No license, express or implied, is granted. See ./NOTICE.
================================================================================

Purpose
-------
This is the *foundational* prototype for Horus-NFE. It demonstrates, in plain,
dependency-free Python, the core innovation of the project:

    A "Phi-quantized" weight distribution in which data is navigated by
    self-similar *proportion* (golden-ratio subdivision) rather than by
    linear *grid addressing* (integer index * stride + anchor).

The module is deliberately modular so that the geometric "free-tag" mapping can
be tested head-to-head against a standard linear grid baseline (see
`LinearGridAddressing` vs `PhiAddressing`, and `demo_benchmark`).

Nothing here depends on numpy or a GPU; it is meant to make the *idea*
legible and measurable, not fast. The physical/accelerated co-design lives
downstream of this reference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Sequence, Tuple

# --------------------------------------------------------------------------- #
# 0. Fundamental constants of the anchorless framework
# --------------------------------------------------------------------------- #

#: The golden ratio, phi = (1 + sqrt(5)) / 2. The single organizing constant of
#: the entire architecture. Every scale in the system is a power of phi.
PHI: float = (1.0 + math.sqrt(5.0)) / 2.0

#: 1/phi == phi - 1. The conjugate that makes the subdivision self-similar:
#: splitting an interval at PHI_INV leaves the two parts in ratio phi:1, and the
#: larger part is a scaled copy of the whole. This is *why* the map is anchorless.
PHI_INV: float = PHI - 1.0

#: The golden angle in turns (fraction of a full circle). Placing successive
#: points this far apart yields the maximally-uniform, non-repeating
#: distribution we exploit for resolution-follows-information sampling.
GOLDEN_ANGLE_TURNS: float = PHI_INV * PHI_INV  # == 2 - phi == 0.381966...


# --------------------------------------------------------------------------- #
# 1. The addressing protocols — the crux of the comparison
# --------------------------------------------------------------------------- #
#
# The whole thesis of Horus-NFE is that *how you address memory* is a design
# choice with real efficiency consequences. We formalize two addressing schemes
# behind one tiny interface so they can be benchmarked apples-to-apples.


class Addressing:
    """Abstract map from a normalized coordinate t in [0, 1) to a storage slot.

    Subclasses implement `position(t)` returning a float in [0, 1). Concrete
    engines quantize that position into a physical slot; here we keep it
    continuous so the *distribution* of slots is what we study.
    """

    name: str = "abstract"

    def position(self, t: float) -> float:  # pragma: no cover - interface
        raise NotImplementedError

    def sample(self, n: int) -> List[float]:
        """Return the storage positions for `n` logical elements."""
        return [self.position(i / n) for i in range(n)]


class LinearGridAddressing(Addressing):
    """The standard baseline: anchored, uniform, integer-strided grid.

    position(t) = t. Every slot is equidistant from its neighbors; resolution
    is uniform everywhere regardless of where information actually lives. This
    is the incumbent that the phi mapping must beat on real workloads.
    """

    name = "linear-grid"

    def position(self, t: float) -> float:
        return t % 1.0


class PhiAddressing(Addressing):
    """The anchorless, self-similar mapping (the 'free-tag' geometric map).

    Successive logical elements are placed by advancing the golden angle around
    the unit interval:

        position(k/n) = frac(k * PHI_INV)

    The resulting set of points is a low-discrepancy (quasi-random) sequence:
    it is self-similar under phi-scaling and has *no repeating stride and no
    privileged anchor*. Any point is as good an origin as any other — which is
    exactly what lets two phi-structured modules "handshake" without agreeing
    on a shared zero.
    """

    name = "phi-handshake"

    def position(self, t: float) -> float:
        # t is treated as a continuous index in turns; frac() folds it onto the
        # unit interval. Multiplying by PHI_INV is the golden-angle advance.
        return (t * PHI_INV) % 1.0

    def sample(self, n: int) -> List[float]:
        # Direct additive-recurrence form of the low-discrepancy sequence.
        return [(k * PHI_INV) % 1.0 for k in range(n)]


# --------------------------------------------------------------------------- #
# 2. Phi-quantized weight distribution
# --------------------------------------------------------------------------- #


@dataclass
class PhiQuantizedWeights:
    """A weight vector whose *levels* are drawn from a phi-self-similar codebook.

    Standard quantization uses a uniform codebook: levels 0, 1/L, 2/L, ... , 1.
    That is a linear grid in value-space and it wastes resolution on ranges the
    weights rarely occupy. Trained weights, however, are overwhelmingly small:
    their mass concentrates near zero. Spending equal resolution on the tails
    is the linear grid's hidden inefficiency.

    The phi-quantized codebook instead places reconstruction points on
    *self-similar shells* whose magnitudes decay by 1/phi:

        levels = { 0 } U { +/- hi * PHI_INV**j  for j = 0, 1, 2, ... }

    Consecutive shells stand in the ratio phi:1, so zooming toward zero reveals
    the *same* proportional spacing at every scale — the value-space analogue of
    `PhiAddressing`. Resolution therefore follows information: it densifies
    exactly where weights cluster (near zero) and thins where they are rare.
    A hardware substrate stores this as a compact *generator* (a seed magnitude
    and the scale rule 1/phi) rather than an explicit table.

    Attributes
    ----------
    levels:
        Number of reconstruction points in the codebook.
    lo, hi:
        Value range the codebook spans (assumed symmetric about 0).
    """

    levels: int
    lo: float = -1.0
    hi: float = 1.0
    _codebook: List[float] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._codebook = self._build_codebook()

    def _build_codebook(self) -> List[float]:
        # Self-similar geometric shells decaying by 1/phi, mirrored about zero.
        # `hi` sets the outermost shell; each inner shell is PHI_INV times the
        # previous one, so the set is invariant under phi-scaling toward 0.
        mag = max(abs(self.lo), abs(self.hi))
        book = [0.0]
        # Alternate +/- shells so that a given `levels` budget spends evenly on
        # both signs while still concentrating near zero.
        j = 0
        while len(book) < self.levels:
            shell = mag * (PHI_INV ** j)
            book.append(shell)
            if len(book) < self.levels:
                book.append(-shell)
            j += 1
        book.sort()
        return book

    @property
    def codebook(self) -> List[float]:
        return list(self._codebook)

    def quantize(self, value: float) -> Tuple[int, float]:
        """Snap `value` to the nearest codebook level.

        Returns (index, reconstructed_value). The index is the compact code an
        engine would actually store; reconstruction is a codebook lookup.
        """
        best_i, best_v, best_d = 0, self._codebook[0], math.inf
        for i, level in enumerate(self._codebook):
            d = abs(level - value)
            if d < best_d:
                best_i, best_v, best_d = i, level, d
        return best_i, best_v

    def quantize_all(self, values: Sequence[float]) -> Tuple[List[int], List[float]]:
        idx: List[int] = []
        rec: List[float] = []
        for v in values:
            i, r = self.quantize(v)
            idx.append(i)
            rec.append(r)
        return idx, rec

    def reconstruction_error(self, values: Sequence[float]) -> float:
        """Mean-squared error of quantizing then reconstructing `values`."""
        if not values:
            return 0.0
        _, rec = self.quantize_all(values)
        return sum((v - r) ** 2 for v, r in zip(values, rec)) / len(values)


# --------------------------------------------------------------------------- #
# 3. The Handshake — matching two structures by proportion, not by address
# --------------------------------------------------------------------------- #


@dataclass
class PhiTile:
    """A self-similar tile of the representation.

    A tile is defined *anchorlessly*: by a scale (a power of phi) and a phase,
    never by an absolute origin. Two tiles interoperate — "handshake" — when one
    is a phi-scaled copy of the other, i.e. their scales differ by an integer
    power of phi and their phases align modulo the golden angle.
    """

    scale_exponent: int  # tile scale is PHI ** scale_exponent
    phase: float = 0.0    # cumulative golden-angle phase, in turns (unfolded)

    @property
    def scale(self) -> float:
        return PHI ** self.scale_exponent

    def child(self) -> "PhiTile":
        """Descend one self-similar level (the recursive subdivision step).

        Each descent shrinks the scale by one power of phi and advances the
        phase by exactly one golden angle. Phase is kept *unfolded* (not taken
        mod 1): the golden angle is irrational in turns, so folding would
        destroy the exact integer relationship that lets descendants be
        recognized as counterparts of their ancestor.
        """
        return PhiTile(
            scale_exponent=self.scale_exponent - 1,
            phase=self.phase + GOLDEN_ANGLE_TURNS,
        )

    def descend(self, depth: int) -> "PhiTile":
        tile = self
        for _ in range(depth):
            tile = tile.child()
        return tile


def handshake(a: PhiTile, b: PhiTile, phase_tol: float = 1e-9) -> bool:
    """Return True if tiles `a` and `b` are self-similar counterparts.

    The handshake succeeds when the two tiles are related purely by phi-scaling:
    their phase difference is an *integer number of golden angles*. When it
    holds, one tile is reachable from the other by repeated self-similar
    subdivision, so either can address data in the other by proportion alone —
    no shared anchor, no stride negotiation. This is the "free-tag" composition
    the manifesto describes.
    """
    steps = (a.phase - b.phase) / GOLDEN_ANGLE_TURNS
    return abs(steps - round(steps)) <= phase_tol


# --------------------------------------------------------------------------- #
# 4. Discrepancy: the quantitative reason the phi map is more efficient
# --------------------------------------------------------------------------- #


def star_discrepancy_1d(points: Sequence[float]) -> float:
    """Approximate star discrepancy of a point set in [0,1).

    Discrepancy measures how far a point set deviates from perfectly uniform
    coverage. *Lower is better.* This is the single number that captures why
    golden-angle placement beats a jittered/linear grid for the same budget:
    it covers the space more evenly at every scale, so a fixed number of stored
    points resolves more structure.
    """
    n = len(points)
    if n == 0:
        return 1.0
    xs = sorted(points)
    d = 0.0
    for i, x in enumerate(xs):
        # empirical vs. ideal fraction of points below each x
        d = max(d, abs((i + 1) / n - x), abs(i / n - x))
    return d


# --------------------------------------------------------------------------- #
# 5. Reference benchmark harness (modularity in action)
# --------------------------------------------------------------------------- #


def _lcg(seed: int) -> Callable[[], float]:
    """Tiny self-contained PRNG so the demo needs no imports/determinism deps."""
    state = seed & 0xFFFFFFFF

    def rnd() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    return rnd


def _clipped_gauss(rnd: Callable[[], float], std: float = 0.15) -> float:
    """Sample a clipped Gaussian in [-1, 1] via Box-Muller (no external deps)."""
    u1 = max(rnd(), 1e-12)
    u2 = rnd()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return max(-1.0, min(1.0, z * std))


def _prefix_grid(n: int, k: int) -> List[float]:
    """First `k` slots of a *linear grid pre-planned for `n` elements*.

    This models the incumbent's failure mode: a uniform grid must commit to its
    resolution up front. If only `k < n` elements have arrived (or fit in the
    budget), the used slots are bunched into [0, k/n) and the rest of the space
    is empty. The grid cannot adapt without being rebuilt.
    """
    return [i / n for i in range(k)]


def demo_benchmark(n: int = 256) -> None:
    """Compare linear-grid vs phi-handshake addressing on coverage quality.

    This is the seed of the head-to-head evaluation the manifesto commits to:
    identical budget `n`, two addressing schemes, one objective metric.

    The honest metric is *extensibility*. A fixed-size uniform grid has the best
    possible discrepancy in 1D — but only if you always use exactly `n` points
    and never change your mind. The anchorless phi map instead keeps *every
    prefix* near-uniform, so the engine can stop at any budget, stream elements
    in, or reallocate resolution on the fly with no rebuild. We measure the mean
    star discrepancy averaged over all prefixes k = 1..n.
    """
    phi_scheme = PhiAddressing()
    phi_points = phi_scheme.sample(n)

    def avg_prefix_discrepancy(points_for_k) -> float:
        total = 0.0
        for k in range(1, n + 1):
            total += star_discrepancy_1d(points_for_k(k))
        return total / n

    phi_avg = avg_prefix_discrepancy(lambda k: phi_points[:k])
    grid_avg = avg_prefix_discrepancy(lambda k: _prefix_grid(n, k))

    print(f"Horus-NFE :: mean prefix discrepancy over k=1..{n} (lower is better)")
    print("  (extensibility test: can the map stop at any budget?)")
    print("-" * 60)
    print(f"  linear-grid      mean prefix discrepancy = {grid_avg:.6f}")
    print(f"  phi-handshake    mean prefix discrepancy = {phi_avg:.6f}")
    if phi_avg < grid_avg:
        print(f"  -> phi map is {grid_avg / phi_avg:.1f}x more uniform across budgets")

    # Weight-quantization comparison on a peaked, small-variance distribution.
    # Trained network weights are overwhelmingly small; a zero-mean Gaussian
    # with modest std is the standard first-order model. This peaked regime is
    # where a self-similar (denser-near-zero) codebook is expected to shine.
    # NOTE (honest caveat): as the distribution spreads out (std >~ 0.25) the
    # geometric shells leave gaps in the tails and the uniform grid catches up
    # and overtakes. We instrument the win; we do not assume it universally.
    rnd = _lcg(seed=1618033)
    values = [_clipped_gauss(rnd, std=0.15) for _ in range(8192)]

    print()
    print("Weight quantization MSE, peaked weights (std=0.15, lower is better)")
    print("-" * 56)
    levels = 16
    phi_wq = PhiQuantizedWeights(levels=levels)
    # Uniform-codebook baseline expressed through the same machinery.
    uniform_wq = PhiQuantizedWeights(levels=levels)
    uniform_wq._codebook = [  # override with a linear grid for comparison
        -1.0 + 2.0 * i / (levels - 1) for i in range(levels)
    ]
    print(f"  linear-codebook  MSE = {uniform_wq.reconstruction_error(values):.6e}")
    print(f"  phi-codebook     MSE = {phi_wq.reconstruction_error(values):.6e}")

    # Handshake demonstration: a tile and its descendants remain counterparts.
    print()
    print("Handshake check (self-similar counterparts must mesh)")
    print("-" * 56)
    root = PhiTile(scale_exponent=0, phase=0.0)
    deep = root.descend(5)
    print(f"  root <-> depth-5 descendant : handshake={handshake(root, deep)}")
    stranger = PhiTile(scale_exponent=-5, phase=0.5)
    print(f"  root <-> unrelated tile     : handshake={handshake(root, stranger)}")


if __name__ == "__main__":
    demo_benchmark()
