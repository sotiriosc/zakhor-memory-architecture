# Zakhor Memory Architecture

**Geometric, self-similar neural inference hardware/software co-design.**

This repository is the founding research codebase for Zakhor Memory Architecture, an original
architectural research project led by **Sotirios Chortogiannos**. Read
[`MANIFESTO.md`](MANIFESTO.md) for the project's philosophy, objectives, and
intellectual property record.

> **Status:** Proprietary research, in active development. See [`NOTICE`](NOTICE).

## Quick start

Run the foundational phi-handshake prototype and its head-to-head benchmark:

```bash
python3 core/phi_theory.py
```

This compares **linear grid addressing** against the **phi-handshake** geometric
mapping on coverage quality and phi-quantized weight reconstruction.

## Repository layout

```
zakhor-memory-architecture/
├── MANIFESTO.md          # Founding record and project mandate
├── NOTICE                # Proprietary / stewardship notice
├── core/                 # Algorithmic prototypes
│   └── phi_theory.py     # Phi-quantized weights & handshake logic
├── docs/                 # Architectural theory
└── research/             # Experiments, benchmarks, notes
```

## Core idea

Conventional inference engines anchor computation to a linear grid: integer
indices, fixed strides, uniform resolution. Zakhor Memory Architecture proposes an **anchorless,
φ-based framework** where data is navigated by **self-similar proportion**
(golden-ratio subdivision) rather than offset from an origin. Components
coordinate through a geometric **handshake** — matching φ-scaled structure —
instead of negotiating a shared address space.

## Modularity & benchmarks

Every geometric primitive in `/core` is designed to be swappable and measurable.
The `demo_benchmark()` harness in `phi_theory.py` is the seed of the project's
commitment to instrument the **free-tag geometric mapping** against standard
linear baselines — no claim without a number.
