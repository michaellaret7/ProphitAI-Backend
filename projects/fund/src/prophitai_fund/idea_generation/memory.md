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

---
date: 2026-04-16
title: Screener alpha_vs_spy / alpha_vs_sector = Blitz-Huij-Martens Residual Momentum Native Implementation
topic: tool_usage
---
The screener columns alpha_vs_spy and alpha_vs_sector are, by definition, regression residual returns against the market and sector — i.e., they ARE residual momentum per Blitz-Huij-Martens (2011) finance theory (alpha = Y-intercept of return regression = historical residual return). This means residual momentum strategies can be implemented NATIVELY in the fund screener without needing raw OHLC regression computation. The information_ratio column (= alpha/vol, no rf) provides a risk-adjusted version. Combining alpha_vs_spy + alpha_vs_sector + information_ratio in a composite z-score produces a sector+market-neutralized residual momentum signal directly. For future momentum strategy ideation, these columns are the primary go-to for any neutralized/residualized momentum formulation.

---
date: 2026-04-16
title: Momentum Research DB Gap: Pivot to Web Search for Post-2020 Variant Performance
topic: tool_usage
---
The research DBs (strategy_research, theory_research) are strong on foundational momentum papers (Jegadeesh-Titman, Daniel-Moskowitz, Barroso-Santa-Clara, Grundy-Martin) but have very thin coverage of residual momentum, industry-neutral momentum, and post-2020 factor performance. For Blitz-Huij-Martens residual momentum, Chaves, Huij-Lansdorp, and post-2022 momentum drawdown/recovery evidence, pivot directly to llm_web_search after 1-2 DB queries. Similar gap for analyst forecast dispersion (DMS 2002) — DB returns V/P papers for these queries. Save 3-4 wasted queries by going to web search immediately on these topics.

---
date: 2026-04-16
title: Distribution-Tail Signals: DB Gap Requires Web Search for Modern Evidence
topic: tool_usage
---
For lottery-demand / MAX effect / IVOL puzzle / skewness-return research, strategy_research and theory_research return strong foundational BAB/Frazzini-Pedersen results but are thin on: (a) Bali-Cakici-Whitelaw 2011 MAX specifics, (b) Bali-Brown-Murray-Tang 2017 lottery-beta link, (c) post-2020 IVOL replication, (d) Π-CAPM probability-weighting extension (2025). Pivot immediately to llm_web_search with specific author/year queries. The Frazzini-Pedersen "Betting Against Beta" paper IS fully indexed in theory_research and provides excellent direct quotes — query it directly with mechanism-focused queries. Key pattern: use theory_research for BAB/CAPM/leverage-constraints, web search for MAX/skewness/IVOL specifics. Saved ~3 queries by going to web search early for Π-CAPM and 2017 Bali paper.

---
date: 2026-04-16
title: FIP / Information Discreteness Evidence Best Sourced via Web Search
topic: tool_usage
---
For Da-Gurun-Warachka (2014) Frog-in-the-Pan, information discreteness, and equity-path-smoothness research, strategy_research and theory_research return weak results (generic ML momentum papers, Fama-French term-structure papers). llm_web_search with "Da Gurun Warachka 2014 frog in the pan" and "information discreteness momentum post-2014 replication" returns strong specific evidence: 8pp continuous vs discrete differential, 2024 market-state replication, international replication, Alpha Architect practitioner implementation. Go directly to web search for FIP / information-path / smoothness research. This pattern is consistent with other behavioral-anomaly DB gaps (R&D anomaly, CMA/asset growth, MAX effect specifics, short-interest anomaly) — the research DBs are strong on foundational momentum/factor/volatility papers but thin on specific behavioral-anomaly author names.

---
date: 2026-04-16
title: Screener frog_in_pan and equity_curve_r2 Are Native FIP Implementation
topic: tool_usage
---
The equity screener columns frog_in_pan (description: "low = continuous = better quality") and equity_curve_r2 (description: "0-1, smoothness of cumulative returns") ARE native implementations of Da-Gurun-Warachka (2014) information discreteness and price-path smoothness respectively. This means FIP-style momentum strategies can be implemented natively in the screener without custom OHLC derivation — similar to how alpha_vs_spy/alpha_vs_sector natively implement Blitz-Huij-Martens residual momentum. For future behavioral-momentum ideation, these two columns are the primary go-to for any path-quality or information-arrival-based signal. Complementary columns: zero_return_days_pct (active price formation), autocorrelation_1d (gradual diffusion consistency), frog_in_pan (direct FIP), equity_curve_r2 (direct smoothness).

---
date: 2026-04-17
title: past_ideas write fails if field values contain XML-like angle-bracket tags
topic: process_mistakes
---
The past_ideas(operation='write') tool call FAILED twice with 'write requires all fields' error when my universe field ended with a literal string like '</universe>' or contained any XML-style tag-like pattern (e.g. '<parameter name="entry_exit">'). The tool's argument parser apparently interprets angle-bracket patterns inside parameter values as field delimiters, causing the subsequent fields to be swallowed into the preceding field. Fix: NEVER include angle brackets, HTML tags, XML tags, or parameter-name-like tokens inside any past_ideas field value. Use plain text, parentheses, or quotation marks instead. Also avoid mathematical symbols like less-than / greater-than signs: write 'greater than 0.10' in prose rather than '> 0.10' — this eliminated the error on the third attempt. This will save failed tool calls on future strategy write-ups.

---
date: 2026-04-17
title: PEAD signal requires mid-cap universe filter and event-driven architecture
topic: pipeline_feedback
---
For any future earnings-surprise or PEAD strategy design: (1) DO NOT target large-caps (market_cap > 30B) — PEAD has been arbitraged to near-zero per Subrahmanyam 2024 and Martineau 2022. (2) DO NOT target microcaps (market_cap < 2B) — Chordia et al 2009 show 70-100 percent of gross profit is eaten by costs. (3) The Goldilocks zone is 2B-30B mid-caps. (4) Include revenue-surprise concordance (Jegadeesh-Livnat 2006) — roughly doubles signal robustness vs SUE alone. (5) Quality overlay (ROE, margin, FCF) is mandatory given Garfinkel-Hribar-Hsiao 2024 finding that SUE persistence decay is the primary PEAD-decay driver. (6) PEAD strategies are DISCRETE-EVENT-DRIVEN, not monthly-rebalance — entry is triggered by a specific qualifying earnings release in the past 1-5 days, not a calendar cycle. This requires the Builder to implement an event scanner plus 45-day time-based holding, not a monthly portfolio constructor.

---
date: 2026-04-17
title: Research DB has very thin PEAD/earnings-surprise coverage — pivot to web immediately
topic: tool_usage
---
strategy_research and theory_research return mostly V/P valuation papers and generic momentum citations when queried for PEAD, SUE, earnings surprise, analyst forecast dispersion, short interest anomaly, or betting-against-correlation. For any of these signal families, go DIRECTLY to llm_web_search with specific author-year queries: 'Chordia Goyal Sadka Sadka Shivakumar 2009 PEAD liquidity', 'Garfinkel Hribar Hsiao 2024 SUE modern replication', 'Subrahmanyam 2024 PEAD microcap exclusion', 'Jegadeesh Livnat 2006 revenue surprise concordance'. This yielded specific quantitative results (5.1%/3mo hedge return, 2.43%/month illiquid, 78.1% beat rate) that the DB queries never produced. Saves 3-4 wasted DB queries. Pattern consistent with previous memory: DB is strong on momentum/BAB/volatility/factor models but thin on event-driven anomalies, intangible-capital signals, short-interest, and specific behavioral-anomaly author names.

