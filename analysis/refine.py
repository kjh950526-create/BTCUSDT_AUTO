import pandas as pd, numpy as np
df = pd.read_parquet("btc_feat.parquet")
c=df["close"].values; h=df["high"].values; l=df["low"].values; ret=df["ret"].values
n=len(df); yr=df["year"].values

def fwd(k):
    f=np.full(n,np.nan); f[:n-k]=np.log(c[k:]/c[:n-k]); return f

# ---- COST CONTEXT ----
print("=== COST CONTEXT (Binance USDT-M perp) ===")
print("  taker 0.045%/side -> 9.0 bp round trip")
print("  maker 0.018%/side -> 3.6 bp round trip")
print("  + spread/slippage on 1m ~1-3 bp. Edge must clear ~5-10bp to matter.\n")

# ---- REFINED FALSE BREAKOUT: signed forward return after breakout ----
K=60
roll_hi=pd.Series(h).rolling(K).max().shift(1).values
roll_lo=pd.Series(l).rolling(K).min().shift(1).values
print("=== FORWARD RETURN after 60m-range breakout (signed, bp) ===")
print("   (breakout UP: +ret=continuation, -ret=fade/reversal)\n")
for label,ys in [("IN 23-24",{2023,2024}),("OUT 25-26",{2025,2026})]:
    ym=np.isin(yr,list(ys))
    up=ym&(h>roll_hi)&~np.isnan(roll_hi)
    dn=ym&(l<roll_lo)&~np.isnan(roll_lo)
    row=[]
    for M in [5,15,30,60]:
        f=fwd(M)
        up_r=np.nanmean(f[up& ~np.isnan(f)])*1e4
        dn_r=np.nanmean(-f[dn& ~np.isnan(f)])*1e4   # for downbreak, fade = +
        row.append((M,up_r,dn_r))
    print(f"  [{label}]")
    for M,ur,dr in row:
        print(f"    {M:2d}m: UP-break fwd {ur:+.2f}bp | DN-break fwd(dir) {dr:+.2f}bp")
    print()

# ---- SPIKE REVERSAL by spike SIZE (do bigger spikes reverse more?) ----
print("=== SPIKE->REVERSAL by spike magnitude, 15m fwd (OOS 25-26) ===")
ym=np.isin(yr,[2025,2026])
f=fwd(15); sig=np.sign(ret)
for qlo,qhi in [(0.99,0.995),(0.995,0.999),(0.999,1.0)]:
    a=np.nanquantile(np.abs(ret[ym]),qlo); b=np.nanquantile(np.abs(ret[ym]),qhi)
    sel=ym&(np.abs(ret)>=a)&(np.abs(ret)<b if qhi<1 else np.abs(ret)>=a)&~np.isnan(f)
    cont=sig*f
    print(f"  spike {a*1e4:.0f}-{(b*1e4 if qhi<1 else 999):.0f}bp: fwd(dir)={np.nanmean(cont[sel])*1e4:+.2f}bp  reversal_mag n={sel.sum()}")

# ---- PERMUTATION NULL for spike reversal (is -1bp real or noise?) ----
print("\n=== PERMUTATION TEST: spike-reversal significance (OOS) ===")
thr=np.nanquantile(np.abs(ret[ym]),0.99)
f5=fwd(5); sel=ym&(np.abs(ret)>thr)&~np.isnan(f5)
obs=np.nanmean((sig*f5)[sel])*1e4
# null: shuffle the sign of forward move relative to spike
rng=np.random.default_rng(0)
vals=(sig*f5)[sel]
null=[]
for _ in range(2000):
    s=rng.choice([-1,1],size=len(vals))
    null.append(np.mean(np.abs(vals)*s)*1e4)
null=np.array(null)
p=(null<=obs).mean()
print(f"  observed reversal: {obs:+.2f}bp | null mean ~0, p(one-sided)={p:.3f}")
print(f"  -> {'SIGNIFICANT' if p<0.05 else 'not significant'} but magnitude {abs(obs):.1f}bp vs cost ~5-9bp")
