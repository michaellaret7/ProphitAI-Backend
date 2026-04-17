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

---
date: 2026-04-16
title: Config day-count fields: int vs float judgment call
topic: coding_patterns
---
For config fields representing day counts used as scheduling lags (e.g. filing_lag_days), prefer int type — they represent discrete calendar/trading days. For day counts derived from floating-point financial ratios (e.g. dpo_absolute_cap_days compared against dso/dio/dpo which are float outputs of balance-sheet formulas), float is correct since the comparison target is float. Code reviewer flagged both as warnings — apply int for scheduling, keep float for financial-ratio thresholds.

---
date: 2026-04-17
title: score hint in get_sizing_hints should be abs(composite_score)
topic: framework_gotchas
---
When score_entries() returns abs(composite_score) for direction-agnostic scoring, get_sizing_hints() must also publish hints["score"] = abs(float(composite_score)). Publishing the raw signed value creates an inconsistency: short candidates carry negative scores and the sizer's top-quintile overweight gate (score >= 1.0) fails to fire for strong short signals. Always match the sign convention between score_entries() and get_sizing_hints()["score"].

---
date: 2026-04-17
title: score_entries clip to documented range prevents oversized sizer inputs
topic: coding_patterns
---
When score_entries() documents a range (e.g. [0.0, 3.0] for abs(composite_score)), always implement the clip explicitly with `.clip(lower=0.0, upper=3.0)` before returning. Without it, extreme outlier composite scores pass uncapped into the sizer, causing the top-quintile overweight gate (score >= 1.0) to fire unexpectedly for borderline signals. The code reviewer flagged the docstring/implementation mismatch — fixing it with `.clip()` is the correct resolution.

