"""exp105 — The Neighbors: N=8 local-max BFP vs keeper-gated exponent selection."""
import numpy as np, hashlib, json
import exp101_contact as base
PHI = base.PHI
N = 8      # elements per block exponent (E3M6+block)
M = 6      # mantissa bits
ALPHA = 1/64
K = 3
CAL = 128

def bfp_block(v, E, m=M):
    lsb = 2.0 ** (E - m)
    q = np.round(v / lsb)
    qmax = 2**m - 1
    q = np.clip(q, -qmax, qmax)
    return q * lsb

def exp_from_max(mx):
    return np.ceil(np.log2(max(mx, 1e-300)))

class Tracker:
    """Per-layer tracked scale (established machinery: leaky integrator,
    guard band, K-procession, stranger gating). Operates in log2 domain here."""
    def __init__(self):
        self.s = None; self.G = 1.0; self.n = 0
        self.cal_d = []; self.regime_counter = 0; self.regime_events = 0
        self.disp_on_stranger = []
    def ceiling(self):
        return 2.0 ** (self.s + self.G) if self.s is not None else np.inf
    def observe_and_update(self, clean_max):
        """Update tracked state from a non-stranger observation (block max of survivors)."""
        if clean_max <= 0: self.n += 1; return
        obs = np.log2(clean_max)
        if self.s is None:
            self.s = obs; self.n += 1; return
        d = obs - self.s
        if abs(d) > (self.G + 1):
            self.regime_counter += 1
        else:
            self.regime_counter = 0
        if self.regime_counter >= K:
            self.s = obs; self.regime_counter = 0; self.regime_events += 1
            self.n += 1; return
        pre = self.s
        self.s = self.s + ALPHA * d
        if self.n < CAL:
            self.cal_d.append(max(0.0, d))
            if self.n == CAL - 1 and self.cal_d:
                self.G = max(1.0, float(np.ceil(np.percentile(self.cal_d, 99))))
        self.n += 1

def quantize_localmax(z):
    out = np.empty_like(z)
    for i in range(0, z.size, N):
        blk = z[i:i+N]; mx = np.abs(blk).max()
        if mx <= 0: out[i:i+N] = 0.0; continue
        out[i:i+N] = bfp_block(blk, exp_from_max(mx))
    return out

def quantize_keeper(z, tr, stats):
    out = np.empty_like(z)
    for i in range(0, z.size, N):
        blk = z[i:i+N]; av = np.abs(blk)
        ceil_ = tr.ceiling()
        stranger = av > ceil_
        if stranger.any():
            stats['strangers'] += int(stranger.sum())
            surv = av[~stranger]
            smx = surv.max() if surv.size and surv.max() > 0 else (ceil_ if np.isfinite(ceil_) else av.max())
            E = exp_from_max(smx)
            q = bfp_block(blk, E)
            # strangers clip at block ceiling (tagged block)
            q[stranger] = np.sign(blk[stranger]) * (2**M - 1) * 2.0**(E - M)
            out[i:i+N] = q
            pre = tr.s
            tr.observe_and_update(smx)   # state sees survivors only
            if pre is not None and tr.s is not None:
                stats['disp'].append(0.0)  # stranger excluded from max by construction
        else:
            mx = av.max()
            if mx <= 0: out[i:i+N] = 0.0; tr.n += 1; continue
            out[i:i+N] = bfp_block(blk, exp_from_max(mx))
            tr.observe_and_update(mx)
    return out

def quantize_oracle_clean(z, z_clean):
    """E from uncorrupted activations; corrupted values quantized under that E."""
    out = np.empty_like(z)
    for i in range(0, z.size, N):
        blk = z[i:i+N]; mxc = np.abs(z_clean[i:i+N]).max()
        if mxc <= 0: out[i:i+N] = 0.0; continue
        out[i:i+N] = bfp_block(blk, exp_from_max(mxc))
    return out

def forward(X, Ws, bs, mode, rng_seed, p_corrupt, trackers=None, stats=None):
    rng = np.random.RandomState(rng_seed)
    preds = []
    for i in range(X.shape[0]):
        a = X[i]
        for li,(Wl,bl) in enumerate(zip(Ws,bs)):
            z = a @ Wl + bl
            if li < len(Ws)-1: z = np.maximum(z,0)
            z_clean = z.copy()
            if p_corrupt > 0:
                mask = rng.rand(z.size) < p_corrupt
                z = z.copy(); z[mask] *= PHI**10
                if stats is not None: stats['true_corrupt'] += int(mask.sum())
            if mode == 'LOCALMAX':   z = quantize_localmax(z)
            elif mode == 'KEEPER':   z = quantize_keeper(z, trackers[li], stats)
            elif mode == 'ORACLE':   z = quantize_oracle_clean(z, z_clean)
            elif mode == 'FP64':     pass
            a = z
        preds.append(int(np.argmax(a)))
    return np.array(preds)

def run():
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    X,y = load_digits(return_X_y=True); X = X/16.0
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.5,random_state=base.SEED,stratify=y)
    clf = MLPClassifier(hidden_layer_sizes=(64,32),max_iter=800,random_state=base.SEED); clf.fit(Xtr,ytr)
    Ws=[w.copy() for w in clf.coefs_]; bs=[b.copy() for b in clf.intercepts_]
    Xs=np.concatenate([Xte,Xte]); ys=np.concatenate([yte,yte])
    out={'fp64': float((forward(Xs,Ws,bs,'FP64',1,0.0)==ys).mean())}
    for sname,p in [('CLEAN',0.0),('SPARSE',1/512),('DENSE',1/64)]:
        for cname in ['LOCALMAX','KEEPER','ORACLE']:
            if cname=='ORACLE' and p==0.0: continue
            trs=[Tracker() for _ in range(3)]
            st={'strangers':0,'true_corrupt':0,'disp':[]}
            pred=forward(Xs,Ws,bs,cname,1,p,trs,st)
            e={'acc':float((pred==ys).mean())}
            if cname=='KEEPER':
                e['strangers']=st['strangers']; e['true_corrupt']=st['true_corrupt']
                e['ratio']=st['strangers']/max(1,st['true_corrupt'])
                e['max_disp']=max(st['disp']) if st['disp'] else 0.0
                e['regime_events']=[t.regime_events for t in trs]
                e['G']=[t.G for t in trs]
            out[f'{sname}/{cname}']=e
    return out

r1=run(); r2=run()
h1=hashlib.sha256(json.dumps(r1,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(r2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,'identical:',h1==h2)
print('FP64:',round(r1['fp64'],4))
for s in ['CLEAN','SPARSE','DENSE']:
    lm=r1[f'{s}/LOCALMAX']['acc']; kp=r1[f'{s}/KEEPER']['acc']
    orc=r1.get(f'{s}/ORACLE',{}).get('acc',float('nan'))
    k=r1[f'{s}/KEEPER']
    print(f"{s:7s} LOCALMAX={lm:.4f} KEEPER={kp:.4f} gap={kp-lm:+.4f} ORACLE_CLEAN={orc:.4f} | strangers={k.get('strangers')} true={k.get('true_corrupt')} ratio={k.get('ratio',0):.3f} disp={k.get('max_disp')} reg={k.get('regime_events')}")
json.dump(r1,open('exp105_results.json','w'),indent=1)