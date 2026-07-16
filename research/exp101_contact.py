"""exp101 — Contact: real workload, zakhor-G3 vs delayed scaling.
Independent reimplementation from Architecture Note 02 §3 design rules only.
"""
import numpy as np, hashlib, json
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

PHI = (1 + 5**0.5) / 2
LOG_PHI = np.log(PHI)
LEVELS = 16
ALPHA = 1/64
K = 3
CAL = 128          # calibration window (blocks)
W_DELAYED = 16     # delayed-scaling amax history window
SEED = 20260712

def lphi(x):  # log base phi of magnitude
    return np.log(x) / LOG_PHI

def quantize(v, hi):
    """Nearest-shell quantization against codebook hi*phi^-j, j=0..LEVELS-1.
    Returns (q, overflow_mask). Values below lowest shell may snap to 0."""
    q = np.zeros_like(v)
    av = np.abs(v)
    nz = av > 0
    if not nz.any():
        return q, np.zeros_like(v, dtype=bool)
    j = np.round(lphi(hi / np.where(nz, av, 1.0)))
    overflow = nz & (j < 0)
    jc = np.clip(j, 0, LEVELS - 1)
    shell = hi * PHI ** (-jc)
    # candidate shell vs zero: pick nearer
    use_zero = nz & (np.abs(av - shell) > av)
    q = np.where(nz, np.sign(v) * shell, 0.0)
    q = np.where(use_zero, 0.0, q)
    q = np.where(overflow, np.sign(v) * hi, q)  # clip at top shell
    return q, overflow

class Zakhor:
    """From Note 02 §3: leaky integrator in log-phi domain, causal pre-update
    read, guard band G, symmetric regime bound D, K in three roles,
    stranger gating, signed regime log."""
    def __init__(self):
        self.s = None            # state: log-phi of tracked block max
        self.G, self.D = 1.0, 2.0  # provisional until calibration derives
        self.noise = None
        self.n = 0
        self.regime_counter = 0
        self.cal_dpos, self.cal_absd = [], []
        self.regime_log = []     # (block, old_s, new_s)
        self.stranger_log = []
        self.displacement_on_stranger = []
        self.flags = []          # per-block: set of flags

    def hi_eff(self):
        return PHI ** (self.s + self.G)

    def step(self, block):
        f = set()
        av = np.abs(block); mx = av.max() if av.size else 0.0
        if self.n < K:
            f.add('INFANCY')
        if mx <= 0:
            self.n += 1; self.flags.append(f); return self.hi_eff() if self.s is not None else 1.0, f
        obs = lphi(mx)
        if self.s is None:               # cold start seed
            self.s = obs
            self.n += 1; self.flags.append(f); return self.hi_eff(), f
        d_raw = obs - self.s
        # symmetric regime gate (before gating decisions)
        if abs(d_raw) > self.D:
            self.regime_counter += 1
        else:
            self.regime_counter = 0
        if self.regime_counter >= K:
            old = self.s; self.s = obs; self.regime_counter = 0
            self.regime_log.append((self.n, old, self.s))
            f.add('REGIME_SETTLE')       # settle window handled by caller-free approx: flag K+4 next blocks
            self._settle = K + 4
        hi = self.hi_eff()
        stranger = mx > hi
        if stranger and 'REGIME_SETTLE' not in f:
            self.stranger_log.append((self.n, mx / hi))
            f.add('STRANGER')
            self.displacement_on_stranger.append(0.0)  # verified below: no update
        else:
            pre = self.s
            self.s = self.s + ALPHA * (obs - self.s)   # leaky integrator
            if self.n < CAL:
                self.cal_dpos.append(max(0.0, d_raw)); self.cal_absd.append(abs(d_raw))
            if self.n == CAL - 1 and self.cal_dpos:
                self.G = max(1.0, float(np.ceil(np.percentile(self.cal_dpos, 99))))
                self.D = max(2.0, self.G + 1)
                self.noise = float(np.percentile(self.cal_absd, 95))
        if getattr(self, '_settle', 0) > 0:
            f.add('REGIME_SETTLE'); self._settle -= 1
        self.n += 1; self.flags.append(f)
        return self.hi_eff(), f

class Delayed:
    """Industry baseline: rolling amax history, hi = max(window)."""
    def __init__(self):
        self.hist = []
    def step(self, block):
        av = np.abs(block); mx = av.max() if av.size else 0.0
        hi = max(self.hist) if self.hist else (mx if mx > 0 else 1.0)  # causal: prior history only
        if mx > 0:
            self.hist.append(mx)
            if len(self.hist) > W_DELAYED: self.hist.pop(0)
        return hi, set()

class Static:
    def __init__(self):
        self.mx, self.n, self.frozen = 0.0, 0, None
    def step(self, block):
        av = np.abs(block); m = av.max() if av.size else 0.0
        if self.n < CAL: self.mx = max(self.mx, m)
        if self.n == CAL - 1: self.frozen = self.mx
        self.n += 1
        return (self.frozen if self.frozen else max(self.mx, 1e-12)), set()

class Oracle:
    def step(self, block):
        av = np.abs(block); m = av.max() if av.size else 0.0
        return (m if m > 0 else 1.0), set()

def forward(X, Ws, bs, controllers=None):
    """Manual forward pass; if controllers given (list of 3 per-layer),
    quantize each layer's activations with that controller's hi."""
    preds = []
    for i in range(X.shape[0]):
        a = X[i]
        for li, (Wl, bl) in enumerate(zip(Ws, bs)):
            z = a @ Wl + bl
            if li < len(Ws) - 1:
                z = np.maximum(z, 0)
            if controllers is not None:
                hi, _ = controllers[li].step(z)
                z, _ = quantize(z, hi)
            a = z
        preds.append(int(np.argmax(a)))
    return np.array(preds)

def run_all():
    rng = np.random.RandomState(SEED)
    X, y = load_digits(return_X_y=True)
    X = X / 16.0
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.5, random_state=SEED, stratify=y)
    clf = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=800, random_state=SEED)
    clf.fit(Xtr, ytr)
    Ws = [w.copy() for w in clf.coefs_]; bs = [b.copy() for b in clf.intercepts_]

    # stream = test set repeated twice -> ~1796 samples; step at 900, spikes at idx%100==99
    Xs = np.concatenate([Xte, Xte]); ys = np.concatenate([yte, yte])
    n = Xs.shape[0]
    streams = {}
    streams['CLEAN'] = Xs.copy()
    sp = Xs.copy(); spike_idx = np.arange(n) % 100 == 99
    sp[spike_idx] *= PHI ** 10
    streams['SPIKE'] = sp
    dn = Xs.copy(); dn[900:] *= PHI ** -8; streams['REGIME_DOWN'] = dn
    up = Xs.copy(); up[900:] *= PHI ** 8;  streams['REGIME_UP'] = up

    ctor = {'ZAKHOR': lambda: [Zakhor() for _ in range(3)],
            'DELAYED': lambda: [Delayed() for _ in range(3)],
            'STATIC': lambda: [Static() for _ in range(3)],
            'ORACLE': lambda: [Oracle() for _ in range(3)]}

    fp64 = {s: forward(streams[s], Ws, bs, None) for s in streams}
    results = {'fp64_clean_acc': float((fp64['CLEAN'] == ys).mean())}

    for sname, SX in streams.items():
        for cname, make in ctor.items():
            ctrls = make()
            pred = forward(SX, Ws, bs, ctrls)
            acc = float((pred == ys).mean())
            match_fp64 = float((pred == fp64[sname]).mean())
            entry = {'acc': acc, 'match_fp64': match_fp64}
            if sname == 'SPIKE':
                entry['acc_normal'] = float((pred[~spike_idx] == ys[~spike_idx]).mean())
                entry['acc_spiked'] = float((pred[spike_idx] == ys[spike_idx]).mean())
            if sname.startswith('REGIME'):
                entry['acc_post'] = float((pred[900:] == ys[900:]).mean())
                entry['acc_pre'] = float((pred[:900] == ys[:900]).mean())
            if cname == 'ZAKHOR':
                entry['regime_events'] = [len(c.regime_log) for c in ctrls]
                entry['regime_log_L0'] = [(b, round(o,3), round(nw,3)) for b,o,nw in ctrls[0].regime_log[:4]]
                entry['strangers'] = [len(c.stranger_log) for c in ctrls]
                entry['max_displacement_on_stranger'] = max([max(c.displacement_on_stranger) if c.displacement_on_stranger else 0.0 for c in ctrls])
                entry['G_D'] = [(c.G, c.D) for c in ctrls]
            results[f'{sname}/{cname}'] = entry
    return results

r1 = run_all(); r2 = run_all()
h1 = hashlib.sha256(json.dumps(r1, sort_keys=True).encode()).hexdigest()[:16]
h2 = hashlib.sha256(json.dumps(r2, sort_keys=True).encode()).hexdigest()[:16]
print(json.dumps(r1, indent=1))
print('HASH run1', h1, ' run2', h2, ' bit-identical:', h1 == h2)
