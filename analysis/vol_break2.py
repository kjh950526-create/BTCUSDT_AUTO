import pandas as pd, numpy as np
df=pd.read_parquet("btc_feat.parquet")
c=df["close"].values; h=df["high"].values; l=df["low"].values
vol=df["volume"].values; n=len(df); yr=df["year"].values
def fwd(k):
    f=np.full(n,np.nan); f[:n-k]=np.log(c[k:]/c[:n-k]); return f
K=60
rh=pd.Series(h).rolling(K).max().shift(1).values
rl=pd.Series(l).rolling(K).min().shift(1).values
vmean=pd.Series(vol).rolling(K).mean().shift(1).values
relv=np.where((vmean>0),vol/vmean,np.nan)   # clean

def analyze(brk_mask, direction, label):
    idx=np.where(brk_mask)[0]
    rv=relv[idx]; ok=~np.isnan(rv)
    idx=idx[ok]; rv=rv[ok]
    f15=fwd(15)
    qs=np.nanquantile(rv,[0,.2,.4,.6,.8,1.0])
    res=[]
    for qi in range(5):
        lo,hi=qs[qi],qs[qi+1]
        m=(rv>=lo)&((rv<hi) if qi<4 else (rv<=hi))
        sub=idx[m]
        fade = -direction*np.nanmean(f15[sub])*1e4   # +=fade
        res.append((lo,hi,fade,len(sub)))
    print(f"[{label}] {'UP' if direction>0 else 'DN'}-break, fade(+)=reversal, fwd15  (n={len(idx)})")
    for qi,(lo,hi,fade,nn) in enumerate(res):
        print(f"   relvol Q{qi+1} [{lo:5.2f}-{hi:6.2f}]: fade {fade:+.2f}bp  n={nn}")
    print()

for label,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=np.isin(yr,ys)
    analyze(ym&(h>rh)&~np.isnan(rh), +1, label)
for label,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=np.isin(yr,ys)
    analyze(ym&(l<rl)&~np.isnan(rl), -1, label)
