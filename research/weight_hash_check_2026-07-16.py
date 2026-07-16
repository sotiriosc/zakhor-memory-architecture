"""weight_hash_check_2026-07-16.py — Does training itself reproduce bit-identically?

================================================================================
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-16.  See ../NOTICE.
================================================================================

Status: POST-HOC VERIFICATION — not a pre-registered experiment, no verdict.

exp101-104's reproduction (2026-07-16) found every double-run SHA-256 over
predictions/accuracies bit-identical between the external sandbox
(sklearn 1.8.0, numpy 2.4.4) and this repository (sklearn 1.7.2,
numpy 2.2.6). That comparison never directly hashed the trained weights —
it hashed downstream predictions. Identical predictions are consistent
with, but do not prove, identical weights (a numerically different
optimizer path could in principle land on different weights that still
classify identically on this test split).

This script reproduces exp101_contact.py's exact training call (same
loader, same split, same seed, same MLPClassifier hyperparameters) and
adds one direct check: the SHA-256 of the concatenated first-layer-through-
last-layer weight matrices, byte-for-byte off clf.coefs_.

Left untouched by design: research/exp101_contact.py itself (a ported
artifact whose byte-identity to the external original is part of its own
provenance record — this check runs alongside it, not inside it).

Run from repository root:

    python3 research/weight_hash_check_2026-07-16.py
"""

from __future__ import annotations

import hashlib

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

SEED = 20260712   # exp101_contact.SEED, unchanged


def train_and_hash() -> str:
    X, y = load_digits(return_X_y=True)
    X = X / 16.0
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.5, random_state=SEED, stratify=y
    )
    clf = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=800, random_state=SEED)
    clf.fit(Xtr, ytr)
    weight_hash = hashlib.sha256(
        np.concatenate([w.ravel() for w in clf.coefs_]).tobytes()
    ).hexdigest()[:16]
    return weight_hash


def main() -> None:
    import sklearn
    print("Zakhor Memory Architecture :: Weight-Hash Check (2026-07-16)")
    print("=" * 72)
    print(f"  Environment: sklearn {sklearn.__version__}, numpy {np.__version__}")
    h = train_and_hash()
    print(f"  Weight hash (SHA-256[:16] of concatenated clf.coefs_): {h}")
    print()
    print("  Original external-sandbox weight hash: NOT RECORDED — the")
    print("  original exp101 artifact hashed predictions/accuracies only,")
    print("  never the raw weight arrays. This run's hash is the first one")
    print("  on record; it establishes a baseline for this repository's")
    print("  environment (sklearn/numpy versions above), not yet a")
    print("  cross-environment comparison.")
    print()
    print("  What IS confirmed by the exp101-104 reproduction (2026-07-16):")
    print("  predictions and accuracies were bit-identical across sklearn")
    print("  1.8.0/numpy 2.4.4 (external) and this repository's sklearn/numpy")
    print("  (above). Identical predictions on identical inputs, from a")
    print("  deterministic feed-forward pass, is only possible if the")
    print("  weights that produced them were either (a) bit-identical, or")
    print("  (b) different but coincidentally classify every one of ~1796")
    print("  x2 test-stream samples across four experiments identically —")
    print("  vanishingly unlikely for a 64-32-10 MLP unless the weights")
    print("  themselves matched. This hash is the direct instrument for")
    print("  confirming which of those it was, going forward: run this")
    print("  script in any environment and compare the printed hash")
    print("  against the value recorded in the dated results file.")


if __name__ == "__main__":
    main()
