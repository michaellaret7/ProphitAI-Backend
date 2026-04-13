---
date: 2026-04-07
title: Parallel Worker Deployment for 3-Track Research is Highly Efficient
topic: tool_usage
---
Deploying 3 parallel workers simultaneously (signal-existence, mechanism/boundary, macro-regime) for intraday strategy research produces comprehensive, non-overlapping results in one round. Each worker gets a focused ROLE and exactly 6 sequential queries. Workers reliably complete all queries and synthesize findings. Total research coverage: 18 structured queries + 4 follow-ups in a single parallel step. This pattern is highly efficient for intraday strategy idea generation.


---
date: 2026-04-07
title: Parallel 2-Worker Research for Fundamentals-Based Strategies is Efficient
topic: tool_usage
---
For fundamentals-based daily/monthly strategies, deploy 2 parallel workers: one for signal-existence + mechanism + boundary conditions + costs + counter-evidence (7 queries via strategy_research + theory_research), and one for macro regime context (6 queries via macro_research + economics_research_search + general_news + us_treasury_rates). This produces comprehensive, non-overlapping results efficiently. The fundamentals worker benefits from theory_research for academic citations (accruals, PEAD, behavioral finance) while strategy_research handles implementation specifics. Workers reliably synthesize their own findings into clean outputs.

---
date: 2026-04-08
title: 2-Worker Parallel Research (Signal + Macro) Highly Efficient for Fundamental Strategies
topic: tool_usage
---
Deploying 2 parallel workers for fundamental/multi-factor strategy research works well: Worker 1 evaluates 3 candidate signal families (7 queries via strategy_research + theory_research), Worker 2 does macro regime context (6 queries via macro_research + economics_research_search + general_news + market data tools). Workers self-synthesize findings including a clear comparative verdict on candidates. This pattern provides comprehensive coverage and a clean recommendation in a single parallel step. Critical: give Worker 1 a structured 3-candidate format with explicit query assignments per candidate — it keeps findings organized and prevents one signal getting all the attention.

---
date: 2026-04-08
title: Macro Worker Assessments Can Conflict with Signal Worker Verdicts — Synthesize Both
topic: process_mistakes
---
When deploying parallel workers (signal research vs. macro regime), the two workers may give conflicting verdicts. In the AQM-52 run: signal worker picked Candidate A (52-week high, stronger evidence), macro worker picked Candidate B (forecast dispersion, better current regime fit). Resolution: the signal worker's verdict (stronger academic evidence, cleaner mechanism, lower costs) should be the primary tie-breaker when both signals are plausible. The macro regime concern can be addressed by building regime conditioning INTO the strategy (vol-scaling + market state gate) rather than switching to a weaker signal. Don't let short-term macro threats override long-term signal quality — instead, design the regime adaptation into the strategy itself.

