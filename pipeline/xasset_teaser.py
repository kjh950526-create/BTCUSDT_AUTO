import pandas as pd, numpy as np
P=pd.read_parquet("../data/close_panel_1m.parquet")
IS=P[(P.index>="2023-01-01")&(P.index<"2025-01-01")]
alts=["ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT","ADAUSDT"]
# 5-min returns
r5=np.log(IS/IS.shift(5))
btc=r5["BTCUSDT"]
print("=== contemporaneous 5m return correlation to BTC (IS) ===")
for a in alts: print(f"  {a}: {r5[a].corr(btc):+.3f}")

print("\n=== LEAD-LAG: after LARGE BTC 5m move (top/bottom 1%), alt forward return next k min (same-dir bp) ===")
thr=btc.abs().quantile(0.99)
big=btc.abs()>thr
sign=np.sign(btc)
for a in alts:
    row=[]
    for k in [1,3,5,10]:
        fwd=np.log(IS[a].shift(-k)/IS[a])   # alt forward return AFTER the BTC move bar
        m=(sign*fwd)[big].mean()*1e4
        row.append(f"{k}m {m:+.1f}")
    # also: how much of BTC's move has alt ALREADY captured contemporaneously (co-move)
    co=(sign*np.log(IS[a]/IS[a].shift(5)))[big].mean()*1e4
    print(f"  {a}: co-move(already)={co:+.0f}bp | forward(remaining): "+"  ".join(row))
print("\n(if forward >> 0, alt keeps following AFTER btc move = tradeable lag; if ~0, already arbitraged)")
