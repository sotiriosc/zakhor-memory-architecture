# Architecture Note 00 — Anchorless Addressing

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-07.  See ../NOTICE.
-->

**Status:** Draft v0.1 · **Author:** Sotirios Chortogiannos · **Date:** 2026-07-07

This is the first formal design note for Zakhor Memory Architecture. It states the problem with
linear grid addressing, defines the anchorless φ-addressing scheme precisely,
and derives the properties the `/core` prototype (`phi_theory.py`) exploits.

---

## 1. The problem: the anchor tax

Every mainstream tensor engine addresses memory as

```
address(i) = anchor + i × stride
```

Three costs follow directly from this formula:

1. **Committed resolution.** A grid of `n` slots must choose `n` up front.
   Growing, shrinking, or refining the representation means rebuilding the
   grid and re-anchoring every consumer.
2. **Uniform spend.** Every region of the representation gets identical
   resolution regardless of its information content. Trained weights
   concentrate near zero; a uniform value grid wastes most of its levels on
   tails the weights rarely occupy.
3. **Address-space negotiation.** Two components can only interoperate if they
   agree on `anchor` and `stride` — a global contract that every module must
   honor, and that couples otherwise independent parts of the system.

We call the sum of these the **anchor tax**.

## 2. The proposal: navigation by proportion

Zakhor Memory Architecture replaces the affine map with a **self-similar recurrence** built on
the golden ratio φ = (1+√5)/2 and its conjugate 1/φ = φ − 1 ≈ 0.618:

```
position(k) = frac(k / φ)          (the golden-angle sequence)
```

Three properties, each answering one component of the anchor tax:

1. **Every prefix is near-uniform.** The golden-angle sequence is a
   low-discrepancy sequence: for *any* budget `k`, the first `k` points cover
   the space almost evenly. The engine can stop, stream, or refine at any
   point with no rebuild. (Measured in `demo_benchmark`: ~15× lower mean
   prefix discrepancy than a pre-committed grid at n=256.)
2. **Resolution follows information.** In value-space, the φ-codebook places
   reconstruction shells at magnitudes `hi · (1/φ)^j`, densifying toward zero
   exactly where weight mass concentrates. (Measured: ~3× lower MSE than a
   uniform codebook on peaked weights, std = 0.15.)
3. **The handshake replaces negotiation.** Two φ-structured tiles interoperate
   iff their phases differ by an integer number of golden angles — a purely
   *relational* test with no shared origin. This is the "free-tag" mapping:
   composition is free because compatibility is guaranteed by construction.

## 3. Why φ specifically

φ is the "most irrational" number: its continued fraction is [1; 1, 1, …], so
its rational approximations converge as slowly as possible. Consequences:

- The sequence `frac(k/φ)` never falls into a near-repeating lattice at any
  scale — the three-distance theorem guarantees at most three distinct gap
  sizes for every prefix, in golden ratio to one another.
- Subdividing an interval at 1/φ leaves the larger part a scaled copy of the
  whole. Self-similarity is therefore *exact*, not approximate, which is what
  makes the handshake test an integer test rather than a tolerance heuristic.

No other constant has both properties simultaneously.

## 4. Honest caveats (to be instrumented, not assumed)

- A fixed-size uniform grid has *optimal* discrepancy in 1D if the budget
  never changes. The φ map wins on **extensibility**, not on a single frozen
  snapshot. Benchmarks must reflect this framing.
- The φ-codebook's advantage inverts for spread-out weight distributions
  (std ≳ 0.25): geometric shells leave tail gaps. Regime boundaries are an
  open experimental question (see `research/exp001`).
- Multi-dimensional generalization (via Kronecker/R_d sequences or golden
  spirals) is designed but not yet prototyped.

## 5. Roadmap

| Stage | Deliverable | Location |
|---|---|---|
| 0 | Reference prototype + demo benchmark | `core/phi_theory.py` (done) |
| 1 | Regime-boundary experiments | `research/exp001_regime_sweep.py` |
| 2 | Multi-dimensional φ-addressing | `core/` (planned) |
| 3 | Memory-topology co-design sketch | `docs/` (planned) |
| 4 | Agentic handshake protocol between engine modules | `core/` (planned) |
