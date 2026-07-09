import pandas as pd, numpy as np
df=pd.read_parquet("btc_1m.parquet"); df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True); df=df.set_index("dt")
df["delta"]=2*df["taker_buy_volume"]-df["volume"]
def agg(rule):
    c=df["close"].resample(rule).last(); v=df["volume"].resample(rule).sum(); d=df["delta"].resample(rule).sum()
    return pd.DataFrame({"close":c,"volume":v,"delta":d}).dropna()

TF="15min"; W=8
b=agg(TF)
# window aggregates
b["pret"]=np.log(b["close"]/b["close"].shift(W))               # price return over window
b["cvdw"]=b["delta"].rolling(W).sum()/b["volume"].rolling(W).sum()  # normalized net aggression over window
# z-scores over trailing 500 bars (regime-relative, no lookahead)
b["pz"]=(b["pret"]-b["pret"].rolling(500).mean())/b["pret"].rolling(500).std()
b["cz"]=(b["cvdw"]-b["cvdw"].rolling(500).mean())/b["cvdw"].rolling(500).std()
for k in [4,8,16]: b[f"f{k}"]=np.log(b["close"].shift(-k)/b["close"])
b=b.dropna()

# ABSORPTION: strong buying aggression (cz high) but weak price (pz low) -> expect DOWN. symmetric.
print(f"=== {TF} ABSORPTION test: aggression vs price mismatch -> forward return (bp) ===")
print("  buy-absorb = CVD z>1 & price z<0 (buying not lifting price -> bearish)")
print("  sell-absorb= CVD z<-1 & price z>0 (selling not dropping price -> bullish)\n")
for name,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=b.index.year.isin(ys)
    ba=ym&(b["cz"]>1)&(b["pz"]<0)   # expect negative fwd
    sa=ym&(b["cz"]<-1)&(b["pz"]>0)  # expect positive fwd
    for k in [4,8,16]:
        bav=b.loc[ba,f"f{k}"].mean()*1e4; sav=b.loc[sa,f"f{k}"].mean()*1e4
        # combined signal pnl: short buy-absorb, long sell-absorb
        print(f"  [{name}] {k}b: buy-absorb fwd={bav:+.1f} (want<0) | sell-absorb fwd={sav:+.1f} (want>0) | edge={(sav-bav)/2:+.1f}bp  n={ba.sum()}/{sa.sum()}")
    print()

# Also the simple continuous: does CVD-price DIVERGENCE (residual) predict reversal? regression-free check
print("=== continuous: corr(window CVD, forward return) — does aggression predict continuation or fade? ===")
for name,ys in [("IS 23-24",[2023,2024]),("OOS 25-26",[2025,2026])]:
    ym=b.index.year.isin(ys)
    for k in [8,16]:
        cc=b.loc[ym,"cz"].corr(b.loc[ym,f"f{k}"])
        print(f"  [{name}] corr(CVD_z, fwd{k})={cc:+.3f}")
