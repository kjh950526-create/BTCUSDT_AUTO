import pandas as pd, numpy as np, glob
# funding full range: combine 2021-22 + 2023-26
frf=sorted(glob.glob("project/data/BTCUSDT_2122/fr/*.csv"))+sorted(glob.glob("extra/fr/*.csv"))
# 2122 fr csvs not yet unzipped -> unzip
import zipfile,os
for z in glob.glob("project/data/BTCUSDT_2122/fr/*.zip"):
    with zipfile.ZipFile(z) as zf: zf.extractall("project/data/BTCUSDT_2122/fr")
fr=[]
for f in sorted(glob.glob("project/data/BTCUSDT_2122/fr/*.csv"))+sorted(glob.glob("extra/fr/*.csv")):
    fr.append(pd.read_csv(f))
fr=pd.concat(fr,ignore_index=True).drop_duplicates("calc_time")
fr["dt"]=pd.to_datetime(fr["calc_time"],unit="ms",utc=True); fr=fr.sort_values("dt")

# price 8h from 2023-26 btc (main range for IS/OOS)
df=pd.read_parquet("btc_1m.parquet"); df["dt"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
px=df.set_index("dt")["close"].resample("8h").last().to_frame("close")
m=px.join(fr.set_index("dt")["last_funding_rate"]).dropna()
m["f"]=m["last_funding_rate"]
# forward returns
for k,lbl in [(1,"8h"),(3,"24h"),(9,"3d")]:
    m[f"fwd{lbl}"]=np.log(m["close"].shift(-k)/m["close"])

def block(name,seg):
    print(f"\n=== {name}: forward return by funding tercile (funding fades?) ===")
    seg=seg.copy(); seg["q"]=pd.qcut(seg["f"],3,labels=["low(neg)","mid","high(crowded long)"],duplicates="drop")
    g=seg.groupby("q").agg(f=("f","mean"),fwd8=("fwd8h","mean"),fwd24=("fwd24h","mean"),fwd3d=("fwd3d","mean"),n=("f","size"))
    for qi,r in g.iterrows():
        print(f"  {str(qi):20s} f={r['f']*100:+.4f}% | fwd8h {r['fwd8']*1e4:+.1f} | fwd24h {r['fwd24']*1e4:+.1f} | fwd3d {r['fwd3d']*1e4:+.0f}bp (n={int(r['n'])})")

IS=m[(m.index>="2023-01-01")&(m.index<"2025-01-01")]
OOS=m[m.index>="2025-01-01"]
block("IN-SAMPLE 2023-24",IS)
block("OUT-OF-SAMPLE 2025-26",OOS)

# Simple strategy: fade funding extremes. position = -sign(f - median), held 8h, include funding carry.
print("\n=== H3 STRATEGY: short when funding high, long when funding low (+ carry), 8h holding ===")
def bt(seg,thr_lo,thr_hi):
    seg=seg.copy()
    pos=np.where(seg["f"]>thr_hi,-1.0,np.where(seg["f"]<thr_lo,1.0,0.0))
    pos=pd.Series(pos,index=seg.index).shift(1)
    # price pnl + funding carry: a long pays funding f each period (so -f); short receives (+f)
    price_pnl=pos*seg["fwd8h"]
    carry=-pos*seg["f"]   # long pays f, short receives f
    gross=price_pnl+carry
    cost=pos.diff().abs().fillna(0)*9/1e4    # taker 9bp per flip
    net=(gross-cost).dropna()
    ann=net.mean()*3*365*100; sh=net.mean()/net.std()*np.sqrt(3*365) if net.std()>0 else 0
    eq=np.exp(net.cumsum()); dd=((eq/eq.cummax())-1).min()*100
    expo=(pos!=0).mean()
    return ann,sh,(eq.iloc[-1]-1)*100,dd,expo
# thresholds from IS funding distribution
lo=IS["f"].quantile(0.2); hi=IS["f"].quantile(0.8)
print(f"  thresholds (IS): long if f<{lo*100:.4f}%, short if f>{hi*100:.4f}%")
for nm,seg in [("IN-SAMPLE",IS),("OUT-OF-SAMPLE",OOS)]:
    a,s,c,dd,e=bt(seg,lo,hi)
    print(f"  {nm:14s}: ann={a:+.0f}% Sharpe={s:.2f} cum={c:+.0f}% maxDD={dd:.0f}% exposure={e*100:.0f}%")

print("\n=== H3b ADAPTIVE: fade funding z-score (trailing 90 x 8h = 30d), relative not absolute ===")
def bt_z(seg, zth, win=90):
    seg=seg.copy()
    z=(seg["f"]-seg["f"].rolling(win).mean())/seg["f"].rolling(win).std()
    pos=np.where(z>zth,-1.0,np.where(z<-zth,1.0,0.0))
    pos=pd.Series(pos,index=seg.index).shift(1)
    gross=pos*seg["fwd8h"] + (-pos*seg["f"])   # price + carry
    cost=pos.diff().abs().fillna(0)*9/1e4
    net=(gross-cost).dropna()
    if net.std()==0 or len(net)<10: return None
    ann=net.mean()*3*365*100; sh=net.mean()/net.std()*np.sqrt(3*365)
    eq=np.exp(net.cumsum()); dd=((eq/eq.cummax())-1).min()*100
    return ann,sh,(eq.iloc[-1]-1)*100,dd,(pos!=0).mean()
# compute z on full series so OOS has trailing history
full=m.copy()
for zth in [1.0,1.5,2.0]:
    r_is=bt_z(full[full.index<"2025-01-01"],zth); 
    r_oos=bt_z(full[full.index>="2024-09-01"],zth)  # include warmup then OOS
    # cleaner: run on full, split net
    seg=full.copy()
    z=(seg["f"]-seg["f"].rolling(90).mean())/seg["f"].rolling(90).std()
    pos=pd.Series(np.where(z>zth,-1.0,np.where(z<-zth,1.0,0.0)),index=seg.index).shift(1)
    gross=pos*seg["fwd8h"]+(-pos*seg["f"]); cost=pos.diff().abs().fillna(0)*9/1e4
    net=(gross-cost)
    for nm,sl in [("IS",net[(net.index>="2023-05-01")&(net.index<"2025-01-01")]),("OOS",net[net.index>="2025-01-01"])]:
        nn=sl.dropna(); 
        if nn.std()>0:
            ann=nn.mean()*3*365*100; sh=nn.mean()/nn.std()*np.sqrt(3*365)
            eq=np.exp(nn.cumsum()); dd=((eq/eq.cummax())-1).min()*100
            print(f"  zth={zth} {nm}: ann={ann:+.0f}% Sharpe={sh:.2f} cum={(eq.iloc[-1]-1)*100:+.0f}% maxDD={dd:.0f}%")
