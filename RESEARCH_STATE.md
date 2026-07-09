# BTCUSDT_AUTO — Research State

> Continuity doc for cross-session work. Read this first. Update after each session.
> Last updated: 2026-07-09

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
- CAVEAT: IS 2023-24 is a one-way bull with no sustained crash, so it CANNOT fairly test trend-following's real value = crash defense. -> re-test needs crash data (see Open Threads).

### H2 — volatility-regime switch (trend vs revert)
- Core structural fact CONFIRMED and strong: regime-conditional lag-1 autocorrelation flips sign. LOW-vol regime = positive autocorr (TREND), HIGH-vol regime = negative autocorr (REVERT). Spread -0.20 (4h), -0.27 (1d). Mechanistically coherent: quiet grind trends; violent liquidation spikes overshoot & snap back. UNIFIES Phase 1 (spikes=high-vol=reversion).
- Explains H1 failure: unconditional momentum mixes trending low-vol with reverting high-vol -> washes out.
- BUT as a strategy: edge lives in lag-1 -> requires flipping ~every bar -> max turnover -> dies to cost (daily 0bp Sharpe 1.34 -> 9bp Sharpe 0.64, < B&H). Smoothing to cut turnover DESTROYS the edge (0bp Sharpe -> 0.30). FAIL as naive tradeable; signal is real.

### Meta-learning
Price-only short-horizon structure on BTC perp is REAL but broadly cost-constrained: big effects are bull-beta or turnover-heavy; clean effects are < 9 bp/event. This motivated moving to non-price (derivatives) data.

### Funding teaser (in-sample, rough)
- Negative funding (crowded shorts) -> higher 3d forward return (+162 bp Q1). High funding still positive fwd (bull drift). Suggestive contrarian-on-funding signal; NOT yet properly tested. qcut collapsed to 4 buckets (mass at default 0.01%).

### Cross-asset lead-lag teaser (in-sample)
- Liquid alts strongly co-move contemporaneously (ETH 0.83, others 0.54-0.68) but forward return AFTER a big BTC 5m move is ~0 or slightly negative for all 6. -> 1-5m BTC->alt lag is ALREADY ARBITRAGED for liquid names. Naive "follow BTC" FAILS here. Would need mid-cap alts or sub-minute data.

## 4. OPEN THREADS / NEXT STEPS
1. **Funding/OI hypotheses (highest priority — data now in hand).** Properly test: funding-extreme contrarian; OI-surge + price (OI up + price up = new money trend vs OI down = short cover); funding carry / basis. Use IS/OOS discipline. This is the real payoff of the derivatives data.
2. **H1 crash re-test.** Owner to provide 2021-2022 (crypto winter ~-77%) Binance BTCUSDT perp 1m in same format -> test trend-following as crash protection (the one arena IS couldn't provide).
3. **Cross-asset, take 2.** Mid-cap alts (slower, bigger lag) and/or conditional on very large BTC moves only; beware survivorship & slippage. Liquid-alt version is dead.
4. Execution note: live fapi is geo-blocked here; the live bot must run on OWNER's server with own API keys. LLM = research/backtest/codegen only, NOT the runtime loop (latency).

## 5. HYPOTHESIS QUEUE (in order)
- [x] Phase 0 terrain
- [x] Phase 1 fade (+vol, +taker conditioning)
- [x] H1 daily momentum (failed IS; crash re-test pending data)
- [x] H2 vol-regime switch (signal real, naive impl fails cost)
- [ ] H3 funding-extreme contrarian  <-- NEXT
- [ ] H4 OI-surge + price direction
- [ ] H5 cross-asset mid-cap lead-lag (pending data)
