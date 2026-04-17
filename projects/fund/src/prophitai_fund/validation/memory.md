---
date: 2026-04-16
title: Template Scaffold Never Customized — Detection Pattern
topic: run_failures
---
When strategy code files (strategy.py, wiring.py, signals/model.py, indicators/suite.py, config.py) all import from `strategies.template.*` unchanged, the strategy was never built by Stages 4+5. Red flags: (1) strategy.py contains `TemplateStrategy` class and imports `from strategies.template.indicators import TemplateIndicatorSuite`; (2) MANIFEST.json may belong to a different strategy entirely (wrong strategy name/ID). In this case the backtest still runs (using template EMA/RSI crossover) but all Sharpe ratios are deeply negative on daily data regardless of parameter tuning. Best fix budget usage: fix the runner's interval string and ticker_universe import — the core strategy logic cannot be patched. Verdict is always `failed` in this scenario.

---
date: 2026-04-16
title: LSDA Short-Leg Screener: Strict Joint Filters Yield Very Few Tickers
topic: screener_translation
---
The LSDA short-leg screen (yang_zhang_vol > 0.45 AND return_skewness > 0.8 AND return_kurtosis > 4.0 AND beta_vs_spy > 1.3 AND vol_ratio_short_long > 1.15 AND atr_pct > 0.04 AND momentum_3m > 0.15 AND rsi_14d > 60 AND corr_to_spy_60d > 0.3) returned only 3 tickers in April 2026. The combination of high vol + high skew + high kurtosis + high beta + active vol expansion + high momentum + overbought + correlated is very rare as a joint condition. For lottery-type strategies with strict joint short filters: expect <5 qualifying tickers in any given market snapshot; a proper implementation uses rolling daily evaluation rather than a point-in-time screener. Similarly, strict low-vol long filters (yang_zhang_vol < 0.25, beta_stability < 0.25) returned only 1 ticker — must loosen substantially (to 0.35, 0.30) to get viable universe of 10+.

---
date: 2026-04-17
title: CIM-Class Strategy: Template Scaffold + Wrong MANIFEST = Always Fails
topic: run_failures
---
When strategy_id has IDEA.md for strategy X but MANIFEST.json for a completely different strategy Y (wrong strategy_name/strategy_id in JSON), Stages 4+5 definitely never ran. In this case the entire strategy directory is the raw template scaffold. The run_vectorized_backtest.py also uses `"1d"` as interval string — invalid; must be `"daily"`. Fix budget: (1) patch runner to import local ticker_universe and use `interval="daily"`, `start/end` from MANIFEST backtest config. Best Sharpe for template EMA/RSI crossover on any daily universe is ~0.31 (long-only variant) — never reaches 0.5. Verdict is always `failed`, not `build_failure` since the template does run cleanly after wiring fixes.

