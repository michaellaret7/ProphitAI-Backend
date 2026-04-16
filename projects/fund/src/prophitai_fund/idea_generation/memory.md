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
For fundamentals-based daily/monthly strategies, deploy 2 parallel workers: one for signal-existence + mechanism + boundary conditions + costs + counter-evidence (7 queries via strategy_research + theory_research), and one for macro regime context (6 queries via macro_research_search_search + economics_research_search + general_news + us_treasury_rates). This produces comprehensive, non-overlapping results efficiently. The fundamentals worker benefits from theory_research for academic citations (accruals, PEAD, behavioral finance) while strategy_research handles implementation specifics. Workers reliably synthesize their own findings into clean outputs.

---
date: 2026-04-08
title: 2-Worker Parallel Research (Signal + Macro) Highly Efficient for Fundamental Strategies
topic: tool_usage
---
Deploying 2 parallel workers for fundamental/multi-factor strategy research works well: Worker 1 evaluates 3 candidate signal families (7 queries via strategy_research + theory_research), Worker 2 does macro regime context (6 queries via macro_research_search_search + economics_research_search + general_news + market data tools). Workers self-synthesize findings including a clear comparative verdict on candidates. This pattern provides comprehensive coverage and a clean recommendation in a single parallel step. Critical: give Worker 1 a structured 3-candidate format with explicit query assignments per candidate — it keeps findings organized and prevents one signal getting all the attention.

---
date: 2026-04-08
title: Macro Worker Assessments Can Conflict with Signal Worker Verdicts — Synthesize Both
topic: process_mistakes
---
When deploying parallel workers (signal research vs. macro regime), the two workers may give conflicting verdicts. In the AQM-52 run: signal worker picked Candidate A (52-week high, stronger evidence), macro worker picked Candidate B (forecast dispersion, better current regime fit). Resolution: the signal worker's verdict (stronger academic evidence, cleaner mechanism, lower costs) should be the primary tie-breaker when both signals are plausible. The macro regime concern can be addressed by building regime conditioning INTO the strategy (vol-scaling + market state gate) rather than switching to a weaker signal. Don't let short-term macro threats override long-term signal quality — instead, design the regime adaptation into the strategy itself.

---
date: 2026-04-13
title: Direct Tool Calls More Efficient Than Workers for Multi-Signal Research
topic: tool_usage
---
For fundamentals-based quarterly strategies with 3-4 candidate signals, doing 8-10 direct strategy_research + theory_research + macro_research_search + llm_web_search calls sequentially (without workers) is efficient and allows dynamic query pivoting based on early results. Workers are better when 6+ queries must be pre-specified before any results arrive. When first 2-3 queries confirm a direction strongly, direct calls let you immediately follow up with targeted disconfirming queries — workers cannot do this adaptively.

---
date: 2026-04-13
title: Direct Tool Calls Adaptive vs. Workers for Signal Selection Research
topic: tool_usage
---
For multi-candidate signal exploration (testing 3-4 novel signal families before committing to one), direct tool calls are more efficient than workers. Early queries confirmed that the research database returned V/P valuation papers for broad queries; pivoting immediately to more specific angles (operating leverage + revenue acceleration) yielded actionable evidence faster than pre-specified worker queries would have. The adaptive pivot saved ~4 redundant queries. Key pattern: when the research DB repeatedly returns the same paper cluster (V/P / accruals / profitability), immediately switch to llm_web_search for more targeted academic findings.

---
date: 2026-04-14
title: Research DB Returns V/P Papers for Broad Payout/Cash Queries — Pivot to LLM Web Search
topic: tool_usage
---
When querying strategy_research or theory_research for shareholder yield, buyback anomaly, net share issuance, or cash return signals, the DB consistently returns V/P valuation papers and accruals papers instead of the target signal. For these specific signals, immediately pivot to llm_web_search with targeted academic queries (e.g., 'Pontiff Woodgate 2008 share issuance anomaly', 'Aktas Croci CCC working capital returns'). The research DB is much better suited to momentum, factor model, and volatility topics than capital structure / payout anomalies. This saved ~4 queries by pivoting early to llm_web_search for CCC/working capital evidence.

---
date: 2026-04-16
title: R&D Anomaly Evidence Gap in Research DB — Use Web Search Immediately
topic: tool_usage
---
The strategy_research and theory_research DBs return no useful results for R&D intensity, intangible investment, or SGA-to-revenue anomaly queries. All R&D anomaly evidence must come from llm_web_search with specific author/paper queries. The DB is strong for momentum, BAB/low-vol, factor models, and stat-arb but blind to intangible capital research. For future R&D-related strategies, go directly to llm_web_search with queries like 'Leung Mazouz Evans 2020 R&D anomaly alpha Carhart' or 'R&D intensity cross-section returns bear market boundary conditions' — saves 3-4 wasted DB queries.

---
date: 2026-04-16
title: CMA/Asset Growth DB Gap — Use Web Search for Post-2013 Factor Decay Evidence
topic: tool_usage
---
strategy_research and theory_research return very little on asset growth / CMA / investment factor specifically (Cooper-Gulen-Schill 2008, Titman-Wei-Xie 2004, Fama-French CMA performance post-2013). The DBs return V/P and general factor papers instead. llm_web_search with specific author/paper queries is far more efficient for these topics. Critical finding unearthed this way: CMA has decayed substantially since 2013 with aggressive-investment firms OUTPERFORMING in recent years — this disconfirming evidence would have been missed relying only on DB queries. Save ~4 DB queries by going directly to web search for asset-growth / investment-factor topics.

---
date: 2026-04-16
title: Distribution-Tail Signals (MAX, Skewness) Are an Open Territory Within Fund's Strategy Set
topic: pipeline_feedback
---
As of April 2026, the fund has 9 strategies covering fundamental trajectory (CBERM/RACEQ/DQROE/OLIGA/WVCCI/IIMM), price momentum (AQM-52), and intraday microstructure (IVCCM/OMFM-15). ZERO strategies use return-distribution-shape signals (MAX effect, skewness, kurtosis, BAB/low-vol). This is the single largest unexplored dimension in the strategy set. Screener already exposes yang_zhang_vol, return_skewness, return_kurtosis, beta_stability — direct support for distribution-based strategies. Future idea generation should prioritize distribution-tail / behavioral-demand signals, short-interest/ownership signals, and dispersion/correlation signals before returning to more fundamental trajectory variants (which are nearing saturation within this fund's set).

