import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")]
def rs(rule):
    return pd.DataFrame({"close":IS["close"].resample(rule).last()}).dropna()

print("=== H2 core test: lag-1 return autocorrelation BY VOLATILITY REGIME (IS 2023-24) ===")
print("   hypothesis: high-vol -> positive (trend), low-vol -> negative (revert)\n")
print("   tf   | low-vol ac1 | mid | high-vol ac1 | spread(hi-lo)")
for rule,name,volwin in [("15min","15m",96),("1h","1h",24),("4h","4h",30),("1D","1d",14)]:
    r=rs(rule); r["lr"]=np.log(r["close"]/r["close"].shift(1))
    r["rv"]=r["lr"].rolling(volwin).std().shift(1)   # trailing vol, no lookahead
    r=r.dropna()
    r["nextlr"]=r["lr"].shift(-1)
    # tercile regimes by trailing vol
    r["reg"]=pd.qcut(r["rv"],3,labels=["low","mid","high"])
    acs={}
    for reg in ["low","mid","high"]:
        sub=r[r["reg"]==reg]
        ac=np.corrcoef(sub["lr"][:-1],sub["lr"].shift(-1).dropna())[0,1] if len(sub)>50 else np.nan
        # cleaner: corr of lr and nextlr within regime
        s=sub.dropna(subset=["nextlr"])
        ac=np.corrcoef(s["lr"],s["nextlr"])[0,1]
        acs[reg]=ac
    print(f"   {name:4s} | {acs['low']:+.3f}      | {acs['mid']:+.3f} | {acs['high']:+.3f}       | {acs['high']-acs['low']:+.3f}")

print("\n=== does the effect give a TRADEABLE conditional signal? (1h bars) ===")
print("   forward-1bar return conditioned on [regime x sign of current bar], bp\n")
r=rs("1h"); r["lr"]=np.log(r["close"]/r["close"].shift(1))
r["rv"]=r["lr"].rolling(24).std().shift(1); r=r.dropna()
r["next"]=r["lr"].shift(-1); r=r.dropna()
r["reg"]=pd.qcut(r["rv"],3,labels=["low","mid","high"])
for reg in ["low","high"]:
    sub=r[r["reg"]==reg]
    up=sub[sub["lr"]>0]["next"].mean()*1e4     # after up bar
    dn=sub[sub["lr"]<0]["next"].mean()*1e4     # after down bar
    # continuation strategy pnl per bar = sign(lr)*next
    cont=(np.sign(sub["lr"])*sub["next"]).mean()*1e4
    print(f"   {reg:4s}-vol: after-up {up:+.2f} | after-down {dn:+.2f} | continuation edge {cont:+.2f}bp/bar (n={len(sub)})")
