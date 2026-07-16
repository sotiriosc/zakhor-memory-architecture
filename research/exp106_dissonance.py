"""exp106 — Dissonance: dual-path per-sample integrity bit."""
import numpy as np, hashlib, json
import exp101_contact as base
import exp105_neighbors as x5

def dual_forward(X, ys, Ws, bs, p_corrupt, seed):
    rng = np.random.RandomState(seed)
    trackers = [x5.Tracker() for _ in range(3)]
    stats = {'strangers':0,'true_corrupt':0,'disp':[]}
    n = X.shape[0]
    served = np.empty(n,dtype=int); lm_pred = np.empty(n,dtype=int)
    for i in range(n):
        a_lm = X[i]; a_kp = X[i]
        for li,(Wl,bl) in enumerate(zip(Ws,bs)):
            z_lm = a_lm @ Wl + bl
            z_kp = a_kp @ Wl + bl
            if li < len(Ws)-1:
                z_lm = np.maximum(z_lm,0); z_kp = np.maximum(z_kp,0)
            if p_corrupt > 0:
                mask = rng.rand(z_lm.size) < p_corrupt   # one draw, applied to BOTH paths
                z_lm = z_lm.copy(); z_lm[mask] *= x5.PHI**10
                z_kp = z_kp.copy(); z_kp[mask] *= x5.PHI**10
                stats['true_corrupt'] += int(mask.sum())
            a_lm = x5.quantize_localmax(z_lm)
            a_kp = x5.quantize_keeper(z_kp, trackers[li], stats)
        lm_pred[i] = int(np.argmax(a_lm)); served[i] = int(np.argmax(a_kp))
    disagree = lm_pred != served
    wrong = served != ys
    def rate(mask):
        return float(wrong[mask].mean()) if mask.sum() else float('nan')
    out = {
        'served_acc': float((~wrong).mean()),
        'localmax_acc': float((lm_pred==ys).mean()),
        'disagree_rate': float(disagree.mean()),
        'err_given_disagree': rate(disagree),
        'err_given_agree': rate(~disagree),
        'p19_ratio': rate(disagree)/rate(~disagree) if rate(~disagree)>0 else float('inf'),
        'p_dis_given_wrong': float(disagree[wrong].mean()) if wrong.sum() else float('nan'),
        'p_dis_given_right': float(disagree[~wrong].mean()) if (~wrong).sum() else float('nan'),
        'strangers': stats['strangers'], 'true_corrupt': stats['true_corrupt'],
        'regime_events': [t.regime_events for t in trackers],
    }
    out['p21_lift'] = (out['p_dis_given_wrong']/out['p_dis_given_right']
                       if out['p_dis_given_right'] and out['p_dis_given_right']>0 else float('inf'))
    return out

def run():
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    X,y = load_digits(return_X_y=True); X = X/16.0
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.5,random_state=base.SEED,stratify=y)
    clf = MLPClassifier(hidden_layer_sizes=(64,32),max_iter=800,random_state=base.SEED); clf.fit(Xtr,ytr)
    Ws=[w.copy() for w in clf.coefs_]; bs=[b.copy() for b in clf.intercepts_]
    Xs=np.concatenate([Xte,Xte]); ys=np.concatenate([yte,yte])
    return {s: dual_forward(Xs,ys,Ws,bs,p,1) for s,p in [('CLEAN',0.0),('SPARSE',1/512),('DENSE',1/64)]}

r1=run(); r2=run()
h1=hashlib.sha256(json.dumps(r1,sort_keys=True).encode()).hexdigest()[:16]
h2=hashlib.sha256(json.dumps(r2,sort_keys=True).encode()).hexdigest()[:16]
print('HASH',h1,h2,'identical:',h1==h2)
for s in ['CLEAN','SPARSE','DENSE']:
    e=r1[s]
    print(f"{s:7s} served={e['served_acc']:.4f} lm={e['localmax_acc']:.4f} disRate={e['disagree_rate']:.4f} "
          f"err|dis={e['err_given_disagree']:.4f} err|agr={e['err_given_agree']:.4f} P19x={e['p19_ratio']:.2f} "
          f"P21lift={e['p21_lift']:.2f} strangers={e['strangers']} true={e['true_corrupt']} reg={e['regime_events']}")
json.dump(r1,open('exp106_results.json','w'),indent=1)