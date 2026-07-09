import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")]
def resample(d,rule):
    return pd.DataFrame({"close":d["close"].resample(rule).last()}).dropna()

# 1h bars, realized vol over trailing 24 bars (1 day). Does LOW vol predict LARGER forward move?
for rule,win,fwd in [("1h",24,24),("4h",18,6)]:
    r=resample(IS,rule); lr=np.log(r["close"]/r["close"].shift(1))
    rv=lr.rolling(win).std()                       # trailing realized vol
    fwd_move=(np.log(r["close"].shift(-fwd)/r["close"])).abs()  # forward abs move over `fwd` bars
    d=pd.DataFrame({"rv":rv,"fwd":fwd_move}).dropna()
    d["q"]=pd.qcut(d["rv"],5,labels=False)
    g=d.groupby("q")["fwd"].mean()*1e4
    print(f"=== {rule} bars: trailing-vol quintile -> forward |move| over {fwd} bars (bp) ===")
    for qi in range(5):
        print(f"   vol Q{qi+1} ({'lowest' if qi==0 else 'highest' if qi==4 else '     '}): fwd |move| {g[qi]:.0f} bp")
    # ratio of expansion: forward move vs its own trailing typical move
    print(f"   -> Q5/Q1 forward-move ratio: {g[4]/g[0]:.2f}x\n")

# Compression breakout flavor: after LOW vol, is the forward move large in RANGE terms?
print("=== interpretation check: is low-vol regime followed by ABOVE-its-own-baseline expansion? ===")
r=resample(IS,"1h"); lr=np.log(r["close"]/r["close"].shift(1))
rv=lr.rolling(24).std()
fwd_move=(np.log(r["close"].shift(-24)/r["close"])).abs()
d=pd.DataFrame({"rv":rv,"fwd":fwd_move}).dropna()
low=d[d["rv"]<d["rv"].quantile(0.2)]
# forward move relative to the trailing vol (expansion multiple)
low_exp=(low["fwd"]/ (low["rv"]*np.sqrt(24))).median()
hi=d[d["rv"]>d["rv"].quantile(0.8)]
hi_exp=(hi["fwd"]/(hi["rv"]*np.sqrt(24))).median()
print(f"  low-vol regime: forward move = {low_exp:.2f}x its trailing expected move")
print(f"  high-vol regime: forward move = {hi_exp:.2f}x its trailing expected move")
print("  (>1 means realized expansion beyond what trailing vol predicted)")
