---
date: 2026-04-09
title: BaseSignalModel.generate() calls enrich() automatically
topic: framework_gotchas
---
generate() in BaseSignalModel calls validate() then enrich(), then passes the enriched df to all 4 signal methods. Signal methods should reference enriched columns (e.g. is_rebalance_bar) directly — they receive the enriched frame, not the original. score_entries() must manually call validate() and enrich() since it does NOT go through generate().

---
date: 2026-04-09
title: AQM52IndicatorSuite takes no constructor args
topic: coding_patterns
---
AQM52IndicatorSuite (and likely other suites with no config-parameterized indicators) has no custom __init__ — instantiate with AQM52IndicatorSuite() (no args). Contrast with template suite which accepts config=.

---
date: 2026-04-09
title: close column is an OHLCV raw input — not in indicator all_output_columns
topic: coding_patterns
---
When a signal model's required_columns includes 'close' (or other OHLCV raw columns like 'open', 'high', 'low', 'volume'), these will not appear in indicator_result.all_output_columns. This is expected — they're always present as DataFrame inputs, not indicator outputs. Not a validation error.

---
date: 2026-04-09
title: run_contract_tests: pytest not installed, use inline Python assertions
topic: framework_gotchas
---
pytest is NOT installed in the venv and prophitai_algo_trading.testing does NOT exist. Contract tests must be written as inline Python assertion scripts using /home/user/strategies/.venv/bin/python. See run_contract_tests skill for the full pattern.

---
date: 2026-04-10
title: Frozen dataclass test: use normal assignment, not object.__setattr__
topic: verification_failures
---
When testing that a dataclass is frozen, use normal attribute assignment (`cfg.field = value`) — it raises FrozenInstanceError. Using `object.__setattr__(cfg, 'field', value)` BYPASSES the frozen check and silently mutates the object, causing subsequent value assertions to fail.

---
date: 2026-04-10
title: signals/__init__.py must export the strategy's own SignalModel class
topic: framework_gotchas
---
When a signals/__init__.py exists (e.g. from scaffold tooling), verify it exports the strategy's actual class — not the template. The file may be auto-populated with TemplateSignalModel imports that break the public API contract even though the strategy imports directly from signals.model (so no runtime bug).

---
date: 2026-04-10
title: ruff binary at /usr/local/bin/ruff, not in venv
topic: verification_failures
---
ruff is installed system-wide at /usr/local/bin/ruff, NOT in .venv/bin/. Use `ruff check file.py` directly (it's on PATH). The sandbox_write tool also auto-runs ruff. Python is at /home/user/strategies/.venv/bin/python.

---
date: 2026-04-14
title: Explicit bool dtype for pd.Series(True/False) no-op signals
topic: coding_patterns
---
When creating pass-through no-op Series in signal methods (e.g. `pd.Series(False, index=df.index)` for disabled shorts), always specify `dtype=bool` explicitly. Without it, pandas infers object dtype in some edge cases, causing downstream bool comparisons or `_coerce_signal` to behave unexpectedly. Always: `pd.Series(False, index=df.index, dtype=bool)`.

---
date: 2026-04-16
title: WVCCI: pass-through enrich() for diagnostic columns from indicator suite
topic: coding_patterns
---
When manifest specifies enrich_columns as "diagnostic pass-throughs" already produced by the indicator suite (e.g. for P&L attribution logging), implement enrich() as a simple return-df pass-through with a docstring explaining why. Do NOT try to recompute these columns inside enrich() — they're already in the DataFrame from the indicator pipeline. The _enrich_columns class attribute can be declared for documentation purposes but validate() only checks required_columns, not enrich_columns.

