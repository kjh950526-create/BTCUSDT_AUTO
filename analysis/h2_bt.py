import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")]

def stats(x,cost_bp=0,turnover=None):
    x=x.dropna()
    if turnover is not None and cost_bp>0:
        x=x-turnover.reindex(x.index).fillna(0)*cost_bp/1e4
    ann=x.mean()*365*100; sh=x.mean()/x.std()*np.sqrt(365) if x.std()>0 else 0
    eq=np.exp(x.cumsum()); cum=(eq.iloc[-1]-1)*100
    dd=((eq/eq.cummax())-1).min()*100
    return ann,sh,cum,dd

for rule,name,volwin,volq in [("4h","4h",30,90),("1D","1d",14,90)]:
    r=pd.DataFrame({"close":IS["close"].resample(rule).last()}).dropna()
    r["lr"]=np.log(r["close"]/r["close"].shift(1))
    r["rv"]=r["lr"].rolling(volwin).std().shift(1)
    # regime: trailing vol above/below its rolling median (no lookahead)
    r["volmed"]=r["rv"].rolling(volq).median().shift(1)
    r["highvol"]=r["rv"]>r["volmed"]
    # signal for NEXT bar: low-vol -> continue sign(lr); high-vol -> revert -sign(lr)
    base=np.sign(r["lr"])
    r["pos"]=np.where(r["highvol"], -base, base)
    r["pos"]=r["pos"].shift(1)   # act next bar, no lookahead
    r["stratlr"]=r["pos"]*r["lr"]
    r["turn"]=r["pos"].diff().abs().fillna(0)   # position change for cost
    print(f"=== {name} conditional regime strategy (IS 2023-24), long/short ===")
    for cost in [0,6,9]:
        a,s,c,dd=stats(r["stratlr"],cost_bp=cost,turnover=r["turn"])
        print(f"   cost={cost}bp/turn: ann={a:+.0f}% Sharpe={s:.2f} cum={c:+.0f}% maxDD={dd:.0f}%")
    bh=stats(r["lr"]); print(f"   Buy&Hold        : ann={bh[0]:+.0f}% Sharpe={bh[1]:.2f} cum={bh[2]:+.0f}% maxDD={bh[3]:.0f}%")
    # decompose: how does each regime sub-strategy do alone
    lowonly=(np.where(~r["highvol"].shift(1).fillna(False), r["stratlr"],0))
    hionly=(np.where(r["highvol"].shift(1).fillna(False), r["stratlr"],0))
    al,sl,cl,_=stats(pd.Series(lowonly,index=r.index))
    ah,sh2,ch,_=stats(pd.Series(hionly,index=r.index))
    print(f"   [decomp] low-vol trend sleeve: ann={al:+.0f}% Sharpe={sl:.2f} | high-vol revert sleeve: ann={ah:+.0f}% Sharpe={sh2:.2f}")
    print(f"   avg holding: turnover/bar={r['turn'].mean():.2f} (1.0=flip every bar)\n")
