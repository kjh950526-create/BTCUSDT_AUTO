import pandas as pd, numpy as np
df = pd.read_parquet("btc_1m.parquet")
df["ret"] = np.log(df["close"]/df["close"].shift(1))
df = df.dropna(subset=["ret"]).reset_index(drop=True)
df["hour"] = df["dt"].dt.hour
df["dow"]  = df["dt"].dt.dayofweek   # 0=Mon
df["date"] = df["dt"].dt.date
df["year"] = df["dt"].dt.year

# ---------- THESIS A: intraday volatility shape ----------
# normalize each day's abs-returns by that day's mean, to get pure SHAPE (regime-free)
df["abr"] = df["ret"].abs()
daily_mean = df.groupby("date")["abr"].transform("mean")
df["abr_norm"] = df["abr"]/daily_mean

hourly = df.groupby("hour")["abr_norm"].mean()
print("=== INTRADAY VOL SHAPE (UTC hour, 1.0 = daily avg) ===")
for h,v in hourly.items():
    bar = "#"*int(round(v*30))
    print(f"{h:02d}:00  {v:.3f}  {bar}")
print(f"peak/trough ratio: {hourly.max()/hourly.min():.2f}  (peak {hourly.idxmax():02d}h, trough {hourly.idxmin():02d}h)")

kst = (hourly.index+9)%24
print("\n(peak hour in KST:", f"{(hourly.idxmax()+9)%24:02d}h )")

# ---------- day of week ----------
dow_names=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
dV = df.groupby("dow")["abr"].mean()
print("\n=== DAY-OF-WEEK avg |1m ret| (bp) ===")
for d,v in dV.items():
    print(f"{dow_names[d]}  {v*1e4:.2f} bp")

# ---------- funding windows: 00/08/16 UTC ----------
print("\n=== FUNDING WINDOWS (00/08/16 UTC), avg |ret| bp by minute offset ===")
fund_hours={0,8,16}
df["minute_of_day"]=df["dt"].dt.hour*60+df["dt"].dt.minute
base = df["abr"].mean()*1e4
for fh in [0,8,16]:
    center=fh*60
    win = df[(df["minute_of_day"]>=center-3)&(df["minute_of_day"]<=center+3)]
    print(f"  {fh:02d}:00 +/-3m avg |ret|: {win['abr'].mean()*1e4:.2f} bp  (baseline {base:.2f})")

df.to_parquet("btc_feat.parquet")
print("\nsaved btc_feat.parquet")
