"""Download Binance USDM perp derivatives data (funding + metrics/OI) from data.binance.vision.
Reproducible: re-run anytime to rebuild. Data NOT committed to git; regenerated on demand."""
import sys, os, io, zipfile, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE="https://data.binance.vision/data/futures/um"
def months(s,e):
    d=dt.date(s[0],s[1],1); out=[]
    while d<=dt.date(e[0],e[1],1):
        out.append(d.strftime("%Y-%m")); d=(d.replace(day=28)+dt.timedelta(days=7)).replace(day=1)
    return out
def days(s,e):
    d=dt.date(*s); end=dt.date(*e); out=[]
    while d<=end: out.append(d.strftime("%Y-%m-%d")); d+=dt.timedelta(days=1)
    return out

def fetch(url, outpath, retries=4):
    if os.path.exists(outpath) and os.path.getsize(outpath)>0: return "skip"
    for i in range(retries):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r: data=r.read()
            with open(outpath,"wb") as f: f.write(data)
            return "ok"
        except Exception as ex:
            if i==retries-1: return f"FAIL {ex.__class__.__name__}"
            import time; time.sleep(1.5*(i+1))

def download_metrics(symbol, s=(2023,1,1), e=(2026,7,7), outdir=None):
    outdir=outdir or f"../data/{symbol}/metrics"; os.makedirs(outdir,exist_ok=True)
    urls=[(f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{d}.zip", f"{outdir}/{d}.zip") for d in days(s,e)]
    res={"ok":0,"skip":0,"fail":0}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs={ex.submit(fetch,u,o):d for u,o,d in [(u,o,u.split('-metrics-')[1][:10]) for u,o in urls]}
        for f in as_completed(futs):
            r=f.result(); res["ok"]+=r=="ok"; res["skip"]+=r=="skip"; res["fail"]+=str(r).startswith("FAIL")
    return res

if __name__=="__main__":
    sym=sys.argv[1] if len(sys.argv)>1 else "BTCUSDT"
    print(sym, download_metrics(sym))
