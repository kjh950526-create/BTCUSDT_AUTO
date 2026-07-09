import pandas as pd, numpy as np, glob
fr=[]
for f in sorted(glob.glob("extra/fr/*.csv")):
    fr.append(pd.read_csv(f))
fr=pd.concat(fr,ignore_index=True).drop_duplicates("calc_time")
fr["dt"]=pd.to_datetime(fr["calc_time"],unit="ms",utc=True)
fr=fr.sort_values("dt").reset_index(drop=True)
print("funding events:",len(fr),"|",fr["dt"].min(),"->",fr["dt"].max())
print("funding rate stats (per 8h): mean {:.4f}% median {:.4f}% min {:.3f}% max {:.3f}%".format(
    fr["last_funding_rate"].mean()*100,fr["last_funding_rate"].median()*100,
    fr["last_funding_rate"].min()*100,fr["last_funding_rate"].max()*100))
ann=(1+fr["last_funding_rate"]).groupby(fr["dt"].dt.year).apply(lambda x:(x.prod()**(1))-1)
# annualized approx: rate*3*365
print("annualized funding (rate*3*365): mean {:.1f}%/yr".format(fr["last_funding_rate"].mean()*3*365*100))

# merge onto daily close for a disciplined teaser (IS only)
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
d=df.set_index("dt")["close"].resample("8h").last().to_frame("close")
d=d.join(fr.set_index("dt")["last_funding_rate"]).dropna()
d["fwd_8h"]=np.log(d["close"].shift(-1)/d["close"])
d["fwd_3d"]=np.log(d["close"].shift(-9)/d["close"])
IS=d[(d.index>="2023-01-01")&(d.index<"2025-01-01")]
print("\n=== TEASER (IS 2023-24): forward return by funding-rate quintile ===")
print("thesis: high positive funding = crowded longs = lower/negative forward return")
IS=IS.copy(); IS["q"]=pd.qcut(IS["last_funding_rate"],5,labels=False,duplicates="drop")
g=IS.groupby("q").agg(fund=("last_funding_rate","mean"),fwd8=("fwd_8h","mean"),fwd3d=("fwd_3d","mean"),n=("fwd_8h","size"))
for qi,row in g.iterrows():
    print(f"  funding Q{int(qi)+1}: rate={row['fund']*100:+.4f}%/8h  fwd8h={row['fwd8']*1e4:+.1f}bp  fwd3d={row['fwd3d']*1e4:+.0f}bp  n={int(row['n'])}")
