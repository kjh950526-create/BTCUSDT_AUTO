import os, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
BASE="https://data.binance.vision/data/spot/monthly/klines"
def months(s,e):
    d=dt.date(s[0],s[1],1); out=[]
    while d<=dt.date(e[0],e[1],1):
        out.append(d.strftime("%Y-%m")); d=(d.replace(day=28)+dt.timedelta(days=7)).replace(day=1)
    return out
def fetch(u,o):
    if os.path.exists(o) and os.path.getsize(o)>0: return "skip"
    for i in range(4):
        try:
            req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=40) as r: d=r.read()
            open(o,"wb").write(d); return "ok"
        except Exception:
            import time; time.sleep(1.5*(i+1))
    return "FAIL"
sym="BTCUSDT"; outdir=f"../data/{sym}_spot/klines"; os.makedirs(outdir,exist_ok=True)
tasks=[(f"{BASE}/{sym}/1h/{sym}-1h-{m}.zip",f"{outdir}/{m}.zip") for m in months((2023,1),(2026,6))]
res={"ok":0,"skip":0,"fail":0}
with ThreadPoolExecutor(max_workers=12) as ex:
    for f in as_completed([ex.submit(fetch,u,o) for u,o in tasks]):
        r=f.result(); res[r if r in res else "fail"]=res.get(r if r in res else "fail",0)+1
print("spot 1h:",res)
