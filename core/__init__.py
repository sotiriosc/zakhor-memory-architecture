"""Zakhor Memory Architecture core algorithmic prototypes.

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 Inception: 2026-07-07.

 See ../NOTICE.
================================================================================
"""

from .phi_theory import (
    PHI,
    PHI_INV,
    GOLDEN_ANGLE_TURNS,
    Addressing,
    LinearGridAddressing,
    PhiAddressing,
    PhiQuantizedWeights,
    PhiTile,
    demo_benchmark,
    handshake,
    star_discrepancy_1d,
)

__all__ = [
    "PHI",
    "PHI_INV",
    "GOLDEN_ANGLE_TURNS",
    "Addressing",
    "LinearGridAddressing",
    "PhiAddressing",
    "PhiQuantizedWeights",
    "PhiTile",
    "demo_benchmark",
    "handshake",
    "star_discrepancy_1d",
]
