"""exp107 — The Rival, the Range, and the Residue."""
import numpy as np, hashlib, json
import exp101_contact as base
import exp105_neighbors as x5

def quantize_trimmed(z):
    out = np.empty_like(z)
    for i in range(0, z.size, x5.N):
        blk = z[i:i+x5.N]; av = np.abs(blk)
        if av.max() <= 0: out[i:i+x5.N] = 0.0; continue
        if av.size >= 2:
            second = np.partition(av, -2)[-2]
            ref = second if second > 0 else av.max()
        else:
            ref = av.max()
        out[i:i+x5.N] = x5.bfp_block(blk, x5.exp_from_max(ref))
    return out

def forward(X, Ws, bs, mode, seed, p, trackers=None, stats=None, corrupt_log=None):
    rng = np.random.RandomState(seed)
    preds = []
    for i in range(X.shape[0]):
        a = X[i]; had_c = False
        for li,(Wl,bl) in enumerate(zip(Ws,bs)):
            z = a @ Wl + bl
            if li < len(Ws)-1: z = np.maximum(z,0)
            if p > 0:
                mask = rng.rand(z.size) < p
                if mask.any(): had_c = True
                z = z.copy(); z[mask] *= x5.PHI**10
            if   mode=='LOCALMAX': z = x5.quantize_localmax(z)
            elif mode=='TRIMMED':  z = quantize_trimmed(z)
            elif mode=='KEEPER':   z = x5.quantize_keeper(z, trackers[li], stats)
            elif mode=='FP64':     pass
            a = z
        preds.append(int(np.argmax(a)))
        if corrupt_log is not None: corrupt_log.append(had_c)
    return np.array(preds)

def setup():
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    X,y = load_digits(return_X_y=True); X = X/16.0
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.5,random_state=base.SEED,stratify=y)
    clf = MLPClassifier(hidden_layer_sizes=(64,32),max_iter=800,random_state=base.SEED); clf.fit(Xtr,ytr)
    Ws=[w.copy() for w in clf.coefs_]; bs=[b.copy() for b in clf.intercepts_]
    Xs=np.concatenate([Xte,Xte]); ys=np.concatenate([yte,yte])
    return Xs,ys,Ws,bs

def run():
    Xs,ys,Ws,bs = setup()
    out={}
    # Streams at seed 1, four competitors
    for sname,p in [('CLEAN',0.0),('SPARSE',1/512),('DENSE',1/64)]:
        for cname in ['LOCALMAX','TRIMMED','KEEPER']:
            trs=[x5.Tracker() for _ in range(3)]; st={'strangers':0,'true_corrupt':0,'disp':[]}
            pred=forward(Xs,Ws,bs,cname,1,p,trs,st)
            e={'acc':float((pred==ys).mean())}
            if cname=='KEEPER':
                e['strangers']=st['strangers']; e['true_corrupt']=st['true_corrupt']
                e['regime_events']=[t.regime_events for t in trs]
            out[f'{sname}/{cname}']=e
    # Decomposition at seed 1, DENSE
    trs=[x5.Tracker() for _ in range(3)]; st={'strangers':0,'true_corrupt':0,'disp':[]}
    kp = forward(Xs,Ws,bs,'KEEPER',1,1/64,trs,st)
    fp = forward(Xs,Ws,bs,'FP64',1,1/64)
    kw = kp!=ys
    out['DENSE/decomp']={'keeper_wrong':float(kw.mean()),
        'fp64_on_corrupted_acc':float((fp==ys).mean()),
        'model_error_share':float((kw&(fp!=ys)).mean()),
        'corruption_attributable':float((kw&(fp==ys)).mean())}
    # Seed sweep on DENSE
    gaps=[]; rows=[]
    for s in [1,2,3,4,5]:
        lm=forward(Xs,Ws,bs,'LOCALMAX',s,1/64)
        tm=forward(Xs,Ws,bs,'TRIMMED',s,1/64)
        trs=[x5.Tracker() for _ in range(3)]; st={'strangers':0,'true_corrupt':0,'disp':[]}
        kp=forward(Xs,Ws,bs,'KEEPER',s,1/64,trs,st)
        row={'seed':s,'LOCALMAX':float((lm==ys).mean()),'TRIMMED':float((tm==ys).mean()),'KEEPER':float((kp==ys).mean())}
        row['gap']=row['KEEPER']-row['LOCALMAX']; gaps.append(row['gap']); rows.append(row)
    out['sweep']={'rows':rows,'gap_mean':float(np.mean(gaps)),'gap_min':float(np.min(gaps))}
    return out

r1=run(); r2=run()
h1=hashlib.sha256(json.dumps(r1,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(r2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,'identical:',h1==h2)
for s in ['CLEAN','SPARSE','DENSE']:
    print(f"{s:7s} LM={r1[f'{s}/LOCALMAX']['acc']:.4f} TRIM={r1[f'{s}/TRIMMED']['acc']:.4f} KEEP={r1[f'{s}/KEEPER']['acc']:.4f}  K-T={r1[f'{s}/KEEPER']['acc']-r1[f'{s}/TRIMMED']['acc']:+.4f}")
d=r1['DENSE/decomp']
print(f"decomp: keeper_wrong={d['keeper_wrong']:.4f} fp64_corrupted_acc={d['fp64_on_corrupted_acc']:.4f} model_share={d['model_error_share']:.4f} corruption_residue={d['corruption_attributable']:.4f}")
sw=r1['sweep']
print('sweep gaps:',[f"{r['gap']:+.3f}" for r in sw['rows']],f"mean={sw['gap_mean']:+.4f} min={sw['gap_min']:+.4f}")
json.dump(r1,open('exp107_results.json','w'),indent=1)