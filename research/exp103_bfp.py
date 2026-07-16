"""exp103 — Horus Water: binary BFP shared-exponent, zakhor vs delayed."""
import numpy as np, hashlib, json
import exp101_contact as base

MBITS = 6  # set per run

def bfp_quantize(v, hi, m):
    E = np.ceil(np.log2(max(hi, 1e-300)))
    lsb = 2.0 ** (E - m)
    q = np.round(v / lsb)
    qmax = 2 ** m - 1
    q = np.clip(q, -qmax, qmax)
    return q * lsb

def forward_bfp(X, Ws, bs, controllers, m):
    preds = []
    for i in range(X.shape[0]):
        a = X[i]
        for li, (Wl, bl) in enumerate(zip(Ws, bs)):
            z = a @ Wl + bl
            if li < len(Ws) - 1:
                z = np.maximum(z, 0)
            hi, _ = controllers[li].step(z)
            z = bfp_quantize(z, hi, m)
            a = z
        preds.append(int(np.argmax(a)))
    return np.array(preds)

def run(m):
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    X, y = load_digits(return_X_y=True); X = X/16.0
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.5, random_state=base.SEED, stratify=y)
    clf = MLPClassifier(hidden_layer_sizes=(64,32), max_iter=800, random_state=base.SEED)
    clf.fit(Xtr, ytr)
    Ws=[w.copy() for w in clf.coefs_]; bs=[b.copy() for b in clf.intercepts_]
    Xs=np.concatenate([Xte,Xte]); ys=np.concatenate([yte,yte]); n=Xs.shape[0]
    spike_idx=np.arange(n)%100==99
    sp=Xs.copy(); sp[spike_idx]*=base.PHI**10
    out={}
    for sname,SX in [('CLEAN',Xs),('SPIKE',sp)]:
        for cname,make in [('ZAKHOR',lambda:[base.Zakhor() for _ in range(3)]),
                           ('DELAYED',lambda:[base.Delayed() for _ in range(3)]),
                           ('ORACLE',lambda:[base.Oracle() for _ in range(3)])]:
            ctrls=make()
            pred=forward_bfp(SX,Ws,bs,ctrls,m)
            e={'acc':float((pred==ys).mean())}
            if sname=='SPIKE': e['acc_normal']=float((pred[~spike_idx]==ys[~spike_idx]).mean())
            if cname=='ZAKHOR':
                e['strangers']=[len(c.stranger_log) for c in ctrls]
                e['max_disp']=max([max(c.displacement_on_stranger) if c.displacement_on_stranger else 0.0 for c in ctrls])
                e['regime_events']=[len(c.regime_log) for c in ctrls]
            out[f'{sname}/{cname}']=e
    return out

res={str(m):run(m) for m in [3,6]}
res2={str(m):run(m) for m in [3,6]}
h1=hashlib.sha256(json.dumps(res,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(res2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,'identical:',h1==h2)
print(f"{'m':>2} {'clean Z':>8} {'clean D':>8} {'clean O':>8} | {'spikeN Z':>9} {'spikeN D':>9} {'gap':>8} | strangers disp regC")
for m in ['3','6']:
    r=res[m]
    gz=r['SPIKE/ZAKHOR']['acc_normal']; gd=r['SPIKE/DELAYED']['acc_normal']
    print(f"{m:>2} {r['CLEAN/ZAKHOR']['acc']:8.4f} {r['CLEAN/DELAYED']['acc']:8.4f} {r['CLEAN/ORACLE']['acc']:8.4f} | {gz:9.4f} {gd:9.4f} {gz-gd:+8.4f} | {r['SPIKE/ZAKHOR']['strangers']} {r['SPIKE/ZAKHOR']['max_disp']} {r['CLEAN/ZAKHOR']['regime_events']}")
json.dump(res,open('exp103_results.json','w'),indent=1)
