import pandas as pd, numpy as np, glob

def to_dt(series):
    v=series.astype("int64")
    # ms ~1.7e12 (13 digits), us ~1.7e15 (16 digits). normalize to ms.
    v=np.where(v>1e14, v//1000, v)
    return pd.to_datetime(v, unit="ms", utc=True)

# spot 1h close
sp=[pd.read_csv(z,compression="zip",header=None) for z in sorted(glob.glob("project/data/BTCUSDT_spot/klines/*.zip"))]
sp=pd.concat(sp,ignore_index=True); sp["dt"]=to_dt(sp[0])
spot=sp.set_index("dt")[4].rename("spot").sort_index()
spot=spot[~spot.index.duplicated()]

perp=pd.read_parquet("btc_1m.parquet"); perp["dt"]=to_dt(perp["open_time"])
perp=perp.set_index("dt")["close"].rename("perp"); perp=perp[~perp.index.duplicated()]

fr=pd.concat([pd.read_csv(f) for f in sorted(glob.glob("extra/fr/*.csv"))],ignore_index=True).drop_duplicates("calc_time")
fr["dt"]=to_dt(fr["calc_time"]); fund=fr.set_index("dt")["last_funding_rate"].rename("f").sort_index()

idx=fund.index
S=spot.reindex(idx,method="nearest",tolerance=pd.Timedelta("30min"))
P=perp.reindex(idx,method="nearest",tolerance=pd.Timedelta("30min"))
d=pd.DataFrame({"spot":S,"perp":P,"f":fund}).dropna()
d["spot_ret"]=d["spot"].pct_change(); d["perp_ret"]=d["perp"].pct_change()
d["carry_ret"]=d["spot_ret"]-d["perp_ret"]+d["f"]
d=d.dropna()
print("aligned range:",d.index.min(),"->",d.index.max(),"n=",len(d))

def stats(x,ppy=3*365):
    x=x.dropna()
    if len(x)<2: return (0,0,0,0)
    ann=x.mean()*ppy*100; sh=x.mean()/x.std()*np.sqrt(ppy) if x.std()>0 else 0
    eq=np.exp(np.log1p(x).cumsum()); dd=((eq/eq.cummax())-1).min()*100
    return ann,sh,(eq.iloc[-1]-1)*100,dd

print("\n=== PASSIVE delta-neutral carry (long spot + short perp) ===")
for nm,seg in [("2023-2026 all",d),("IS 23-24",d[d.index.year.isin([2023,2024])]),("OOS 25-26",d[d.index.year>=2025])]:
    a,s,c,dd=stats(seg["carry_ret"]); fann=seg["f"].mean()*3*365*100
    print(f"  {nm:14s}: ann={a:+.1f}%  Sharpe={s:.2f}  cum={c:+.1f}%  maxDD={dd:.1f}%  (raw funding {fann:+.1f}%/yr)")

print(f"\n  basis risk: std(spot_ret-perp_ret)={ (d['spot_ret']-d['perp_ret']).std()*1e4:.1f} bp/8h")
print(f"  funding negative {(d['f']<0).mean()*100:.0f}% of periods")
neg=d[d["f"]<0]; print(f"  during negative-funding periods: carry avg {neg['carry_ret'].mean()*3*365*100:+.1f}%/yr annualized")

print("\n=== ACTIVE: normal carry when 24h funding>0, reverse when <0 (maker fees) ===")
d["ftr"]=d["f"].rolling(3).mean().shift(1); d["pos"]=np.sign(d["ftr"]).fillna(0)
d["act"]=d["pos"]*d["carry_ret"]; cost=d["pos"].diff().abs().fillna(0)*(2*1.8/1e4)
d["actnet"]=d["act"]-cost
for nm,seg in [("IS 23-24",d[d.index.year.isin([2023,2024])]),("OOS 25-26",d[d.index.year>=2025])]:
    a,s,c,dd=stats(seg["actnet"]); print(f"  {nm:14s}: ann={a:+.1f}%  Sharpe={s:.2f}  cum={c:+.1f}%  maxDD={dd:.1f}%")

print("\n=== yearly funding harvest ===")
for y in [2023,2024,2025,2026]:
    seg=d[d.index.year==y]
    if len(seg): print(f"  {y}: funding {seg['f'].mean()*3*365*100:+.1f}%/yr  carry return {stats(seg['carry_ret'])[0]:+.1f}%/yr ann")
