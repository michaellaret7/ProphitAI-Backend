---
date: 2026-04-16
title: Template Scaffold Never Customized — Detection Pattern
topic: run_failures
---
When strategy code files (strategy.py, wiring.py, signals/model.py, indicators/suite.py, config.py) all import from `strategies.template.*` unchanged, the strategy was never built by Stages 4+5. Red flags: (1) strategy.py contains `TemplateStrategy` class and imports `from strategies.template.indicators import TemplateIndicatorSuite`; (2) MANIFEST.json may belong to a different strategy entirely (wrong strategy name/ID). In this case the backtest still runs (using template EMA/RSI crossover) but all Sharpe ratios are deeply negative on daily data regardless of parameter tuning. Best fix budget usage: fix the runner's interval string and ticker_universe import — the core strategy logic cannot be patched. Verdict is always `failed` in this scenario.

