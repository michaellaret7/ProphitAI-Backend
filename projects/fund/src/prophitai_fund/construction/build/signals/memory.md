---
date: 2026-04-09
title: BaseSignalModel.generate() calls enrich() automatically; score_entries does not
topic: framework_gotchas
---
generate() in BaseSignalModel calls validate() then enrich(), then passes the enriched df to all 4 signal methods. Signal methods should reference enriched columns (e.g. is_rebalance_bar) directly — they receive the enriched frame, not the original. score_entries() must manually call validate() and enrich() since it does NOT go through generate().

---
date: 2026-04-09
title: Indicator suites may have no constructor args — check the suite signature
topic: coding_patterns
---
Some indicator suites have no custom __init__ and are instantiated with no arguments (Suite()), while the template suite accepts config=. Check the suite's signature before instantiating — passing config= to a no-arg suite raises TypeError. Suites without config-parameterized indicators typically omit __init__ entirely.

---
date: 2026-04-09
title: OHLCV raw columns are not in indicator_result.all_output_columns
topic: coding_patterns
---
When a signal model's required_columns includes 'close', 'open', 'high', 'low', or 'volume', these will not appear in indicator_result.all_output_columns. This is expected — they're always present as DataFrame inputs, not indicator outputs. Not a validation error. Skip OHLCV raw columns when cross-checking required_columns against indicator outputs.

---
date: 2026-04-09
title: Contract tests: pytest absent, use inline Python assertion scripts
topic: framework_gotchas
---
pytest is NOT installed in the venv and prophitai_algo_trading.testing does NOT exist. Contract tests must be written as inline Python assertion scripts invoked via /home/user/strategies/.venv/bin/python. See run_contract_tests skill for the full pattern.

---
date: 2026-04-10
title: Frozen dataclass test: use normal assignment, not object.__setattr__
topic: verification_failures
---
When testing that a dataclass is frozen, use normal attribute assignment (cfg.field = value) — it raises FrozenInstanceError. Using object.__setattr__(cfg, 'field', value) BYPASSES the frozen check and silently mutates the object, causing subsequent value assertions to fail.

---
date: 2026-04-10
title: signals/__init__.py must export the strategy's own SignalModel class
topic: framework_gotchas
---
When a signals/__init__.py exists (from scaffold tooling), verify it exports the strategy's actual class — not the template. The file may be auto-populated with TemplateSignalModel imports that break the public API contract even though the strategy imports directly from signals.model (so no runtime bug). Always rewrite signals/__init__.py to export the new strategy's SignalModel class before committing.

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
When creating pass-through no-op Series in signal methods (e.g. pd.Series(False, index=df.index) for disabled shorts), always specify dtype=bool explicitly. Without it, pandas infers object dtype in edge cases, causing downstream bool comparisons or _coerce_signal to behave unexpectedly. Always: pd.Series(False, index=df.index, dtype=bool).

---
date: 2026-04-16
title: Pass-through enrich() when manifest specifies diagnostic columns from indicator suite
topic: coding_patterns
---
When manifest specifies enrich_columns as 'diagnostic pass-throughs' already produced by the indicator suite (e.g. for P&L attribution logging), implement enrich() as a simple return-df pass-through with a docstring explaining why. Do NOT try to recompute these columns inside enrich() — they're already in the DataFrame from the indicator pipeline. The _enrich_columns class attribute can be declared for documentation, but validate() only checks required_columns, not enrich_columns.

---
date: 2026-04-16
title: Config day-count fields: int for scheduling, float for financial-ratio thresholds
topic: coding_patterns
---
For config fields representing day counts used as scheduling lags (filing_lag_days, entry_window_days), prefer int — they represent discrete calendar/trading days. For day counts compared against floating-point financial ratios (absolute_cap_days compared to dso/dio/dpo which are float outputs of balance-sheet formulas), float is correct since the comparison target is float. Apply int for scheduling, keep float for financial-ratio thresholds.

---
date: 2026-04-17
title: score_entries and get_sizing_hints must use the same sign convention
topic: framework_gotchas
---
When score_entries() returns abs(composite_score) for direction-agnostic scoring, get_sizing_hints() must also publish hints['score'] = abs(float(composite_score)). Publishing the raw signed value creates an inconsistency: short candidates carry negative scores and the sizer's top-quintile overweight gate (score >= 1.0) fails to fire for strong short signals. Always match the sign convention between score_entries() and get_sizing_hints()['score'].

---
date: 2026-04-17
title: score_entries: clip to the documented range before returning
topic: coding_patterns
---
When score_entries() documents a range (e.g. [0.0, 3.0] for abs(composite_score)), always implement the clip explicitly with .clip(lower=0.0, upper=3.0) before returning. Without it, extreme outlier composite scores pass uncapped into the sizer, causing the top-quintile overweight gate to fire unexpectedly for borderline signals. Fix the docstring/implementation mismatch with .clip() at the return site.

---
date: 2026-04-17
title: Event-driven strategies: check implementation_notes for OR vs AND exit intent
topic: coding_patterns
---
Event-driven strategies with mandatory pre/post-event exits typically use OR logic across exit conditions (e.g. days_to_event <= 1 | reschedule_flag == 1 | regime_off == 1) — any single condition triggers exit. Do NOT default to AND. Always check the manifest's implementation_notes section for explicit OR/AND intent before coding long_exit/short_exit. Missing this produces strategies that only exit on the rare conjunction of all conditions, holding through the event the strategy was designed to avoid.
---
date: 2026-04-17
title: z_window config field: int not float for rolling bar counts
topic: coding_patterns
---
z_window (and any rolling window bar count) should be typed as int in frozen dataclasses, not float. The code reviewer caught z_window: float = 252.0 — rolling window APIs expect int and float weakens the contract. Apply int for ALL rolling window bar-count config fields. Only use float for ratio/threshold comparisons (z_floor, z_cap, composite_entry_threshold, etc.).

---
date: 2026-04-17
title: Dead signal-model params: remove z_trend_min and allow_shorts when pre-computed by suite
topic: coding_patterns
---
When the indicator suite pre-computes gate columns (e.g. trend_gate, universe_quality_gate) from derived features, signal model params like z_trend_min and allow_shorts become dead code — the signal method just checks the pre-computed boolean column. Remove these params from both the signal model __init__ and config dataclass to avoid misleading API. Code reviewer will flag them as "stored but never used" warnings. Pattern: if gate logic lives entirely in derived_features → pre-computed column → signal model checks column directly, no threshold param needed.

---
date: 2026-04-20
title: Config fields from manifest: keep all config_defaults.strategy regardless of suite wiring
topic: coding_patterns
---
The manifest's config_defaults.strategy section defines ALL strategy-facing parameters — including indicator window params — even when the indicator suite takes no constructor args and can't consume them yet. Keep all fields in the config dataclass (they are the documented tunable contract for the Execution Layer Builder to wire later). Add a docstring note clarifying which fields are consumed by the signal model directly vs. which are reserved for suite wiring. Code reviewer will flag them as "dead" but this is by-design for layered builders. The response: add a docstring explanation, not remove the fields.

---
date: 2026-04-20
title: Dead signal-model params: keep in __init__ signature but don't store — noqa: ARG002 pattern
topic: coding_patterns
---
When a signal model accepts threshold params for API compatibility with PSMOConfig (so PSMOStrategy can pass config.long_entry_threshold etc.), but those params are dead because the suite pre-computes eligibility columns, keep the params in __init__ signature with defaults but do NOT store them as self.attr. Add `# noqa: ARG002` inline and a comment explaining why. This avoids ruff ARG002 lint errors AND documents the intent. The code reviewer will flag "stored but never used" — the fix is exactly this pattern: accept but don't store, with noqa + comment.

---
date: 2026-04-20
title: enrich() variable naming: use month_group not intra_month_day for cumsum grouping key
topic: coding_patterns
---
In the monthly rebalance enrich() pattern (from enrich_month_rebalance_signal skill), the cumsum() result used as a groupby key should be named `month_group` (not `intra_month_day`). The code reviewer flagged `intra_month_day` as misleading since it's the group key (increments at month boundaries), not the actual within-month day counter. `trading_day_of_month` = the actual cumcount+1 result. Update the skill accordingly.

---
date: 2026-04-20
title: OR-exit logic: document intent in docstring to silence code reviewer
topic: coding_patterns
---
When long_exit / short_exit implement OR semantics across multiple conditions (any condition sufficient to exit), always add an explicit docstring comment "OR logic per implementation_notes" AND label each condition with (1), (2), (3) inline comments. Code reviewers don't flag the logic as wrong when it's documented this way. APEX build confirmed: the reviewer found no issues with the OR-exit implementation once the conditions were labeled.

---
date: 2026-04-20
title: Direct ADX/Hurst thresholds in signal model: document why not pre-computed gates
topic: coding_patterns
---
When signal methods directly threshold raw indicator columns (adx_14d > adx_min_threshold, hurst_exponent > hurst_min_threshold) rather than consuming pre-computed gate columns, the code reviewer will flag a "design mismatch" warning. Fix: add explicit docstring rationale explaining (a) the manifest lists them as direct entry criteria, (b) they are tunable via config without re-running the indicator pipeline, (c) they differ conceptually from the gate flags (which are pre-computed multi-condition AND expressions). APEX build: added this explanation to the module docstring, reviewer warning resolved.

---
date: 2026-04-21
title: Indicator-suite config drift: document deferred wiring when suite has no constructor args
topic: framework_gotchas
---
If the manifest exposes strategy-facing indicator params but the generated indicator suite has no config-aware __init__, keep the full frozen config contract and add an explicit strategy comment/docstring that suite wiring is deferred to downstream builders. Otherwise code review flags silent config drift between manifest tunables and runtime behavior.

---
date: 2026-04-22
title: allow_shorts must be stored + used in short_entry(); don't suppress with noqa:ARG002
topic: coding_patterns
---
When allow_shorts is a constructor param in a signal model, it must be stored as self._allow_shorts and short_entry() must return pd.Series(False, index=df.index, dtype=bool) when not self._allow_shorts. The noqa:ARG002 pattern is only correct for params that are truly reserved for future wiring (e.g. time strings, thresholds baked into the suite). Behavioral flags that gate signal generation must always be stored and applied. Code reviewer will flag this as an error — it's a real correctness bug, not a style issue.

---
date: 2026-04-22
title: get_sizing_hints: invert or_score for shorts using target_position < 0 branch
topic: coding_patterns
---
For strategies where score_entries() returns a long-biased score (e.g. or_rank_pct / or_score where high = strong long), get_sizing_hints() must publish hints['score'] = 1.0 - float(or_score_val) when target_position < 0 (short candidates). This ensures the sizer's overweight gate fires consistently for strong shorts (low rank = strong short = high inverted score). Pattern: check target_position in get_sizing_hints(), invert the score for shorts, keep raw score for longs.

