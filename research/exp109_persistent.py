"""exp109 — the persistent-outlier warning test."""
import numpy as np, hashlib, json
import exp101_contact as base
import exp105_neighbors as x5

def forward(X, Ws, bs, mode, seed, corruption, trackers=None, stats=None):
    rng = np.random.RandomState(seed)
    # persistent hot channels: fixed per hidden layer, chosen once by seed
    hot = [rng.choice(64,4,replace=False), rng.choice(32,4,replace=False)]
    preds=[]
    for i in range(X.shape[0]):
        a=X[i]
        for li,(Wl,bl) in enumerate(zip(Ws,bs)):
            z=a@Wl+bl
            if li<len(Ws)-1: z=np.maximum(z,0)
            if corruption=='DENSE':
                mask=rng.rand(z.size)<1/64
                z=z.copy(); z[mask]*=x5.PHI**10
            elif corruption=='PERSISTENT' and li<2:
                z=z.copy(); z[hot[li]]*=2.0**7
            if mode=='LOCALMAX': z=x5.quantize_localmax(z)
            elif mode=='KEEPER': z=x5.quantize_keeper(z,trackers[li],stats)
            a=z
        preds.append(int(np.argmax(a)))
    return np.array(preds)

def run():
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    X,y=load_digits(return_X_y=True); X=X/16.0
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.5,random_state=base.SEED,stratify=y)
    clf=MLPClassifier(hidden_layer_sizes=(64,32),max_iter=800,random_state=base.SEED); clf.fit(Xtr,ytr)
    Ws=[w.copy() for w in clf.coefs_]; bs=[b.copy() for b in clf.intercepts_]
    Xs=np.concatenate([Xte,Xte]); ys=np.concatenate([yte,yte])
    out={}
    for stream in ['PERSISTENT','DENSE']:
        for mode in ['LOCALMAX','KEEPER']:
            trs=[x5.Tracker() for _ in range(3)]; st={'strangers':0,'true_corrupt':0,'disp':[]}
            pred=forward(Xs,Ws,bs,mode,1,stream,trs,st)
            e={'acc':float((pred==ys).mean())}
            if mode=='KEEPER':
                e['strangers']=st['strangers']; e['regime_events']=[t.regime_events for t in trs]
                e['G']=[round(t.G,2) for t in trs]
            out[f'{stream}/{mode}']=e
    return out
r1=run(); r2=run()
h1=hashlib.sha256(json.dumps(r1,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(r2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,h1==h2)
for s in ['PERSISTENT','DENSE']:
    lm=r1[f'{s}/LOCALMAX']['acc']; kp=r1[f'{s}/KEEPER']['acc']; k=r1[f'{s}/KEEPER']
    print(f"{s:10s} LM={lm:.4f} KEEP={kp:.4f} gap={kp-lm:+.4f} strangers={k['strangers']} reg={k['regime_events']} G={k['G']}")
json.dump(r1,open('exp109_results.json','w'),indent=1)