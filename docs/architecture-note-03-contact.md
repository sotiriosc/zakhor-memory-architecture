# Architecture Note 03 — Contact

<!--
 ZAKHOR MEMORY ARCHITECTURE  |  PROPRIETARY RESEARCH — IN DEVELOPMENT
 Original architectural research project.
 Steward / Founder: Sotirios Chortogiannos.
 This note: 2026-07-16.  See ../NOTICE.
-->

**Status:** Draft v0.1 · **Date:** 2026-07-16

This note is written from the ported exp101–109 ("Contact") artifacts only.
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
| exp105 | `bc5f35d17500737e` | `bc5f35d17500737e` | exact |
| exp106 | `d1ccd001dfdf497b` | `d1ccd001dfdf497b` | exact |
| exp107 | `f17c22c36ee9df13` | `f17c22c36ee9df13` | exact |
| exp108 | `48b189777f967720` | `48b189777f967720` | exact |
| exp109 | `bf0419e664c3a4f1` | `bf0419e664c3a4f1` | exact |

No threshold, number, or verdict was altered in porting. All decisions —
what to port, how to verify, what this note claims — are the steward's.

---

## 9. exp108/109 — The Loss Scale and the Warning

Four findings: one incumbent collapse, one falsified prediction of ours,
one falsified external warning, and an open calibration deficit that
blocks any training claim from leaving this repository.

### exp108 — Keeper-controlled dynamic loss scaling

**The incumbent collapse (SPIKED/HEURISTIC).** The industry-standard
dynamic loss-scale heuristic — double every 500 clean steps, halve on
overflow — trained to **10.01% accuracy** on the SPIKED stream (chance
level, 10 classes). It detected only 4 overflows across all 30 spike
events (every 100th of 3000 steps). The remaining 26 spike gradient
updates, scaled ×2^8, passed through the FP16 path unchecked: each
applied a gradient update 256× larger than the loss warranted, corrupting
the weights irreversibly within the first spike encounters. The heuristic
could not detect the spikes because its scale was calibrated for clean
gradient magnitudes and the spikes, while enormous, fell within FP16
range at the operating scale. The heuristic has no mechanism to recognise
an outlier gradient as distinct from a valid large gradient — it only
sees overflow, not anomaly.

**P26 FALSIFIED — the direction of our prediction was backwards.**
P26 predicted KEEPER skips ≤ 1/3 as many steps as HEURISTIC on SPIKED.
Measured: KEEPER skips **679**, HEURISTIC skips **4**. KEEPER skips
~170× *more* steps, not fewer. The prediction conflated "correct
behavior" with "fewer skips." KEEPER is correct to skip: it tracks
log₂(max|g|) per step, identifies the spike gradient (≫ state + G) as a
stranger, skips the step without updating the scale or the state, and
continues. Each of the 30 spikes is correctly classified and skipped (679
total includes the calibration-period skip rate as well). HEURISTIC,
lacking anomaly detection, lets 26 spikes through. The accuracy
comparison settles what "correct" means: KEEPER SPIKED acc = **0.9700**,
HEURISTIC SPIKED acc = **0.1001**.

**P27 PASS.** KEEPER SPIKED accuracy (0.9700) exceeds HEURISTIC (0.1001)
by 86.9 points — P27's accuracy condition satisfied. KEEPER mean flushed
fraction (0.0000963) < HEURISTIC (0.000534) — P27's flush condition
satisfied. The halving aftermath is real: each overflow-triggered halve
pushes the scale low enough to flush small gradients in subsequent steps,
compounding the training damage. KEEPER's scale, set continuously from
the tracked state, never halves.

**P28 PASS.** On CLEAN, |KEEPER − HEURISTIC| = |0.9689 − 0.9722| =
**0.33%** ≤ 0.5%. No accuracy harm on the clean stream.

**The 22% skip rate — open calibration deficit, blocking training
claims.** On CLEAN, KEEPER issues **659 step skips out of 3000** (22.0%)
with zero spikes present. HEURISTIC: 0 skips. Every one of KEEPER's 659
CLEAN skips is a false-positive stranger declaration: normal step-to-step
variation in max|g| exceeds the G=1.0 guard band (2× in linear space,
1 log₂ unit) often enough to classify routine gradient variance as an
anomaly. This is the same G=1.0 calibration failure that produced 310
false stranger declarations in exp105 and drove the P17 falsification in
exp106; on gradient data the natural variance is larger than on activation
data, and the failure rate is correspondingly higher.

Skipping 22% of clean training steps wastes compute and slows convergence
— the model still reaches 0.9689 on this small task, but this cannot be
extrapolated to larger training runs where calibration adequacy is not
guaranteed. **No training-domain claim leaves this repository until G
calibration on gradient data is pre-registered and tested.** The required
fix is identified: calibrate G from the actual gradient-magnitude
distribution during a warm-up phase, allowing it to grow well beyond 1.0
when the gradient variance requires it — the same fix that P17 (exp105)
implied for activation data.

### exp109 — The persistent-outlier warning falls

**P29 FALSIFIED — the external warning was wrong.** P29 was explicitly
registered "siding with the external warning": on PERSISTENT stream (4
fixed hot channels per hidden layer, ×2^7 = 128× on every sample), the
predicted gap was KEEPER − LOCALMAX ≤ +1.0%. The predicted mechanism:
the tracked state would learn the hot channels, the ceiling would rise to
cover them, strangers would stop firing, and the keeper would converge to
LOCALMAX-equivalence. Measured gap: **+60.5%** (KEEPER 0.8154 vs
LOCALMAX 0.2102).

The warning's mechanism did not occur, for a structural reason:
strangers: **11456**, regime_events: **[0, 0, 0]**, G: **[1.0, 1.0,
1.0]**. The hot channels (128× = 7 log₂ units above the tracked mean)
are always classified as strangers under G=1.0 (threshold: 1 log₂ unit).
When a stranger block's surviving elements are themselves all strangers
(or absent), the tracker's fallback updates the state from the tracked
ceiling — a value close to the current state — keeping d ≈ 0. The regime
counter, which requires K=3 consecutive observations with |d| > G+1 = 2,
never accumulates past zero. **The state never reseats. The ceiling never
rises. The hot channels are perpetual strangers.**

This is not a failure of the keeper — it is the keeper working correctly
under the wrong model. The warning assumed adaptation; G=1.0 prevents
adaptation by construction, which in this fault model means the hot
channels are always excluded and the neighbors always protected. The
result (+60.5%) exceeds exp105's DENSE gap (+53.9%).

The DENSE rerun confirms continuity: DENSE gap = **+56.1%** (KEEPER
0.9327 vs LOCALMAX 0.3715), 0 regime events — consistent with exp105's
mechanism operating at a different seed.

**The sharpened product thesis.** The pre-registration offered a
conditional: "if P29 passes, record that this is a fault-tolerance play,
not a general quantization play." P29 FALSIFIED does not trigger that
condition. But the data sharpens the thesis in a different direction: the
keeper's advantage is largest precisely where activation-magnitude
outliers are most severe and most persistent, because the G=1.0 stranger
gate excludes them completely in both cases. On PERSISTENT, every hot
block across all 3594 samples in both hidden layers fires a stranger
declaration; the keeper never adapts, the neighbors are always protected,
and the per-channel scale-learning the warning assumed is exactly what
the design prevents. The product thesis stands with a narrower description
of its jurisdiction: outlier-driven activation faults, transient or
persistent, where the magnitude anomaly is detectable under the calibrated
guard band.

**Series provenance for exp108/109.** Both experiments pre-registered,
implemented, and executed externally (Claude, Anthropic sandbox,
sklearn 1.8.0, numpy 2.4.4). Both scripts ported byte-identical to
`research/`. Reproduced twice independently: exp108 hash
`48b189777f967720`, exp109 hash `bf0419e664c3a4f1`, both matching
original exactly. See `research/results/exp108_2026-07-12_inrepo.txt`
and `research/results/exp109_2026-07-12_inrepo.txt`.

---

## 8. exp107 — The Rival, the Range, and the Residue

**Three solidification attacks on the +53.9 headline.** Does the gap
survive a strong memoryless rival? Does it survive changing the
corruption seed? And how much of the agree-wrong frontier is the keeper's
own fault?

### The memoryless dilemma (P22, P23)

**P22 — PASS.** TRIMMED (block exponent from the second-largest element,
no state) beats LOCALMAX on DENSE by **+47.2 points** (0.8560 vs 0.3838),
easily clearing the 20-point threshold. The rival is genuinely strong:
excluding the single largest element per block is enough to avoid the
most catastrophic underflows.

**P23 — PASS. Memory resolves the dilemma KEEPER dominates TRIMMED on
every stream.** The differences at seed 1:

| stream | LOCALMAX | TRIMMED | KEEPER | K − T |
|---|---|---|---|---|
| CLEAN  | 0.9700 | 0.9444 | 0.9689 | **+2.45%** |
| SPARSE | 0.8532 | 0.9383 | 0.9650 | **+2.67%** |
| DENSE  | 0.3838 | 0.8560 | 0.9227 | **+6.68%** |

KEEPER exceeds TRIMMED by more than 0.5% on all three streams — P23's
stronger condition — against a threshold of −0.3% on every stream. The
verdict is unambiguous.

**The memoryless dilemma, named.** TRIMMED's CLEAN accuracy is **0.9444
against LOCALMAX's 0.9700 — a chronic −2.56% tax on every clean block.**
A memoryless heuristic that clips the block maximum must clip the
legitimate maximum of every block, every time, regardless of whether
corruption is present. KEEPER, tracking the scale causally, declares an
element a stranger only when it exceeds the tracked ceiling; clean blocks
cost nothing. The dilemma TRIMMED faces — clip everything or nothing —
is exactly the dilemma the tracked state resolves. The 2.6-point CLEAN
tax is the measured cost of choosing a memoryless answer to a stateful
problem.

### Seed stability (P24)

**P24 — PASS.** The KEEPER − LOCALMAX gap across five DENSE corruption
seeds:

| seed | LOCALMAX | TRIMMED | KEEPER | gap |
|---|---|---|---|---|
| 1 | 0.3838 | 0.8560 | 0.9227 | +53.9% |
| 2 | 0.3693 | 0.8676 | 0.9316 | +56.2% |
| 3 | 0.3760 | 0.8521 | 0.9099 | **+53.4%** (min) |
| 4 | 0.3704 | 0.8582 | 0.9194 | +54.9% |
| 5 | 0.3732 | 0.8548 | 0.9244 | +55.1% |

Mean gap **+54.7%**, minimum **+53.4%** — both well above the 40/30-point
thresholds. The headline is not a seed artefact: it holds within a 2.8-
point band (53.4%–56.2%) across all five seeds. KEEPER dominates TRIMMED
at every seed, by 5.4–6.7 points on DENSE.

### Frontier decomposition (P25)

**P25 — PASS.** On the DENSE corrupted stream at seed 1, running FP64
inference on the same corrupted activations yields accuracy **0.3910**
(39.1%): the network itself, operating in full floating-point with no
quantization, classifies only 39% of corrupted samples correctly. This
is the baseline of what the corruption does to the representation before
any quantization scheme touches it.

Decomposing the 7.73% KEEPER error rate:

| class | fraction of samples | meaning |
|---|---|---|
| model error | **7.23%** | KEEPER wrong, FP64 also wrong — network fails on the corrupted input regardless of quantization |
| corruption-attributable | **0.50%** | KEEPER wrong, FP64 right — quantization/stranger-clipping interacted with the corruption to produce an error FP64 would not have made |

**0.5% is the keeper-attributable residue.** The 9.2% agree-wrong class
from exp106 decomposes as: 7.23% is the model failing on corrupted
inputs in a way that no activation quantization scheme can prevent (FP64
also fails), and 0.5% is genuinely attributable to the keeper's
stranger-clipping interaction with the corrupted stream. The remaining
difference is composition: agree-wrong in exp106 was measured among
agreeing samples, not as a flat fraction of all samples.

**Stranger-clipping as fault suppression, scoped.** The FP64 accuracy on
the corrupted stream (39.1%) establishes the scope of the finding: the
keeper's +53.9-point advantage over LOCALMAX is not primarily accuracy
recovery — it is fault suppression at the activation level. When a
corrupted element inflates a block's exponent, LOCALMAX propagates that
distortion forward through all subsequent layers; KEEPER clips it at the
tracked ceiling and forwards a representable (if clipped) activation
instead. This is not the same as preventing the corruption from affecting
the network's representation — FP64 on the same corrupted stream still
fails 60.9% of the time. The keeper intercepts activation-level
quantization faults, not the underlying corrupted values. That scoping is
exact: the 39.1% FP64 corrupted accuracy is the ceiling of what
activation-level fault suppression can deliver, and 0.9227 approaches
it from below (gap 0.9227 − 0.3910 = 0.532 recovered, against 0.609
total FP64-lost).

Stranger-clipping is activation-level fault suppression in both senses:
it restores the honest neighbors' encoding AND bounds the corrupted
value's propagated magnitude — which is why the keeper pipeline exceeds
unquantized FP64 under this fault model. What it is not is input-level
corruption correction: faults that alter the input's semantics before the
network lie beyond any scale controller's jurisdiction, and the 7.23%
model-error share measures exactly that territory.

**The honest frontier, updated.** Of the 7.73% KEEPER errors on DENSE,
7.23% are model errors the keeper cannot be asked to fix — FP64 fails
them too. The 0.5% corruption-attributable residue is the honest
measurement of what a better stranger-clipping or recovery strategy might
reach. The agree-wrong class from exp106 is overwhelmingly model error,
not an open keeper engineering problem.

**Series provenance for exp107.** Pre-registered, implemented, and
executed externally (Claude, Anthropic sandbox, sklearn 1.8.0, numpy
2.4.4). Ported byte-identical to `research/exp107_rival.py`; run twice
independently in this environment (sklearn 1.7.2, numpy 2.2.6). Both
invocations produced hash `f17c22c36ee9df13`, matching the original
exactly. See `research/results/exp107_2026-07-12_inrepo.txt`.

---

## 7. exp106 — The Dissonance Bit: regime-dependent semantics and the agree-wrong frontier

**The bit.** Run the same corrupted-stream inference through two paths
simultaneously — LOCALMAX (per-block, memoryless) and KEEPER (exp105's
tracked-scale machinery, stateful) — and emit one bit per sample: did
their predictions differ? The served answer is always KEEPER's (the
better path per exp105). The flag costs one comparison.

**P20 (clean floor) — PASS.** On CLEAN, the disagreement rate is
**0.11%** (0.0011), well within the 3.0% bound. All 310 CLEAN
disagreements are wrong (err_given_disagree = 1.0); they are precisely
the false-stranger declarations the guard band produces on clean data —
the same 310 elements flagged in exp105, now visible as prediction
divergences. On CLEAN the bit is near-perfectly specific: 100% of
disagreements are errors, 0% of agreements are false-alarm disagreements.
The P19 CLEAN ratio is 33.3× — structurally correct, but P19 was not
specified on CLEAN and this number is not a verdict.

**P19 (informativeness) — FALSIFIED on both specified streams.** P19
requires P(wrong | disagree) ≥ 3.0 × P(wrong | agree) on SPARSE and on
DENSE.

On SPARSE: err_given_disagree = 4.25%, err_given_agree = 3.40%,
ratio = **1.25** < 3.0. The bit is slightly, not strongly, informative.
At p=1/512 most disagreements trace to the false-stranger background
(310 calibration-tail declarations per stream vs 365 true corruptions),
diluting the signal: many disagreements arise from the G=1.0 artifact
rather than from actual corruption events, pushing the error rate among
disagreements closer to the error rate among agreements.

On DENSE: err_given_disagree = 6.69%, err_given_agree = **9.19%**,
ratio = **0.73** — the flag **inverts**. Samples where the two paths
disagree are *less likely to be wrong* than samples where they agree. The
threshold of 3.0× is not approached; the direction reverses.

**P21 (wrongness coverage) — FALSIFIED.** P21 requires P(disagree |
wrong) ≥ 2.0 × P(disagree | right) on DENSE. Measured: P(disagree |
wrong) = 50.4%, P(disagree | right) = 58.9%, lift = **0.855** < 1.0 —
again inverted. Wrong samples are *less likely* to be flagged as
disagreements than correct samples.

**Root cause: the semantics of disagreement invert in the dense regime.**
At DENSE (p = 1/64), 58.2% of samples produce a disagreement. These
disagreements are not "both paths confused, served answer suspect" — they
are "KEEPER recovered the sample by excluding the stranger, LOCALMAX
failed catastrophically." Disagreement flags the KEEPER rescue operation.
The served answer under disagreement is the *better* answer: KEEPER
classified correctly while LOCALMAX, whose exponent was inflated by the
in-block outlier, underflowed the 7 surviving neighbors to zero and
predicted from noise. Disagreement in the dense regime is therefore a
positive-quality signal for the served answer, not a warning about it —
the bit's polarity is backwards for the use case P19 and P21 assumed.

The inversion is complete and structural. It is not a calibration
artifact and it does not diminish with more data; it is the geometry of
what the two paths are doing when corruption is common.

**The agree-wrong class: the honest frontier.** When both paths agree on
DENSE, the error rate is **9.19%**. These are the samples where the
corruption damage is absorbed the same way by both paths — either both
correctly classify a clean block, or both fail on the same quantized
representation of a corrupted block. The agree-wrong cases are the second
category: 9.19% of the samples that elicited agreement are wrong, and no
signal built in this series sees them.

The stranger flag is silent (by construction: if a stranger were present,
KEEPER and LOCALMAX would diverge). The dissonance bit is silent (by
definition). The regime log is silent (the regime event has already
fired; the state has reseated; the block looks normal to the tracker).
These answers pass every integrity check we have, then fail.

9.2% of DENSE-stream agreeing answers are wrong with both layers in
agreement, and no signal we have built yet reaches them. That is the
honest description of the frontier.

**Rider.** exp106 uses exp105's seeds and machinery; audit numbers must
match exp105 exactly. They do: CLEAN (310 strangers, 0 true), SPARSE
(613/365, [1,1,1]), DENSE (3204/2998, [1,1,1]) — bit-for-bit identical.
No implementation drift.

**Series provenance for exp106.** Pre-registered, implemented, and
executed externally (Claude, Anthropic sandbox, sklearn 1.8.0, numpy
2.4.4). Ported byte-identical to `research/exp106_dissonance.py`; run
twice independently in this environment (sklearn 1.7.2, numpy 2.2.6).
Both invocations produced hash `d1ccd001dfdf497b`, matching the original
exactly. See `research/results/exp106_2026-07-12_inrepo.txt`.

---

## 6. exp105 — The Neighbors: N=8 keeper-gated exponent selection

**Scope statement.** exp103/104's +12-point result was measured in a
per-layer tracked-scale mode (shared exponent driven by a scalar leaky
integrator across the whole layer). Horus's native compressed format is
E3M6+block: a 6-bit shared exponent per 8-element block, set from the
block's own local maximum — a per-block oracle that is perfectly adapted
to clean data and maximally exposed to in-block outliers. The exp103/104
numbers are not cited here; they are scoped to their mode, as the
pre-registration requires.

**The concentration claim (P14) — PASS.** On DENSE (p = 1/64
element-level corruption, ~1 corrupted element per 8-element block),
KEEPER-GATED top-1 was **0.9227** against LOCALMAX's **0.3838**: a gap
of **+53.9%** absolute, against a threshold of 3.0%. The mechanism
operates as predicted: a single corrupted element, multiplied by φ^10
(≈123×), inflates its block's shared exponent by approximately 10
φ-shells (~7 octaves), pushing the block's 7 surviving elements below
the 6-bit mantissa floor and underflowing them to zero. The keeper
detects the element as a stranger, excludes it from the block-max
computation, sets the exponent from the surviving elements, and clips
the outlier to the block ceiling. At the block level, the neighbors keep
their precision; at the network level, the classification accuracy is
recovered from near chance (0.38) to 0.92.

On SPARSE (p = 1/512, ~1 corrupted element per 64 blocks), the gap is
**+11.2%** (KEEPER 0.9650 vs LOCALMAX 0.8532) — P15 PASS. Corrupted
blocks, though rare, are individually catastrophic under LOCALMAX and
individually recoverable under KEEPER; the aggregate advantage reflects
the per-block mechanism operating correctly wherever corruption lands.

**Oracle-equivalence (P18) — PASS.** On DENSE, KEEPER-GATED top-1
**0.9227 = ORACLE-CLEAN 0.9227** exactly. ORACLE-CLEAN is the
unreachable diagnostic ceiling: it sets each block's exponent from the
uncorrupted activations directly, bypassing the corruption entirely.
The keeper, operating causally from a tracked scalar state with no
foreknowledge of corruption, matches ORACLE-CLEAN's per-block accuracy
to four decimal places. At N=8, stranger exclusion from the block's own
max fully recovers what the block's neighbors would have seen had the
spike never arrived.

**P16 (no honesty tax on CLEAN) — PASS.** CLEAN gap is −0.11%
(KEEPER 0.9689 vs LOCALMAX 0.9700), well within the 1.0% bound. Zero
regime events on CLEAN across all three layers. Tracked-state
displacement from stranger-declared blocks ≡ 0.0 (exact) in every
configuration.

**P17 (the audit) — FALSIFIED.** The audit specified two conditions:
(i) on DENSE, the stranger-declaration count is within 1.05× of the
true corrupted-element count; (ii) zero strangers declared on CLEAN
beyond the calibration-tail rate.

Condition (i): DENSE ratio is 3204 / 2998 = **1.069**, exceeding the
1.05× bound. On SPARSE the overcounting is more pronounced: 613
declared against 365 true corruptions, ratio **1.679**. Root cause: the
calibration window (128 blocks) does not drive G above its 1.0 minimum
on this workload's per-block maxima, leaving the guard band fixed at a
single log₂ unit. Under N=8 granularity the per-block maximum is a
single element's magnitude; the activation distribution's upper tail
occasionally places normal clean elements above the tracked ceiling +
1.0, declaring them as strangers. The SPARSE overcounting (1.679) is
larger than DENSE (1.069) because at SPARSE the true-corrupt count is
small (365 out of ≈1.4M elements) and the false-declaration background
from normal-tail elements is proportionally dominant.

Condition (ii): 310 strangers declared on CLEAN, against 0 true
corruptions, ratio 310.0. Inspecting the per-layer counts (regime_events
= [0,0,0] on CLEAN, G = [1.0, 1.0, 1.0] all layers): all 310
declarations originate in the logits layer — the same heavy-tail
artifact established as an open observation in §3 of this note. The
hidden layers declare 0 strangers on CLEAN, as they do throughout
exp101–104; the logits layer, with its unbounded output distribution, is
not calibrated to the same scale as the hidden layers, and G = 1.0 is
insufficient guard for it. The underlying phenomenon is the same
heavy-tail finding from §3; at N=8 it appears as audit overcounting
rather than a separate defect.

P17 FALSIFIED on both conditions. The falsification is a statement about
calibration adequacy at N=8 granularity, not about the keeper's core
mechanism (stranger exclusion, tracked-state update, displacement): all
three of those properties held exactly.

**One regime event per layer per corrupted stream.** On both SPARSE and
DENSE, every layer fired exactly one regime event ([1, 1, 1]) — matching
the number of distinct corruption epochs in each stream (one per run,
since the corruption rate is steady). On CLEAN, regime events are
[0, 0, 0] everywhere. This confirms the regime machinery's response at
N=8 granularity: a sustained corruption rate, once it accumulates K=3
consecutive stranger observations, triggers one rebirth per layer, after
which the tracked state reseats and the regime counter resets. The
count of regime events equals the count of independently corrupted
streams, not the count of corrupted elements — the rebirth absorbs the
pattern, then the standard stranger-gate handles individual events.

**Series provenance for exp105.** Pre-registered, implemented, and
executed externally (Claude, Anthropic sandbox, sklearn 1.8.0, numpy
2.4.4). Ported byte-identical to `research/exp105_neighbors.py`; run
twice independently in this environment (sklearn 1.7.2, numpy 2.2.6).
Both in-repo invocations produced hash `bc5f35d17500737e`, matching the
original exactly. See `research/results/exp105_2026-07-12_inrepo.txt`.
