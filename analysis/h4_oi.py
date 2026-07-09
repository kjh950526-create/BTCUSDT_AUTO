import pandas as pd, numpy as np
met=pd.read_parquet("project/data/BTCUSDT/BTCUSDT_metrics.parquet")
met=met.set_index("dt")
df=pd.read_parquet("btc_1m.parquet"); df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
px=df.set_index("dt")["close"]
TF="1h"
c=px.resample(TF).last()
oi=met["sum_open_interest"].resample(TF).last()
d=pd.DataFrame({"close":c,"oi":oi}).dropna()
d["dret"]=np.log(d["close"]/d["close"].shift(1))
d["doi"]=d["oi"].pct_change()
# forward return
for k,l in [(1,"1h"),(4,"4h"),(12,"12h")]:
    d[f"fwd{l}"]=np.log(d["close"].shift(-k)/d["close"])

def quad(row):
    if row["dret"]>0 and row["doi"]>0: return "P+OI+ (new longs)"
    if row["dret"]>0 and row["doi"]<0: return "P+OI- (short cover)"
    if row["dret"]<0 and row["doi"]>0: return "P-OI+ (new shorts)"
    return "P-OI- (long liq)"

for name,ys in [("IN-SAMPLE 2023-24",[2023,2024]),("OUT-OF-SAMPLE 2025-26",[2025,2026])]:
    seg=d[d.index.year.isin(ys)].copy()
    seg["quad"]=seg.apply(quad,axis=1)
    print(f"\n=== {name}: forward return by (price,OI) quadrant, {TF} bars ===")
    g=seg.groupby("quad").agg(fwd1=("fwd1h","mean"),fwd4=("fwd4h","mean"),fwd12=("fwd12h","mean"),n=("fwd1h","size"))
    for q,r in g.iterrows():
        print(f"  {q:22s}: fwd1h {r['fwd1']*1e4:+.1f} | fwd4h {r['fwd4']*1e4:+.1f} | fwd12h {r['fwd12']*1e4:+.1f}bp (n={int(r['n'])})")

# focus: does P+OI+ continue and P+OI- fade? build directional signal, IS/OOS, with cost
print("\n=== H4 STRATEGY: long P+OI+ (trend), fade P+OI- (short-cover exhaustion) ; 4h hold ===")
d["quad"]=d.apply(quad,axis=1)
sig=np.select([d["quad"]=="P+OI+ (new longs)", d["quad"]=="P-OI+ (new shorts)",
               d["quad"]=="P+OI- (short cover)", d["quad"]=="P-OI- (long liq)"],
              [1.0,-1.0,-1.0,1.0],0.0)   # trend on new-position quadrants, fade on unwinds
d["sig"]=pd.Series(sig,index=d.index).shift(1)
d["pnl"]=d["sig"]*d["dret"]
cost=d["sig"].diff().abs().fillna(0)*9/1e4
net=d["pnl"]-cost
for nm,ys in [("IS",[2023,2024]),("OOS",[2025,2026])]:
    x=net[net.index.year.isin(ys)].dropna()
    ann=x.mean()*24*365*100/24; sh=x.mean()/x.std()*np.sqrt(24*365) if x.std()>0 else 0
    eq=np.exp(x.cumsum()); dd=((eq/eq.cummax())-1).min()*100
    print(f"  {nm}: ann~{x.mean()*24*365*100:+.0f}% Sharpe={sh:.2f} cum={(eq.iloc[-1]-1)*100:+.0f}% maxDD={dd:.0f}%")
