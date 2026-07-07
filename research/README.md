# Research & Experiments

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Steward / Founder: Sotirios Chortogiannos.  See ../NOTICE.
-->

This directory is for experiments, benchmark results, and research notes that
validate (or falsify) claims about the Zakhor Memory Architecture geometric mapping.

## Benchmark commitment

The project prioritizes **head-to-head comparison** of the free-tag φ-handshake
mapping against standard linear grid baselines. The seed harness lives in
[`core/phi_theory.py`](../core/phi_theory.py) (`demo_benchmark`).

Future work here may include:

- Prefix discrepancy sweeps across budgets and dimensions
- Weight-quantization MSE across distribution regimes
- End-to-end inference latency/energy vs. linear layouts
- Notes on failure modes and honest caveats
