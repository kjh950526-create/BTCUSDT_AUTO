import pandas as pd, numpy as np
df=pd.read_parquet("btc_feat.parquet")
c=df["close"].values; h=df["high"].values; l=df["low"].values
vol=df["volume"].values; tbuy=df["taker_buy_volume"].values; n=len(df); yr=df["year"].values
def fwd(k):
    f=np.full(n,np.nan); f[:n-k]=np.log(c[k:]/c[:n-k]); return f
K=60
rh=pd.Series(h).rolling(K).max().shift(1).values
rl=pd.Series(l).rolling(K).min().shift(1).values
# taker buy ratio at the breakout bar: 1.0 = all aggressive buying
tbr=np.where(vol>0, tbuy/vol, np.nan)

print("COST REF: taker 9bp RT, maker 3.6bp RT.\n")
def analyze(mask,direction,label):
    idx=np.where(mask)[0]; r=tbr[idx]; ok=~np.isnan(r)
    idx=idx[ok]; r=r[ok]; f15=fwd(15); f30=fwd(30)
    qs=np.nanquantile(r,[0,.2,.4,.6,.8,1.0])
    print(f"[{label}] {'UP' if direction>0 else 'DN'}-break by taker-buy-ratio  (n={len(idx)})")
    for qi in range(5):
        lo,hi=qs[qi],qs[qi+1]
        m=(r>=lo)&((r<hi) if qi<4 else (r<=hi)); sub=idx[m]
        fade15=-direction*np.nanmean(f15[sub])*1e4
        fade30=-direction*np.nanmean(f30[sub])*1e4
        print(f"   TBR Q{qi+1} [{lo:.2f}-{hi:.2f}]: fade15={fade15:+.2f}  fade30={fade30:+.2f}  n={len(sub)}")
    print()

for label,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=np.isin(yr,ys); analyze(ym&(h>rh)&~np.isnan(rh),+1,label)
for label,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=np.isin(yr,ys); analyze(ym&(l<rl)&~np.isnan(rl),-1,label)

# Focused: UP-break with EXTREME taker buy (top 5%) vs the rest
print("=== EXTREME taker-buy up-breaks (TBR>0.75) fade, fwd15/30 ===")
for label,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=np.isin(yr,ys); up=ym&(h>rh)&~np.isnan(rh)&~np.isnan(tbr)
    ext=up&(tbr>0.75); norm=up&(tbr<=0.75)
    for m,nm in [(ext,"TBR>0.75"),(norm,"TBR<=0.75")]:
        print(f"  [{label}] {nm}: fade15={-np.nanmean(fwd(15)[m])*1e4:+.2f}  fade30={-np.nanmean(fwd(30)[m])*1e4:+.2f}  n={m.sum()}")
