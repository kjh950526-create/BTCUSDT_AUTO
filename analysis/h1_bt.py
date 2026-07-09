import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")]
d=pd.DataFrame({"close":IS["close"].resample("1D").last()}).dropna()
d["lr"]=np.log(d["close"]/d["close"].shift(1))

def stats(x):
    x=x.dropna()
    ann=x.mean()*365*100; sh=x.mean()/x.std()*np.sqrt(365)
    eq=np.exp(x.cumsum()); cum=(eq.iloc[-1]-1)*100
    dd=((eq/eq.cummax())-1).min()*100
    return ann,sh,cum,dd

bh=stats(d["lr"])
print("=== IS 2023-24 daily ===")
print(f"  Buy&Hold          : ann={bh[0]:+.0f}%  Sharpe={bh[1]:.2f}  cum={bh[2]:+.0f}%  maxDD={bh[3]:.0f}%\n")
print("  --- LONG/FLAT (flat instead of short; realistic for crypto) ---")
for N in [7,14,21,30,50]:
    sig=(np.log(d["close"]/d["close"].shift(N))>0).astype(float).shift(1)
    s=stats(sig*d["lr"])
    print(f"  N={N:2d}: ann={s[0]:+.0f}%  Sharpe={s[1]:.2f}  cum={s[2]:+.0f}%  maxDD={s[3]:.0f}%")
print("  --- LONG/SHORT ---")
for N in [7,14,21,30,50]:
    sig=np.sign(np.log(d["close"]/d["close"].shift(N))).shift(1)
    s=stats(sig*d["lr"])
    print(f"  N={N:2d}: ann={s[0]:+.0f}%  Sharpe={s[1]:.2f}  cum={s[2]:+.0f}%  maxDD={s[3]:.0f}%")

# MA-cross variant (price vs N-day SMA)
print("  --- LONG/FLAT price>SMA(N) ---")
for N in [10,20,30,50]:
    sma=d["close"].rolling(N).mean()
    sig=(d["close"]>sma).astype(float).shift(1)
    s=stats(sig*d["lr"])
    print(f"  SMA{N:2d}: ann={s[0]:+.0f}%  Sharpe={s[1]:.2f}  cum={s[2]:+.0f}%  maxDD={s[3]:.0f}%")
