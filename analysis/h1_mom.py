import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")]
d=pd.DataFrame({"close":IS["close"].resample("1D").last()}).dropna()
d["lr"]=np.log(d["close"]/d["close"].shift(1))
uncond=d["lr"].mean()*1e4
print(f"unconditional daily drift (bull-market beta): {uncond:+.1f} bp/day\n")

print("=== PURE MOMENTUM: fwd return after UP-trend vs DOWN-trend (drift-neutral spread) ===")
print("  lookback | fwd(1d) after up | after down | SPREAD(up-down) | days")
for N in [1,3,5,7,14,21,30]:
    trail=np.log(d["close"]/d["close"].shift(N))     # trailing N-day return
    fwd1=d["lr"].shift(-1)                            # next-day return
    up=trail>0; dn=trail<0
    up_r=fwd1[up].mean()*1e4; dn_r=fwd1[dn].mean()*1e4
    spread=up_r-dn_r
    print(f"   {N:2d}d     | {up_r:+7.1f}         | {dn_r:+7.1f}    | {spread:+7.1f}        | {up.sum()}/{dn.sum()}")

print("\n=== same, but forward 5-day return (does momentum persist multi-day) ===")
print("  lookback | fwd(5d) after up | after down | SPREAD | days")
fwd5=np.log(d["close"].shift(-5)/d["close"])
for N in [3,7,14,21,30]:
    trail=np.log(d["close"]/d["close"].shift(N))
    up=trail>0; dn=trail<0
    up_r=fwd5[up].mean()*1e4; dn_r=fwd5[dn].mean()*1e4
    print(f"   {N:2d}d     | {up_r:+7.1f}         | {dn_r:+7.1f}    | {up_r-dn_r:+7.1f} | {up.sum()}/{dn.sum()}")

# Simple always-in TS-momentum vs buy&hold, IS (isolate skill from beta)
print("\n=== TS-momentum backtest on IS (long if above N-day ago, else SHORT) vs buy&hold ===")
for N in [7,14,21,30]:
    sig=np.sign(np.log(d["close"]/d["close"].shift(N))).shift(1)  # act next day, no lookahead
    strat=(sig*d["lr"]).dropna()
    bh=d["lr"].loc[strat.index]
    def stats(x):
        ann=x.mean()*365*1e2; sh=x.mean()/x.std()*np.sqrt(365)
        cum=np.exp(x.cumsum())[-1]-1
        return ann,sh,cum*100
    a,s,c=stats(strat); ba,bs,bc=stats(bh)
    print(f"   N={N:2d}: MOM ann={a:+.0f}% Sharpe={s:.2f} cum={c:+.0f}%  |  B&H ann={ba:+.0f}% Sharpe={bs:.2f} cum={bc:+.0f}%")
