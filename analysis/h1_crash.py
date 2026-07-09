import pandas as pd, numpy as np
df=pd.read_parquet("/home/claude/btc/project/data/BTCUSDT_2122/BTCUSDT_2122_1m.parquet")
d=pd.DataFrame({"close":df.set_index("dt")["close"].resample("1D").last()}).dropna()
d["lr"]=np.log(d["close"]/d["close"].shift(1))
def stats(x):
    x=x.dropna(); ann=x.mean()*365*100; sh=x.mean()/x.std()*np.sqrt(365) if x.std()>0 else 0
    eq=np.exp(x.cumsum()); return ann,sh,(eq.iloc[-1]-1)*100,((eq/eq.cummax())-1).min()*100
print("=== H1 CRASH RE-TEST: 2021-2022 (incl -77% bear) daily ===")
bh=stats(d["lr"]); print(f"  Buy&Hold          : ann={bh[0]:+.0f}% Sharpe={bh[1]:.2f} cum={bh[2]:+.0f}% maxDD={bh[3]:.0f}%")
print("  --- trend-following long/FLAT (sit out downtrends) ---")
for N in [20,30,50,100]:
    sma=d["close"].rolling(N).mean(); sig=(d["close"]>sma).astype(float).shift(1)
    s=stats(sig*d["lr"]); print(f"  SMA{N:3d}: ann={s[0]:+.0f}% Sharpe={s[1]:.2f} cum={s[2]:+.0f}% maxDD={s[3]:.0f}%")
print("  --- trend-following long/SHORT (short the downtrend) ---")
for N in [20,30,50,100]:
    sma=d["close"].rolling(N).mean(); sig=np.where(d["close"]>sma,1.0,-1.0); sig=pd.Series(sig,index=d.index).shift(1)
    s=stats(sig*d["lr"]); print(f"  SMA{N:3d}: ann={s[0]:+.0f}% Sharpe={s[1]:.2f} cum={s[2]:+.0f}% maxDD={s[3]:.0f}%")
