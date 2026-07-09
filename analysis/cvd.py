import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet"); df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
df=df.set_index("dt")
# per-minute order-flow delta (aggressor side)
df["delta"]=2*df["taker_buy_volume"]-df["volume"]

# aggregate to 15m bars
def agg(rule):
    o=df["open"].resample(rule).first(); h=df["high"].resample(rule).max()
    l=df["low"].resample(rule).min(); c=df["close"].resample(rule).last()
    v=df["volume"].resample(rule).sum(); d=df["delta"].resample(rule).sum()
    return pd.DataFrame({"open":o,"high":h,"low":l,"close":c,"volume":v,"delta":d}).dropna()

for TF,W,fwds in [("15min",20,[4,8,16]),("1h",20,[4,8,24])]:
    b=agg(TF)
    b["cvd"]=b["delta"].cumsum()
    # rolling extremes
    b["px_hi"]=b["high"].rolling(W).max().shift(1)
    b["cvd_roll_hi"]=b["cvd"].rolling(W).max().shift(1)
    # breakout up: new W-bar high in price
    up=b["high"]>b["px_hi"]
    # confirmed if CVD (at this bar) also exceeds its rolling high; diverged otherwise
    conf = up & (b["cvd"]>b["cvd_roll_hi"])
    div  = up & (b["cvd"]<=b["cvd_roll_hi"])
    for k in fwds: b[f"f{k}"]=np.log(b["close"].shift(-k)/b["close"])
    print(f"\n=== {TF} breakout: CONFIRMED vs DIVERGED CVD, forward return (bp) ===")
    for name,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
        ym=b.index.year.isin(ys)
        row_c=[]; row_d=[]
        for k in fwds:
            row_c.append(b.loc[ym&conf,f"f{k}"].mean()*1e4)
            row_d.append(b.loc[ym&div, f"f{k}"].mean()*1e4)
        nc=(ym&conf).sum(); nd=(ym&div).sum()
        print(f"  [{name}] CONFIRMED (n={nc}): "+" ".join(f"{k}b {v:+.1f}" for k,v in zip(fwds,row_c)))
        print(f"  [{name}] DIVERGED  (n={nd}): "+" ".join(f"{k}b {v:+.1f}" for k,v in zip(fwds,row_d)))
        # the tradeable spread: confirmed continuation minus diverged
        spread=[c-d for c,d in zip(row_c,row_d)]
        print(f"           spread(conf-div): "+" ".join(f"{k}b {v:+.1f}" for k,v in zip(fwds,spread)))
