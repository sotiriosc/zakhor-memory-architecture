"""exp108 — keeper-controlled dynamic loss scaling vs industry heuristic."""
import numpy as np, hashlib, json
SEED=20260712
FP16_MAX=65504.0; FP16_TINY=2.0**-24

def fp16_path(g, S):
    x = g*S
    if not np.all(np.isfinite(x)) or np.abs(x).max() > FP16_MAX:
        return None, 0.0  # overflow
    x = x.astype(np.float16).astype(np.float64)
    flushed = float((np.abs(x) < FP16_TINY).mean() - (g==0).mean())
    x[np.abs(x) < FP16_TINY] = 0.0
    return x/S, max(0.0, flushed)

def train(mode, spiked, seed=SEED, steps=3000):
    rng=np.random.RandomState(seed)
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    X,y=load_digits(return_X_y=True); X=X/16.0
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.5,random_state=SEED,stratify=y)
    n_in,h1,h2,n_out=64,64,32,10
    W1=rng.randn(n_in,h1)*np.sqrt(2/n_in); b1=np.zeros(h1)
    W2=rng.randn(h1,h2)*np.sqrt(2/h1);    b2=np.zeros(h2)
    W3=rng.randn(h2,n_out)*np.sqrt(2/h2); b3=np.zeros(n_out)
    lr=0.05; S=2.0**10
    # keeper state
    ks=None; G=1.0; cal=[]; K=3; cnt=0; skips=0; flush_acc=[]; scale_log=[]
    grow_timer=0
    for t in range(steps):
        idx=rng.choice(Xtr.shape[0],32,replace=False)
        xb,yb=Xtr[idx],ytr[idx]
        z1=xb@W1+b1; a1=np.maximum(z1,0)
        z2=a1@W2+b2; a2=np.maximum(z2,0)
        z3=a2@W3+b3
        z3-=z3.max(1,keepdims=True); e=np.exp(z3); p=e/e.sum(1,keepdims=True)
        d3=p.copy(); d3[np.arange(32),yb]-=1; d3/=32
        gW3=a2.T@d3; gb3=d3.sum(0)
        d2=(d3@W3.T)*(z2>0); gW2=a1.T@d2; gb2=d2.sum(0)
        d1=(d2@W2.T)*(z1>0); gW1=xb.T@d1; gb1=d1.sum(0)
        grads=[gW1,gb1,gW2,gb2,gW3,gb3]
        if spiked and t%100==99:
            grads=[g*2.0**8 for g in grads]
        gmax=max(np.abs(g).max() for g in grads)
        # controller sets/updates S
        if mode=='KEEPER':
            obs=np.log2(max(gmax,1e-300))
            if ks is None: ks=obs
            d=obs-ks
            out_of_bound = d > G
            if abs(d) > (G+1): cnt+=1
            else: cnt=0
            if cnt>=K:
                ks=obs; cnt=0; S=2.0**(14-ks)
            elif out_of_bound:
                skips+=1; scale_log.append(S); continue  # stranger: skip, no state/scale change
            else:
                ks=ks+(1/16)*d
                if t<128:
                    cal.append(max(0.0,d))
                    if t==127 and cal: G=max(1.0,float(np.ceil(np.percentile(cal,99))))
                S=2.0**(14-ks)
        scale_log.append(S)
        qg=[]; fl=0.0; over=False
        for g in grads:
            gq,f=fp16_path(g,S)
            if gq is None: over=True; break
            qg.append(gq); fl+=f
        if over:
            skips+=1
            if mode=='HEURISTIC': S=max(S/2,1.0); grow_timer=0
            continue
        flush_acc.append(fl/6)
        if mode=='HEURISTIC':
            grow_timer+=1
            if grow_timer>=500: S=min(S*2,2.0**24); grow_timer=0
        W1-=lr*qg[0]; b1-=lr*qg[1]; W2-=lr*qg[2]; b2-=lr*qg[3]; W3-=lr*qg[4]; b3-=lr*qg[5]
    # eval
    z1=np.maximum(Xte@W1+b1,0); z2=np.maximum(z1@W2+b2,0); pred=np.argmax(z2@W3+b3,1)
    return {'acc':float((pred==yte).mean()),'skips':skips,
            'flush_mean':float(np.mean(flush_acc)) if flush_acc else 0.0,
            'scale_final':scale_log[-1],'scale_min':float(min(scale_log))}

def run():
    out={}
    for stream,sp in [('CLEAN',False),('SPIKED',True)]:
        for mode in ['HEURISTIC','KEEPER']:
            out[f'{stream}/{mode}']=train(mode,sp)
    return out
r1=run(); r2=run()
h1=hashlib.sha256(json.dumps(r1,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(r2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,h1==h2)
for k,v in r1.items():
    print(f"{k:18s} acc={v['acc']:.4f} skips={v['skips']:4d} flush={v['flush_mean']:.5f} S_final={v['scale_final']:.1f} S_min={v['scale_min']:.1f}")
json.dump(r1,open('exp108_results.json','w'),indent=1)