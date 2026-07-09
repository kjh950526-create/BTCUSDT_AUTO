"""Build parquet datasets from downloaded zips. Reproducible."""
import pandas as pd, numpy as np, glob, os, zipfile
KCOLS=["open_time","open","high","low","close","volume","close_time","quote_volume","count","taker_buy_volume","taker_buy_quote_volume","ignore"]

def build_klines(symbol, datadir="../data"):
    files=sorted(glob.glob(f"{datadir}/{symbol}/klines/*.zip"))
    parts=[]
    for f in files:
        with zipfile.ZipFile(f) as z:
            name=z.namelist()[0]
            with z.open(name) as fh:
                first=fh.readline().decode()
                hdr=0 if first.startswith("open_time") else None
        d=pd.read_csv(f,compression="zip",header=hdr,names=None if hdr==0 else KCOLS)
        parts.append(d)
    df=pd.concat(parts,ignore_index=True).drop(columns=["ignore"])
    df=df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
    out=f"{datadir}/{symbol}/{symbol}_1m.parquet"; df.to_parquet(out)
    return df, out

def build_metrics(symbol="BTCUSDT", datadir="../data"):
    files=sorted(glob.glob(f"{datadir}/{symbol}/metrics/*.zip"))
    parts=[]
    for f in files:
        try: parts.append(pd.read_csv(f,compression="zip"))
        except Exception: pass
    m=pd.concat(parts,ignore_index=True)
    m["dt"]=pd.to_datetime(m["create_time"],utc=True)
    m=m.drop_duplicates("dt").sort_values("dt").reset_index(drop=True)
    out=f"{datadir}/{symbol}/{symbol}_metrics.parquet"; m.to_parquet(out)
    return m,out

if __name__=="__main__":
    syms=["ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT","ADAUSDT"]
    panel={}
    for s in syms:
        df,out=build_klines(s); panel[s]=df.set_index("dt")["close"]
        print(f"{s}: {len(df):,} rows -> {out}")
    m,mo=build_metrics("BTCUSDT"); print(f"BTC metrics: {len(m):,} rows -> {mo}")
    # combined close panel incl BTC
    btc=pd.read_parquet("../../btc_1m.parquet"); btc["dt"]=pd.to_datetime(btc["open_time"],unit="ms",utc=True)
    panel["BTCUSDT"]=btc.set_index("dt")["close"]
    P=pd.DataFrame(panel).sort_index()
    P.to_parquet("../data/close_panel_1m.parquet"); print(f"panel: {P.shape} -> close_panel_1m.parquet")
