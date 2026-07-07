# Architectural Theory

<!--
 HORUS-NFE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Steward / Founder: Sotirios Chortogiannos.  See ../NOTICE.
-->

This directory holds the formal architectural theory for Horus-NFE: design
documents, derivations, and co-design notes for the geometric NFE engine.

## Planned topics

- **Anchorless addressing** — why fixed origins and uniform strides are a hidden
  tax on inference.
- **The φ-handshake** — self-similarity as an inter-component protocol.
- **Phi-quantized representations** — resolution that follows information density.
- **Hardware/software co-design** — mapping self-similar memory topology to
  algorithmic primitives in `/core`.

Start with [`MANIFESTO.md`](../MANIFESTO.md) for the founding statement, then
see [`core/phi_theory.py`](../core/phi_theory.py) for the reference prototype.
