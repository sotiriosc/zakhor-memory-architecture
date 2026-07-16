"""exp102 — Shallow Water: LEVELS sweep on CLEAN + SPIKE."""
import numpy as np, hashlib, json
import exp101_contact as base

def run_depth(levels):
    base.LEVELS = levels
    rng = np.random.RandomState(base.SEED)
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
    sp=Xs.copy(); sp[spike_idx]*= base.PHI**10
    out={}
    for sname,SX in [('CLEAN',Xs),('SPIKE',sp)]:
        for cname,make in [('ZAKHOR',lambda:[base.Zakhor() for _ in range(3)]),
                           ('DELAYED',lambda:[base.Delayed() for _ in range(3)]),
                           ('ORACLE',lambda:[base.Oracle() for _ in range(3)])]:
            ctrls=make()
            pred=base.forward(SX,Ws,bs,ctrls)
            e={'acc':float((pred==ys).mean())}
            if sname=='SPIKE':
                e['acc_normal']=float((pred[~spike_idx]==ys[~spike_idx]).mean())
            if cname=='ZAKHOR':
                e['regime_events']=[len(c.regime_log) for c in ctrls]
                e['strangers']=[len(c.stranger_log) for c in ctrls]
                e['max_disp']=max([max(c.displacement_on_stranger) if c.displacement_on_stranger else 0.0 for c in ctrls])
            out[f'{sname}/{cname}']=e
    return out

res={str(L):run_depth(L) for L in [4,6,8,16]}
res2={str(L):run_depth(L) for L in [4,6,8,16]}
h1=hashlib.sha256(json.dumps(res,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(res2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,'identical:',h1==h2)
print(f"{'L':>3} {'clean Z':>8} {'clean D':>8} | {'spikeN Z':>9} {'spikeN D':>9} {'gap':>7} | strangers  disp  regC")
for L in ['4','6','8','16']:
    r=res[L]
    gz=r['SPIKE/ZAKHOR']['acc_normal']; gd=r['SPIKE/DELAYED']['acc_normal']
    print(f"{L:>3} {r['CLEAN/ZAKHOR']['acc']:8.4f} {r['CLEAN/DELAYED']['acc']:8.4f} | {gz:9.4f} {gd:9.4f} {gz-gd:+7.4f} | {r['SPIKE/ZAKHOR']['strangers']} {r['SPIKE/ZAKHOR']['max_disp']} {r['CLEAN/ZAKHOR']['regime_events']}")
json.dump(res,open('exp102_results.json','w'),indent=1)
