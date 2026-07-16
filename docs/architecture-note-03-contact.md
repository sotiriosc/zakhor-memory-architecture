# Architecture Note 03 — Contact

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-16.  See ../NOTICE.
-->

**Status:** Draft v0.1 · **Date:** 2026-07-16

This note is written from the ported exp101–104 ("Contact") artifacts only.
No new claims are made beyond what those pre-registrations, scripts, and
results establish. The exp00x series (exp001–exp007b) is CLOSED; its
deliverable, [Architecture Note 02](architecture-note-02-synthesis.md),
synthesizes that series. Nothing here reopens exp00x or touches Note 02's
verdicts — this note only proposes one addition to Note 02 §3/§4 (§4
below), on the strength of evidence Note 02 did not have when it was
written. Contact is a new series, on a real trained workload, testing
whether the zakhor scale controller — designed and closed on synthetic
streams — survives contact with (a) a real classifier, (b) shallow codebooks, and
(c) a foreign quantization format (binary block-floating-point).

---

## 1. What contact established

**(a) At deep codebooks, zakhor confers no accuracy advantage — its value
there is telemetry only, stated plainly.** At 16 φ-shells (exp101), ZAKHOR's
SPIKE normal-sample top-1 (0.9607) did not exceed DELAYED's (0.9624): P2
FALSIFIED. The codebook's ~1364× dynamic range absorbs a single spike's
window-poisoning damage on the industry-standard delayed-scaling baseline;
there is nothing left for the controller to protect against. At this depth
the controller's product is not accuracy but the audit trail: which frames
were corrupted, by name, with zero false alarms (§1e below).

**(b) The shallow-water rule: the advantage appears where dynamic range is
scarce, peaked near 6 shells.** Sweeping LEVELS ∈ {4, 6, 8, 16} (exp102),
the SPIKE normal-sample gap (ZAKHOR − DELAYED) is +12.2% at L=4, **+14.7%
at L=6** (peak), +13.8% at L=8, and −0.2% at L=16 — the exp101 null,
recovered as one point on a curve rather than a contradiction. The
mechanism is now visible in the data at every depth: each spike inflates
DELAYED's window ceiling ×123 for W=16 blocks; when the codebook is
shallow, normal data sitting under that inflated ceiling falls below the
representable floor and underflows to zero for the whole window. ZAKHOR
gates the spike out of its state entirely (displacement on strangers ≡ 0.0
at every depth, exact), so its ceiling never moves.

**(c) The gap survives full quantization.** exp104 quantizes weights
(per-block BFP, m=6, identical procedure for every competitor) in addition
to activations. Clean-stream accuracy for all three activation
controllers matches FP64 exactly (0.9700 = 0.9700 = 0.9700 = 0.9700);
weights-only quantization cost is zero. Under SPIKE, ZAKHOR's normal-sample
top-1 (0.9702) is **ORACLE-EQUIVALENT under attack** — identical to
ORACLE's per-block descriptive maximum (0.9702 = 0.9702) — against
DELAYED's 0.8456. The kept exponent, driven only by a causal scalar state,
matches the accuracy of a controller with foreknowledge of every block's
true maximum.

**(d) The controller is format-agnostic.** The `Zakhor` state machine
(log-φ leaky integrator, causal pre-update read, guard band G, symmetric
regime bound D, K in three roles, stranger gating, signed regime log) is
the same object in exp101 (φ-codebook), exp103 (binary BFP shared
exponent, m ∈ {3, 6}), and exp104 (BFP + quantized weights). Only the
quantizer changed — `quantize()` (φ-codebook) versus `bfp_quantize()`
(binary). The controller crossed from the phi-codebook to binary BFP
unchanged, and the payoff crossed with it: at m=6 (NFE-13's mantissa
width), the SPIKE normal-sample gap is +12.1%; at m=3 (aggressive
compression), +14.5% — both in the same 12–15% band the shallow-water
sweep established, on a wholly different arithmetic representation.

**(e) The confidence sideband.** Across every experiment, every depth, and
every mantissa width, the two hidden-layer stranger counts on SPIKE are
**exactly 17 and 17** — matching the true injected-spike count precisely,
every time, with zero misses and zero false positives. Displacement on
strangers is 0.0 (exact) in every recorded run. Regime events on CLEAN are
0 in every recorded run — zero hallucinated regimes anywhere. The
controller does not merely track scale; it names, without error, which
frames were attacked.

## 2. Falsifications and defects, preserved

**exp101 P1 (CLEAN, all controllers within 0.5% of FP64) — METRIC-DEFECT.**
Every controller, including ORACLE (a purely descriptive per-block
maximum with no adaptation to falsify), missed the 0.5% bound: ZAKHOR
−0.90%, DELAYED −0.67%, STATIC −0.61%, ORACLE −1.34%. A bound that even
the oracle cannot satisfy is not measuring controller quality; it is
measuring the network's own scale-sensitivity to 16-shell activation
quantization. The bound, not the mechanism, was wrong.

**exp101 P3 (REGIME-DOWN, ZAKHOR post-step ≥ DELAYED) — METRIC-DEFECT.**
ZAKHOR's post-step accuracy (0.1080) is numerically ≥ DELAYED's (0.0980),
but both — and ORACLE's (0.0980) — collapse to near chance level (10 
classes) after the permanent φ^-8 gain drop. The comparison cannot
discriminate controller quality when the network itself has failed for
every competitor simultaneously; it is measuring the network's
scale-sensitivity to a gain-drop, not the controller.

**exp101 P2 (SPIKE, ZAKHOR normal ≥ DELAYED) — FALSIFIED.** See §1a. The
damage model was wrong, not the mechanism: at 16 shells, depth absorbs
window poisoning before the controller ever gets a chance to matter.
exp102 subsequently vindicated the mechanism at shallower depths — the
falsification was a statement about where the codebook sat, not about
what the controller does.

**exp102 P7 (no honesty tax, |ZAKHOR − DELAYED| ≤ 1.0% on CLEAN) —
FALSIFIED at L=4.** CLEAN accuracy diff at L=4 is −2.1% (ZAKHOR 0.9366 vs
DELAYED 0.9577); at L=6/8/16 the diff is +0.1%/−0.3%/−0.2%, all within
bound. The guard band costs 2.1% when shells are scarcest — the honesty
tax is real at extreme shallowness, not a myth of the synthetic series.

**exp102 P8 (dose-response, gap non-increasing across L ∈ {4,6,8,16}) —
FALSIFIED.** The measured gaps are +12.2%, +14.7%, +13.8%, −0.2% — rising
from L=4 to L=6 before falling. The gap is peaked, not monotone. §1b's
"shallow-water rule" is the corrected shape: the payoff is not simply
"shallower is better," it has an interior maximum.

## 3. Open observations, unforced

**The logits layer's heavy tail.** The classifier's final (logits) layer
shows a materially different stranger rate than the two hidden layers at
every depth and every experiment. Hidden layers: exactly 0 strangers on
CLEAN, exactly 17 on SPIKE, everywhere, exact. The logits layer: 54–69
strangers on CLEAN streams and 68–82 on SPIKE/REGIME streams, across
exp101–104 — a background declaration rate the hidden layers do not
show at all. Calibration-window adequacy is apparently per-layer: the
last layer of a classifier, with a different activation distribution
(unbounded logit magnitudes, not ReLU-clipped), is not like the others.
This is reported as observed, not diagnosed — no verdict is attached.

**A quiet confirmation of note-sufficiency.** The ported `Zakhor` class
(exp101) implements exactly three flags: INFANCY, REGIME_SETTLE, STRANGER.
It does *not* implement a persistence-gated MID-RETURN trigger — the
mechanism that exp007b's H14 left FALSIFIED at the close of the prior
series. An external reimplementation working from the design-rule table
alone correctly omitted the one register that the table's source series
did not establish. This is indirect evidence for exp101's P5
(note-sufficiency PASS): the table transmitted exactly the established
mechanisms, no more, no less.

**The unopened doors.** Three lines of inquiry this series did not walk
through: gradient-accumulation streams (Contact tested only forward-pass
activation and weight quantization); the honesty instrument proper (the
`s_j`-relative promise metric that would replace exp007's METRIC-DEFECT
`(1−1/φ)/2 × |v|` criterion with the corrected `(1−1/φ)/2 × s_j` form);
and the amended MID-RETURN register (the counter-visible fix identified
in the post-exp007b gap analysis, which closed the K−1 blind spot at
measured zero stationary cost but has never been pre-registered or sworn
in its own right).

## 4. Design rule for the Note 02 §3 table: the confidence sideband

**THE CONFIDENCE SIDEBAND.** A 2-bit per-block tag — OK / stranger-present
/ mid-return / reborn — derivable entirely from signals the block
normalizer already computes (the block's observed maximum, compared
against the controller's current ceiling and regime counter). No new
arithmetic beyond what scale-tracking already performs; no new memory
beyond two bits per block. Contact's §1e result is the empirical case for
this rule: at every depth and format tested, the sideband's stranger flag
alone identified 100% of corrupted frames (17/17, every run) with zero
false positives and zero hallucinated regimes, at zero cost to the
controller's own accuracy. Architecture Note 02 §3 (the design-rules
table) already carries the three registers this tag packs (stranger log,
mid-return log, signed regime log — Note 02 §1 item 8) and §4 (the export
boundary) already carries three of the four rules this note's export
draft proposes (the recovery clock, the symmetric persistence gate, the
guarded ceiling). This rule is proposed as the fourth addition to both
tables — Note 02 §3's row and §4's list — now that real-workload contact
has measured its payoff; Note 02 itself predates that measurement (dated
2026-07-12, concurrent with exp101's pre-registration) and does not yet
contain it.

## 5. Provenance

The exp101–104 series was proposed, pre-registered, implemented, and
executed by Claude (Anthropic) in an external sandbox (sklearn 1.8.0,
numpy 2.4.4), working from the Note 02 §3 design-rule table alone — no
zakhor source code was transferred to that environment, only the design
rules (note-sufficiency: exp101 P5, PASS by the reimplementation's
correct omission of the falsified MID-RETURN mechanism, §3 above).

All twelve artifacts (four pre-registrations, four scripts, four results
files) were independently reproduced in this repository (sklearn 1.7.2,
numpy 2.2.6) by running each script as two separate process invocations.
Every double-run hash matched bit-for-bit — not merely within the ±0.5%
absolute tolerance specified, but exactly, across both the internal
double-run check each script performs and the original external-sandbox
hash:

| experiment | original hash | in-repo hash | match |
|---|---|---|---|
| exp101 | `72f15dc0cc00eae6` | `72f15dc0cc00eae6` | exact |
| exp102 | `dac01066e6db2acb` | `dac01066e6db2acb` | exact |
| exp103 | `2d47a95618b92c95` | `2d47a95618b92c95` | exact |
| exp104 | `200e9e3c78214f50` | `200e9e3c78214f50` | exact |

No threshold, number, or verdict was altered in porting. All decisions —
what to port, how to verify, what this note claims — are the steward's.
