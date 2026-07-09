import pandas as pd, numpy as np
df = pd.read_parquet("btc_feat.parquet")
c = df["close"].values; h=df["high"].values; l=df["low"].values
n=len(df)

# =========================================================
# TEST 1: SPIKE -> REVERSAL (mean reversion after big 1m move)
# For each bar, if |ret| in top 1% (per-year threshold), measure
# forward return over next k bars, SIGNED so that + = continuation, - = reversal
# =========================================================
df["fwd1"]  = np.log(np.r_[c[1:], np.nan][:n]/c) if False else np.nan
def fwd(k):
    f = np.full(n, np.nan)
    f[:n-k] = np.log(c[k:]/c[:n-k])
    return f
ret = df["ret"].values
for split,mask_years in [("IN (23-24)",{2023,2024}),("OUT(25-26)",{2025,2026})]:
    ym = df["year"].isin(mask_years).values
    thr = np.nanquantile(np.abs(ret[ym]),0.99)
    print(f"\n=== SPIKE->REVERSAL  {split}  (spike=|1m ret|>{thr*1e4:.0f}bp) ===")
    print("  horizon | contin.ret(bp) | reversal? ")
    for k in [1,3,5,15,30]:
        f=fwd(k)
        # continuation return = forward move in SAME direction as spike
        sig = np.sign(ret)
        cont = sig*f  # positive => continued, negative => reversed
        sel = ym & (np.abs(ret)>thr) & ~np.isnan(cont)
        m = np.nanmean(cont[sel])*1e4
        tag = "REVERSAL" if m<0 else "continuation"
        print(f"  {k:3d}m    | {m:8.2f}      | {tag}  (n={sel.sum()})")

# =========================================================
# TEST 2: FALSE BREAKOUT of rolling 60m high/low
# breakout UP = high breaks max(prev 60 highs). "false" if within M bars
# price closes back below the broken level. Measure false-breakout RATE.
# Compare vs continuation.
# =========================================================
K=60
roll_hi = pd.Series(h).rolling(K).max().shift(1).values
roll_lo = pd.Series(l).rolling(K).min().shift(1).values
print("\n\n=== FALSE BREAKOUT of 60m range ===")
for split,mask_years in [("IN (23-24)",{2023,2024}),("OUT(25-26)",{2025,2026})]:
    ym=df["year"].isin(mask_years).values
    for M in [5,15,30]:
        up_break = ym & (h>roll_hi) & ~np.isnan(roll_hi)
        idx=np.where(up_break)[0]; idx=idx[idx<n-M]
        # false if close within next M bars goes back below the broken level (roll_hi)
        false_cnt=0; cont_cnt=0
        for i in idx:
            lvl=roll_hi[i]
            future_close=c[i+1:i+1+M]
            if np.any(future_close<lvl): false_cnt+=1
            else: cont_cnt+=1
        tot=false_cnt+cont_cnt
        print(f"  {split}  UP-break, {M:2d}m window: false={false_cnt/tot*100:.1f}%  (n={tot})")
