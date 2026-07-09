import pandas as pd, numpy as np
btc=pd.read_parquet("/home/claude/btc/btc_1m.parquet"); btc["dt"]=pd.to_datetime(btc["open_time"],unit="ms",utc=True)
bc=btc.set_index("dt")["close"]
mids=['LINKUSDT','AVAXUSDT','DOTUSDT','LTCUSDT','ATOMUSDT','UNIUSDT','FILUSDT','NEARUSDT']
data={}
for s in mids:
    d=pd.read_parquet(f"/home/claude/btc/project/data/{s}/{s}_1m.parquet")
    data[s]=d.set_index("dt")["close"]
P=pd.DataFrame({**{s:data[s] for s in mids},"BTCUSDT":bc}).sort_index()
IS=P[(P.index>="2023-01-01")&(P.index<"2025-01-01")]
r5=np.log(IS/IS.shift(5)); btcr=r5["BTCUSDT"]
thr=btcr.abs().quantile(0.99); big=btcr.abs()>thr; sign=np.sign(btcr)
print("=== MID-CAP lead-lag after big BTC 5m move (IS) : forward same-dir bp ===")
print(f"{'alt':10s} corr | co-move | fwd1m fwd3m fwd5m fwd10m")
for s in mids:
    co=(sign*np.log(IS[s]/IS[s].shift(5)))[big].mean()*1e4
    fwds=[]
    for k in [1,3,5,10]:
        fwd=np.log(IS[s].shift(-k)/IS[s]); fwds.append((sign*fwd)[big].mean()*1e4)
    corr=r5[s].corr(btcr)
    print(f"{s:10s} {corr:.2f} | {co:+4.0f}bp | "+" ".join(f"{x:+.1f}" for x in fwds))
print("\n(fwd>>0 = tradeable follow-through; ~0/neg = already arbitraged like the liquid alts)")
