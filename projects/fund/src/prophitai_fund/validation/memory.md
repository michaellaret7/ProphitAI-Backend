---
date: 2026-04-16
title: Template scaffold detection — HALT the pipeline, do not tune and accept
topic: run_failures
---
If strategy code files (strategy.py, wiring.py, signals/model.py, indicators/suite.py, config.py) import from strategies.template.* unchanged, or reference TemplateStrategy / TemplateSignalModel / TemplateIndicatorSuite class names, the strategy was never built by Stages 4+5. Additional red flag: MANIFEST.json's strategy_id or strategy_name does not match the current strategy_id, or wiring.py imports classes from a different strategy's directory. When any of these is detected, the correct verdict is `build_failure` — halt the validation stage and report upstream. Do NOT run 12 tunings on the template EMA/RSI crossover and record it as a signal-level failure. Recording template scaffold as 'failed' pollutes past_ideas.md and causes future idea generators to skip a genuinely unevaluated signal concept.

---
date: 2026-04-16
title: Strict joint screener filters can return <5 tickers — validate universe size first
topic: screener_translation
---
Some signal designs combine many filters (e.g. vol + skew + kurtosis + beta + momentum + RSI + correlation), producing a valid per-filter screen but near-empty joint result. Before proceeding to tuning, assert that the screened universe has at least ~20 tickers (or the minimum needed for diversification per IDEA.md). If under 5, halt and report the universe construction as structurally broken — either loosen the joint filters or switch to rolling daily evaluation rather than a point-in-time screener. Do not continue to backtest on a 3-ticker universe.

---
date: 2026-04-17
title: ETF screener quantitative columns return zero results — drop at screen time
topic: screener_translation
---
hurst_exponent, autocorrelation_1d, adx_14d, and vol_regime_pctile are sparsely populated in the etf_screener and return zero results when used as filters, even on broad equity_etf universes with other filters relaxed. Workaround: drop all four quantitative regime/behavior filters from etf_screener calls; apply only market_cap, dollar_volume, expense_ratio, nav (price), ann_vol, and industry/sub_industry filters. If IDEA.md requires these as universe gates, they must be computed downstream in the indicator suite — note this as unverifiable at screen time.

---
date: 2026-04-17
title: Structural mismatch between signal logic and universe — treat as build_failure
topic: run_failures
---
When a signal model's long_entry conditions depend on a data gate that is structurally impossible for the chosen universe (e.g. fundamentals_valid == 1.0 on an ETF universe, earnings_in_window on a non-reporting security, sector_neutral gate on a single-sector universe), the strategy produces 0 trades across all parameter variations. Detection: 0 trades on baseline AND 0 trades at every relaxed threshold. Do NOT attempt tuning — verdict is `build_failure`, not `failed`, because the builder wired incompatible components. Report the mismatch upstream (signal/universe incompatibility) so the next run rebuilds rather than re-ranks.

---
date: 2026-04-17
title: Broadcast columns required by signal model must be injected by load_backtest_data
topic: run_failures
---
Strategies that gate entries on broadcast columns (spy_close, spy_above_200sma, vix_level, claims_value) produce 0 trades on baseline if load_backtest_data() doesn't inject the broadcast column into per-ticker DataFrames. Detection pattern: 0 trades + regime_entry_allowed all-zero + the broadcast column all-NaN in sampled ticker DataFrames. Fix: modify load_backtest_data() in wiring.py to load the broadcast source separately, reindex to the per-ticker date index, and inject as a column into every non-source ticker DataFrame. Source ticker (SPY) gets the value from its own close. This is a valid in-validator wiring fix — distinct from the build_failure class above, because the signal model and indicator pipeline are correctly built but the wiring forgot to broadcast.

---
date: 2026-04-17
title: Small universes (<100 tickers) structurally cap event-driven Sharpe
topic: tuning_patterns
---
Event-calendar-gated strategies (earnings-proximate, macro-event-driven) produce ~200 trades over 8 years on a 50-ticker universe at default composite thresholds — too sparse for reliable Sharpe. Lowering the composite entry threshold increases trade count but still fails the Sharpe bar when the universe cannot supply enough simultaneous events. Before tuning, check IDEA.md's target universe size — if the screened result is <25% of target, flag as a universe-size failure and recommend expanding the screen before further tuning. Per-trade edge can be positive (win rate >50%, avg trade >0) even while Sharpe is negative from long flat periods between events.
---
date: 2026-04-17
title: Warmup-period Sharpe drag in vectorized backtest
topic: run_failures
---
Strategies with long warmup periods (e.g., 504 bars = ~2 years for rolling z-score indicators) can show negative Sharpe despite positive per-trade metrics and positive total return. The VectorizedBacktestEngine computes Sharpe over the FULL equity curve including the flat warmup phase. Two flat years depress mean daily return toward zero while daily volatility from the active period appears in the denominator. Detection: total_return_pct > 0, win_rate > 50%, profit_factor > 1, but Sharpe negative. Post-warmup Sharpe computed manually was -1.54 on a case where engine reported -1.76 — showing the warmup is partially but not entirely responsible. Low capital deployment (1/N sizing with few simultaneous positions on a 50-ticker universe) compounds the problem. Fix recommendation: start backtest after warmup completes, expand universe, or use portfolio-level gross-exposure targeting.

---
date: 2026-04-17
title: Financial ratios column naming: TTM suffix mismatch
topic: run_failures
---
Indicator code built for DSY-VSG used column names with TTM suffix (dividendYieldTTM, priceToFreeCashFlowsRatioTTM, etc.) but the actual financial_ratios data from the data resolver uses non-suffixed names (dividendYield, priceToFreeCashFlowsRatio, debtRatio, interestCoverage, dividendPaidAndCapexCoverageRatio). Fix: remove TTM suffix from source column name constants in the indicator. Detection: 0 trades on baseline, all fundamental ratio columns are NaN, but financial_ratios is present in df.attrs with 162 rows.

---
date: 2026-04-18
title: Current-vs-historical universe mismatch in quality-gated strategies
topic: run_failures
---
When a strategy screener selects tickers based on CURRENT fundamental metrics (e.g., asset_turnover >= 0.30 today) but the strategy's indicator pipeline enforces the same gate on HISTORICAL data (e.g., in custom.py hardcoded `_MIN_ASSET_TURNOVER = 0.30`), the backtest will produce very few trades because many tickers didn't meet the gate historically even though they do today. Detection: screener returns 400+ qualifying tickers, backtest fires only 9-14 trades over 7 years. The sparse trades then produce negative Sharpe from the warmup-drag pattern (few positions deployed, long flat periods). Remedies: (1) expand universe to 200+ with historical screening, (2) lower the historical gate threshold (e.g., 0.20 vs 0.30), (3) skip warmup bars from Sharpe calculation.

---
date: 2026-04-20
title: SPY and sector ETFs use kind="equity_price", not commodity
topic: run_failures
---
Indicators needing SPY / QQQ / sector ETF (XLK, XLV, XLF, ...) close series must declare `DataRequirement(kind="equity_price", attrs_key="<name>", scope="shared", params={"symbol": "<SYMBOL>"})`. Declaring `kind="commodity"` with an equity symbol returns empty (CommodityProvider only fetches from the commodity table). One DataRequirement per ETF. FLAG any strategy whose indicator reads `df.attrs['spy']` / `df.attrs['xlk']` but whose indicator-level `data_requirements` use kind="commodity" for those symbols. Detection at validation time: `df.attrs` contains 'vix' but not 'spy'; alpha_vs_spy is all-NaN; composite score stuck at its NaN-fill value; 0 trades. Do NOT accept "fix in wiring.py by manually injecting" — the execution prompt forbids manual fetching (execution.md:211,301); the indicator builder must use the correct kind.

---
date: 2026-04-20
title: ticker_meta is a dict {symbol, sector, industry} — flag string-assumers
topic: run_failures
---
`TickerMetaProvider` attaches a dict `{"symbol", "sector", "industry"}` to `df.attrs[attrs_key]`. Validator should FLAG strategies whose indicator treats `ticker_meta` as a bare ticker string (e.g. using `df.attrs.get("ticker")` and feeding it to a dataframe filter). Expected readers look like `df.attrs["ticker_meta"]["sector"]` or `meta = df.attrs["ticker_meta"]; sector = meta["sector"]`. Detection: `alpha_vs_sector` all-NaN despite sector ETF series being present in `df.attrs`; sector-proxy mapping returns None; 0 sector-residual trades.

---
date: 2026-04-20
title: DataRequirement params=[] vs params={} causes TypeError at **unpacking
topic: run_failures
---
DataRequirement.params must be a dict (defaulting to {}), not a list ([]). When params=[] (a list), the DataResolver's call to provider.fetch(tickers, sd, ed, **req.params) raises TypeError: argument after ** must be a mapping, not list. Fix: change params=[] to params={} in the DataRequirement definition. This is a builder error that appears in indicators with no provider params needed (e.g. ticker_meta which needs no symbol).

