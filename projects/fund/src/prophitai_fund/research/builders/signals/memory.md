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

