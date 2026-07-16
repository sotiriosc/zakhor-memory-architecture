"""exp104 — Full Water: weights + activations BFP, m=6."""
import numpy as np, hashlib, json
import exp101_contact as base
from exp103_bfp import bfp_quantize

M = 6
BLK = 64

def quantize_weights(Ws):
    out = []
    for W in Ws:
        Q = W.copy().ravel()
        for i in range(0, Q.size, BLK):
            blk = Q[i:i+BLK]
            mx = np.abs(blk).max()
            if mx > 0:
                Q[i:i+BLK] = bfp_quantize(blk, mx, M)
        out.append(Q.reshape(W.shape))
    return out

def forward_fq(X, Ws, bs, controllers):
    preds = []
    for i in range(X.shape[0]):
        a = X[i]
        for li, (Wl, bl) in enumerate(zip(Ws, bs)):
            z = a @ Wl + bl
            if li < len(Ws) - 1:
                z = np.maximum(z, 0)
            hi, _ = controllers[li].step(z)
            z = bfp_quantize(z, hi, M)
            a = z
        preds.append(int(np.argmax(a)))
    return np.array(preds)

def run():
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    X, y = load_digits(return_X_y=True); X = X/16.0
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.5, random_state=base.SEED, stratify=y)
    clf = MLPClassifier(hidden_layer_sizes=(64,32), max_iter=800, random_state=base.SEED)
    clf.fit(Xtr, ytr)
    Ws=[w.copy() for w in clf.coefs_]; bs=[b.copy() for b in clf.intercepts_]
    Wq = quantize_weights(Ws)
    # weight quantization cost alone (FP64 activations)
    Xs=np.concatenate([Xte,Xte]); ys=np.concatenate([yte,yte]); n=Xs.shape[0]
    wonly = base.forward(Xs, Wq, bs, None)
    spike_idx=np.arange(n)%100==99
    sp=Xs.copy(); sp[spike_idx]*=base.PHI**10
    out={'fp64_clean': float((base.forward(Xs,Ws,bs,None)==ys).mean()),
         'weights_only_quant_clean': float((wonly==ys).mean())}
    for sname,SX in [('CLEAN',Xs),('SPIKE',sp)]:
        for cname,make in [('ZAKHOR',lambda:[base.Zakhor() for _ in range(3)]),
                           ('DELAYED',lambda:[base.Delayed() for _ in range(3)]),
                           ('ORACLE',lambda:[base.Oracle() for _ in range(3)])]:
            ctrls=make()
            pred=forward_fq(SX,Wq,bs,ctrls)
            e={'acc':float((pred==ys).mean())}
            if sname=='SPIKE': e['acc_normal']=float((pred[~spike_idx]==ys[~spike_idx]).mean())
            if cname=='ZAKHOR':
                e['strangers']=[len(c.stranger_log) for c in ctrls]
                e['max_disp']=max([max(c.displacement_on_stranger) if c.displacement_on_stranger else 0.0 for c in ctrls])
                e['regime_events']=[len(c.regime_log) for c in ctrls]
            out[f'{sname}/{cname}']=e
    return out

r1=run(); r2=run()
h1=hashlib.sha256(json.dumps(r1,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(r2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,'identical:',h1==h2)
print('FP64 clean:', r1['fp64_clean'], ' weights-only-quant clean:', r1['weights_only_quant_clean'])
for s in ['CLEAN','SPIKE']:
    for c in ['ZAKHOR','DELAYED','ORACLE']:
        e=r1[f'{s}/{c}']
        extra = f" normal={e.get('acc_normal',float('nan')):.4f}" if s=='SPIKE' else ''
        aud = f" strangers={e['strangers']} disp={e['max_disp']} reg={e['regime_events']}" if c=='ZAKHOR' else ''
        print(f"{s:6s} {c:8s} acc={e['acc']:.4f}{extra}{aud}")
json.dump(r1,open('exp104_results.json','w'),indent=1)
