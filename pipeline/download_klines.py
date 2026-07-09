"""Download Binance USDM perp 1m klines for any symbol from data.binance.vision (monthly)."""
import sys, os, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
def months(s,e):
    d=dt.date(s[0],s[1],1); out=[]
    while d<=dt.date(e[0],e[1],1):
        out.append(d.strftime("%Y-%m")); d=(d.replace(day=28)+dt.timedelta(days=7)).replace(day=1)
    return out
def fetch(url,outpath,retries=4):
    if os.path.exists(outpath) and os.path.getsize(outpath)>0: return "skip"
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=40) as r: data=r.read()
            with open(outpath,"wb") as f: f.write(data); return "ok"
        except Exception as ex:
            if i==retries-1: return f"FAIL"
            import time; time.sleep(1.5*(i+1))
def download(symbol,s=(2023,1),e=(2026,6),interval="1m",outdir=None):
    outdir=outdir or f"../data/{symbol}/klines"; os.makedirs(outdir,exist_ok=True)
    res={"ok":0,"skip":0,"fail":0}
    tasks=[(f"{BASE}/{symbol}/{interval}/{symbol}-{interval}-{m}.zip",f"{outdir}/{m}.zip") for m in months(s,e)]
    with ThreadPoolExecutor(max_workers=12) as ex:
        for f in as_completed([ex.submit(fetch,u,o) for u,o in tasks]):
            r=f.result(); res["ok"]+=r=="ok"; res["skip"]+=r=="skip"; res["fail"]+=str(r).startswith("FAIL")
    return res
if __name__=="__main__":
    syms=sys.argv[1:] or ["ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"]
    for s in syms: print(s, download(s))
