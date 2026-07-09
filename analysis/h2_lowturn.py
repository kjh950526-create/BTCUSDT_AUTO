import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")]
r=pd.DataFrame({"close":IS["close"].resample("1D").last()}).dropna()
r["lr"]=np.log(r["close"]/r["close"].shift(1))
r["rv"]=r["lr"].rolling(14).std().shift(1)
r["highvol"]=r["rv"]>r["rv"].rolling(90).median().shift(1)

def stats(x,turn=None,cost=0):
    x=x.copy()
    if turn is not None and cost>0: x=x-turn*cost/1e4
    x=x.dropna()
    ann=x.mean()*365*100; sh=x.mean()/x.std()*np.sqrt(365) if x.std()>0 else 0
    eq=np.exp(x.cumsum()); return ann,sh,(eq.iloc[-1]-1)*100,((eq/eq.cummax())-1).min()*100

print("=== LOW-TURNOVER regime strategy (IS 2023-24, daily) ===\n")
for Ntrend in [10,20]:
    for zth in [1.0,1.5]:
        sma=r["close"].rolling(Ntrend).mean()
        # trend sleeve position (low-vol): sign(price - sma)
        trend_pos=np.sign(r["close"]-sma)
        # revert sleeve (high-vol): fade z of price vs sma, only if |z|>zth, hold via ffill
        z=(r["close"]-sma)/(r["close"].rolling(Ntrend).std())
        rev_pos=np.where(z>zth,-1.0,np.where(z<-zth,1.0,np.nan))
        rev_pos=pd.Series(rev_pos,index=r.index).ffill().fillna(0)
        pos=np.where(r["highvol"],rev_pos,trend_pos)
        pos=pd.Series(pos,index=r.index).shift(1)      # no lookahead
        strat=pos*r["lr"]
        turn=pos.diff().abs().fillna(0)
        a0,s0,c0,d0=stats(strat)
        a9,s9,c9,d9=stats(strat,turn,9)
        print(f" Ntrend={Ntrend} zth={zth}: turn/bar={turn.mean():.2f} | 0bp Sharpe={s0:.2f} cum={c0:+.0f}% | 9bp Sharpe={s9:.2f} cum={c9:+.0f}% DD={d9:.0f}%")

bh=stats(r["lr"]); print(f"\n Buy&Hold: Sharpe={bh[1]:.2f} cum={bh[2]:+.0f}% DD={bh[3]:.0f}%")
print("\n(reminder: IS is a bull market -> buy&hold hard to beat on return;")
print(" regime strat's real test is crash-defense in out-of-sample / 2021-22)")
