import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet")
df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
df=df.set_index("dt")

# ===== LOCK OOS: explore only 2023-2024 =====
IS=df[(df.index>="2023-01-01")&(df.index<"2025-01-01")].copy()
print("IS explore window:",IS.index.min(),"->",IS.index.max(),"| rows",len(IS))
print("(2025-2026 LOCKED, untouched)\n")

def resample(d,rule):
    o=d["open"].resample(rule).first(); h=d["high"].resample(rule).max()
    l=d["low"].resample(rule).min(); c=d["close"].resample(rule).last()
    v=d["volume"].resample(rule).sum()
    r=pd.DataFrame({"open":o,"high":h,"low":l,"close":c,"volume":v}).dropna()
    return r

def variance_ratio(logret, q):
    # Lo-MacKinlay variance ratio at horizon q. VR>1 trend, <1 mean-revert
    r=logret.dropna().values; n=len(r)
    mu=r.mean()
    var1=np.sum((r-mu)**2)/(n-1)
    # q-period returns
    rq=np.convolve(r,np.ones(q),'valid')
    m=len(rq)
    varq=np.sum((rq-q*mu)**2)/(m*q)
    return varq/var1

print("=== VARIANCE RATIO term structure (VR>1 trend, VR<1 mean-revert) ===")
tfs=[("1min","1m"),("5min","5m"),("15min","15m"),("1h","1h"),("4h","4h"),("1D","1d")]
for rule,name in tfs:
    r=resample(IS,rule)
    lr=np.log(r["close"]/r["close"].shift(1))
    vrs=[]
    for q in [2,4,8,16]:
        try: vrs.append(f"VR{q}={variance_ratio(lr,q):.3f}")
        except: vrs.append(f"VR{q}=na")
    # lag-1 autocorr
    ac1=lr.autocorr(1)
    print(f"  {name:4s} (n={len(r):6d})  ac1={ac1:+.3f}  "+"  ".join(vrs))

print("\n=== VOLATILITY PERSISTENCE (autocorr of |ret|, lag1) ===")
for rule,name in tfs:
    r=resample(IS,rule); lr=np.log(r["close"]/r["close"].shift(1)).abs()
    print(f"  {name:4s}  ac1(|ret|)={lr.autocorr(1):+.3f}")

# ===== day-of-week mean return, ETF era split =====
print("\n=== DAY-OF-WEEK mean daily return (bp), pre vs post spot-ETF (2024-01-11) ===")
d1=resample(IS,"1D"); d1["lr"]=np.log(d1["close"]/d1["close"].shift(1))*1e4
d1["dow"]=d1.index.dayofweek
for lbl,sub in [("2023 (pre-ETF)",d1[d1.index<"2024-01-11"]),("2024 (ETF era)",d1[d1.index>="2024-01-11"])]:
    g=sub.groupby("dow")["lr"].mean()
    names=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    print(f"  {lbl}: "+"  ".join(f"{names[i]}{g.get(i,float('nan')):+.0f}" for i in range(7)))

# ===== session mean return (Asia vs US, hourly) =====
print("\n=== SESSION mean hourly return (bp), IS ===")
h1=resample(IS,"1h"); h1["lr"]=np.log(h1["close"]/h1["close"].shift(1))*1e4; h1["h"]=h1.index.hour
asia=h1[(h1["h"]>=0)&(h1["h"]<8)]["lr"].mean()
eu=h1[(h1["h"]>=8)&(h1["h"]<13)]["lr"].mean()
us=h1[(h1["h"]>=13)&(h1["h"]<21)]["lr"].mean()
print(f"  Asia 00-08UTC: {asia:+.2f}/h   EU 08-13: {eu:+.2f}/h   US 13-21UTC: {us:+.2f}/h")
