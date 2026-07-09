# BTCUSDT_AUTO — Research State

> Continuity doc for cross-session work. Read this first. Update after each session.
> Last updated: 2026-07-09 (session 2: crash re-test + H3-H5)

## 0. Project goal
Build a rigorously-validated automated trading strategy for Binance USDM perpetual futures.
Owner trades a small fractional sleeve elsewhere; this is a separate crypto-algo research track.

## 1. METHODOLOGY (non-negotiable)
- **Hypothesis-first.** No blind data-mining. Every hypothesis needs a mechanistic "why".
- **In-sample = 2023-01 .. 2024-12. Out-of-sample = 2025-01 .. 2026-07, LOCKED.** Explore only on in-sample; touch OOS only for final validation of a frozen rule.
- **Small number of hypotheses** to control multiple-testing / data-snooping.
- **Cost reference (Binance USDM perp):** taker ~9 bp round trip, maker ~3.6 bp round trip, +1-3 bp slippage on 1m. An edge must clear this to matter.
- Realistic fills = 1-minute close prices (no lookahead — the ORB bug lesson from the MNQ work).

## 2. DATA (regenerate with pipeline/, do NOT commit raw data)
Source: data.binance.vision (public dump; live fapi.binance.com is geo-blocked 451 from some regions).
- **BTCUSDT 1m klines** 2023-01-01 .. 2026-07-07, ~1.85M bars. Clean: 0 gaps, 0 dup, 0 OHLC errors. (root btc_1m.parquet in original session)
- **BTC funding rate** 2023-01 .. 2026-06, 3831 events (8h). mean +0.0067%/8h ~= 7.3%/yr.
- **BTC metrics** (5-min): sum_open_interest, OI value, top-trader L/S ratio, global L/S ratio, taker buy/sell vol ratio. 2023.. , ~370k rows. (via daily/metrics/)
- **Alt 1m klines** (USDM perp): ETH, SOL, XRP, DOGE, BNB, ADA — each ~1.84M bars, 2023-01..2026-06.
- Combined 1m close panel: close_panel_1m.parquet (7 assets).
- Note: klines carry taker_buy_volume (partial order-flow, free).

### Pipeline (pipeline/)
- download_klines.py SYM...   -> monthly 1m klines
- download_derivatives.py SYM -> daily metrics (OI/LS/taker) [+ funding via monthly/fundingRate]
- build_dataset.py           -> parquet per asset + metrics + close panel
All parallel, resumable (skips existing), retry w/ backoff.

## 3. FINDINGS LOG (verdicts)

### Phase 0 — terrain (in-sample)
- Intraday vol shape: NO sharp single opening spike (peak/trough 1.98x, vs NQ ~4-5x). Broad US-session hump 13-16 UTC (=22-01 KST); quietest 05 UTC (14 KST). Weekends ~40% quieter. -> use as filter/context, not a time-of-day anomaly.
- Funding-time (00/08/16 UTC) vol effect weak/mixed. Discard as standalone.

### Phase 1 — fade / false-breakout (mean-reversion)
- Spike->reversal is REAL & stable IS+OOS (perm test p=0.001) but tiny: ~1-2.5 bp < cost. FAIL as tradeable.
- 60m-range breakout "false rate" 72-88% is an ARTIFACT (no null baseline). Signed forward return is the right metric: breakouts fade ~1-2 bp (OOS), regime-dependent in IS. Below cost.
- Conditioning on LOW breakout volume: direction textbook (low-vol fades more, high-vol continued in IS bull) but OOS kills the high-vol continuation; best cell ~1.5 bp. FAIL vs cost.
- Conditioning on taker-buy imbalance: hypothesis (extreme taker = exhaustion = fade) REJECTED; relationship hump-shaped/noisy. FAIL.

### H1 — daily time-series momentum
- FAILED in-sample. Loses to buy&hold on return/Sharpe/drawdown (B&H Sharpe 1.78 vs best mom 1.53). Long/short bleeds (short side in a bull). VR>1 at daily was only mild (1.03-1.07); pure drift-neutral momentum spread is noisy/unstable across lookbacks.
- CAVEAT resolved: CRASH RE-TEST on 2021-2022 (incl -77% bear, data pulled from vision) DONE. Trend-following long/flat HALVES drawdown (SMA100 maxDD -38% vs buy&hold -77%; SMA30 -50%) but doesn't profit long/flat (just loses less). Long/short can profit in bear (SMA30 +33%) but parameter-fragile -> don't trust the number, direction only.
- FINAL H1 verdict: trend-following is NOT standalone alpha; it's a DRAWDOWN-CONTROL / regime overlay — gives up bull upside to roughly halve bear drawdown (classic trend profile). Use as risk overlay, not as the edge.

### H2 — volatility-regime switch (trend vs revert)
- Core structural fact CONFIRMED and strong: regime-conditional lag-1 autocorrelation flips sign. LOW-vol regime = positive autocorr (TREND), HIGH-vol regime = negative autocorr (REVERT). Spread -0.20 (4h), -0.27 (1d). Mechanistically coherent: quiet grind trends; violent liquidation spikes overshoot & snap back. UNIFIES Phase 1 (spikes=high-vol=reversion).
- Explains H1 failure: unconditional momentum mixes trending low-vol with reverting high-vol -> washes out.
- BUT as a strategy: edge lives in lag-1 -> requires flipping ~every bar -> max turnover -> dies to cost (daily 0bp Sharpe 1.34 -> 9bp Sharpe 0.64, < B&H). Smoothing to cut turnover DESTROYS the edge (0bp Sharpe -> 0.30). FAIL as naive tradeable; signal is real.

### H3 — funding-extreme contrarian (derivatives)
- Relationship REAL and (unlike IS) clean in OOS: high funding (crowded longs) -> -170 bp/3d in 2025-26. But IS bull makes high-funding still +ve -> can't build a validated short rule from IS. Absolute-threshold strategy: IS +12%/Sh0.35, OOS -18%/Sh-0.42 (FAILS; funding level is non-stationary, IS threshold doesn't transfer). Adaptive funding z-score version ALSO negative IS+OOS after 9bp cost. FAIL as tradeable. Only robust half: negative funding -> higher fwd return (IS +129, OOS +36, both +ve) — a weak long-only sliver.

### H4 — OI-surge + price quadrant (derivatives)
- (price up/down x OI up/down) quadrants do NOT separate forward returns: IS all +ve (bull drift), OOS all -ve (drift), no differentiation by quadrant. Mechanistic "OI confirms trend" story does not show up at 1h. Hourly strategy dies to turnover (-100%). FAIL.

### H5 — cross-asset BTC->alt lead-lag
- Liquid alts (ETH/SOL/XRP/DOGE/BNB/ADA) AND mid-caps (LINK/AVAX/DOT/LTC/ATOM/UNI/FIL/NEAR): strong contemporaneous co-move (corr 0.54-0.83, co-move +80-100bp same 5m bar) but forward return AFTER big BTC move ~0 at 1-3m and NEGATIVE at 5-10m for ALL. -> BTC->alt lag is already arbitraged at 1-minute for the entire liquid+mid universe. Would need sub-minute/tick data. FAIL.


### H6 — order flow / CVD (from taker_buy_volume, the "new info" angle from a GPT feature list)
- Built CVD = cumsum(2*taker_buy - volume). Three tests, all IS/OOS:
  - Breakout CVD-confirmation vs divergence: IS confirmed-breakouts continue (+26 to +46bp spread) but OOS FLIPS sign (confirmed fade) -> regime/momentum-beta, not independent edge. FAIL.
  - Absorption (strong aggression, no price progress -> reversal): wrong sign in IS (-5.2bp), ~0 in OOS. FAIL.
  - Continuous corr(windowed CVD, forward return) = +0.003 IS / -0.006 OOS = essentially ZERO both samples.
- ROOT CAUSE: kline taker volume = aggressor side, which is contemporaneously ~equal to the price move itself, so CVD carries almost no info beyond price. Real order-flow edge needs order book (resting liquidity/absorption) or actual liquidation prints — NOT available from OHLCV+taker. CONFIRMS meta-conclusion.

### Meta-learning (STRONG — confirmed across 6 hypotheses)
At 1-minute+ resolution with Binance perp costs (~9bp taker RT), essentially every simple price/derivatives statistical structure we found is one of: (a) below cost per event (fade, funding), (b) turnover-killed (H2 regime, H4 OI), (c) just market beta (H1 momentum in bull), or (d) already arbitraged (H5 lead-lag). The ONLY thing with genuine, cost-robust value is trend-following as a DRAWDOWN-CONTROL overlay (not alpha). Honest implication: a durable retail edge at this frequency likely needs richer data we don't have (full order book, per-event liquidations) or infrastructure (sub-minute/colocation) out of reach for a solo dev — OR a shift to lower-frequency / bigger-target strategies where cost is a small fraction (none found yet), or discretionary approaches.

## 4. OPEN THREADS / NEXT STEPS
1. **Funding/OI hypotheses (highest priority — data now in hand).** Properly test: funding-extreme contrarian; OI-surge + price (OI up + price up = new money trend vs OI down = short cover); funding carry / basis. Use IS/OOS discipline. This is the real payoff of the derivatives data.
2. **H1 crash re-test.** Owner to provide 2021-2022 (crypto winter ~-77%) Binance BTCUSDT perp 1m in same format -> test trend-following as crash protection (the one arena IS couldn't provide).
3. **Cross-asset, take 2.** Mid-cap alts (slower, bigger lag) and/or conditional on very large BTC moves only; beware survivorship & slippage. Liquid-alt version is dead.
4. Execution note: live fapi is geo-blocked here; the live bot must run on OWNER's server with own API keys. LLM = research/backtest/codegen only, NOT the runtime loop (latency).

## 5. HYPOTHESIS QUEUE
- [x] Phase 0 terrain
- [x] Phase 1 fade (+vol, +taker conditioning) — FAIL (< cost)
- [x] H1 daily momentum — FAIL as alpha; WIN as drawdown overlay (crash-tested 2021-22)
- [x] H2 vol-regime switch — signal real, FAIL as tradeable (turnover)
- [x] H3 funding-extreme contrarian — FAIL after cost (non-stationary)
- [x] H4 OI + price quadrant — FAIL (no separation, turnover)
- [x] H5 cross-asset lead-lag (liquid+mid) — FAIL (arbitraged at 1m)
- [x] H6 order-flow/CVD — FAIL (CVD~price, zero forward corr; needs order book/liquidations)

### Where to go next (all naive 1m price/deriv hypotheses exhausted)
- If continuing: (a) lower-frequency / bigger-target setups where 9bp is a small fraction (unexplored, but no edge found yet); (b) sub-minute/tick data for lead-lag & microstructure (infra-heavy); (c) full order-book / detailed liquidation data (not on vision); (d) accept trend-following risk-overlay as the one real result and stop mining 1m alpha.
- Available but unused data already downloaded: BTC metrics top/global long-short ratios (only OI + taker tested so far); alt funding/metrics (not downloaded); 2021-2022 metrics/funding (downloaded, only klines used).
