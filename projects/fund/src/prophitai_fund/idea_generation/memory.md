---
date: 2026-04-07
title: Parallel 3-worker deployment for intraday strategy research
topic: tool_usage
---
Deploying 3 parallel workers simultaneously (signal-existence, mechanism/boundary, macro-regime) for intraday strategy research produces comprehensive, non-overlapping results in one round. Each worker gets a focused ROLE and exactly 6 sequential queries. Total research coverage: 18 structured queries plus follow-ups in a single parallel step.

---
date: 2026-04-07
title: Parallel 2-worker deployment for fundamentals-based strategy research
topic: tool_usage
---
For fundamentals-based daily/monthly strategies, deploy 2 parallel workers: one for signal-existence plus mechanism plus boundary conditions plus costs plus counter-evidence (7 queries via strategy_research + theory_research), one for macro regime context (6 queries via macro_research + economics_research + general_news + us_treasury_rates). The fundamentals worker benefits from theory_research for academic citations (accruals, PEAD, behavioral finance) while strategy_research handles implementation specifics.

---
date: 2026-04-08
title: Parallel 2-worker research with 3-candidate signal family comparison
topic: tool_usage
---
For fundamental/multi-factor strategy research, deploy 2 parallel workers: Worker 1 evaluates 3 candidate signal families (7 queries across strategy_research + theory_research), Worker 2 covers macro regime context (6 queries). Critical: give Worker 1 a structured 3-candidate format with explicit query assignments per candidate — keeps findings organized and prevents one signal getting all the attention.

---
date: 2026-04-08
title: Signal worker vs macro worker verdict conflicts — signal quality wins
topic: process_mistakes
---
When parallel workers give conflicting verdicts (signal worker favors candidate A on academic evidence, macro worker favors candidate B on current-regime fit), the signal worker's verdict wins when both signals are plausible — stronger academic evidence, cleaner mechanism, and lower costs dominate short-term macro fit. Address the macro concern by building regime conditioning INTO the strategy (vol scaling, market-state gate) rather than switching to a weaker signal. Don't let short-term macro threats override long-term signal quality.

---
date: 2026-04-13
title: Direct tool calls beat workers for multi-signal exploration
topic: tool_usage
---
For fundamentals-based quarterly strategies with 3-4 candidate signals, 8-10 direct strategy_research + theory_research + macro_research + web_search calls sequentially (without workers) is efficient and allows dynamic query pivoting based on early results. Workers are better when 6+ queries must be pre-specified before any results arrive. When first 2-3 queries confirm a direction strongly, direct calls let you immediately follow up with targeted disconfirming queries — workers cannot pivot adaptively.

---
date: 2026-04-13
title: Pivot to web_search when research DB returns the same paper cluster
topic: tool_usage
---
When strategy_research or theory_research repeatedly returns the same paper cluster for distinct queries (commonly V/P valuation papers, accruals papers, or generic momentum papers), immediately switch to web_search with more targeted academic queries (specific author-year citations). The research DBs are strong on foundational momentum, factor models, BAB/low-vol, and volatility topics but thin on capital-structure, intangible-capital, event-driven, and specific behavioral-anomaly topics.

---
date: 2026-04-14
title: Research DB gaps requiring immediate web-search pivot
topic: tool_usage
---
The strategy_research and theory_research DBs return V/P valuation and generic momentum papers for the following signal families and should be skipped after 1 confirmatory query. Go directly to web_search with specific author-year queries for: shareholder yield / buybacks / net share issuance (Pontiff-Woodgate), working-capital / CCC (Aktas-Croci), R&D intensity / intangibles (Leung-Mazouz-Evans), CMA / asset growth / investment factor (Cooper-Gulen-Schill, Titman-Wei-Xie, Fama-French CMA post-2013), lottery / MAX / IVOL / skewness (Bali-Cakici-Whitelaw, Bali-Brown-Murray-Tang, Π-CAPM), Frog-in-the-Pan / information discreteness (Da-Gurun-Warachka), PEAD / SUE / earnings surprise (Chordia-Goyal-Sadka, Garfinkel-Hribar-Hsiao, Subrahmanyam, Jegadeesh-Livnat), earnings announcement premium / EAP (Frazzini-Lamont, Barber-De George-Lehavy-Trueman, Savor-Wilson), residual momentum (Blitz-Huij-Martens, Chaves, Huij-Lansdorp), and analyst forecast dispersion (Diether-Malloy-Scherbina). For BAB / CAPM / leverage constraints, the theory_research DB indexes Frazzini-Pedersen directly with good mechanism quotes — query it first. Going to web search early on these topics saves 3-4 wasted DB queries per session.

---
date: 2026-04-16
title: Screener alpha_vs_spy and alpha_vs_sector are native residual-momentum columns
topic: tool_usage
---
alpha_vs_spy and alpha_vs_sector in the equity screener are, by definition, regression residual returns against the market and sector — i.e., they ARE residual momentum per Blitz-Huij-Martens (2011) finance theory (alpha = Y-intercept of return regression = historical residual return). Residual momentum strategies can be implemented NATIVELY in the fund screener without raw OHLC regression. The information_ratio column (alpha / vol, no rf) provides a risk-adjusted version. Composite z-score of alpha_vs_spy + alpha_vs_sector + information_ratio produces a sector-and-market-neutralized residual momentum signal directly.

---
date: 2026-04-16
title: Screener frog_in_pan and equity_curve_r2 are native FIP implementation
topic: tool_usage
---
frog_in_pan (low = continuous = better quality) and equity_curve_r2 (0-1, smoothness of cumulative returns) in the equity screener ARE native implementations of Da-Gurun-Warachka (2014) information discreteness and price-path smoothness. FIP-style momentum strategies can be implemented natively without custom OHLC derivation. Complementary columns: zero_return_days_pct (active price formation), autocorrelation_1d (gradual diffusion consistency).

---
date: 2026-04-17
title: past_ideas writes fail on angle brackets and mathematical symbols
topic: process_mistakes
---
The past_ideas(operation='write') tool call fails with 'write requires all fields' when any field value contains angle-bracket patterns ('</universe>', '<parameter>', '&lt;tag&gt;') OR mathematical symbols (> 0.10, < 0.40). The argument parser interprets angle brackets as field delimiters and swallows subsequent fields. Always use prose thresholds: 'greater than 0.10', 'less than 0.40', 'approximately 7 to 10', 'between 500 million USD and 10 billion USD'. Writes succeed on first attempt with prose thresholds.

---
date: 2026-04-17
title: PEAD and earnings-event strategies — universe, signal, and architecture checklist
topic: pipeline_feedback
---
For any earnings-surprise or PEAD strategy design: (1) Target market_cap 2B-30B mid-caps — large-cap PEAD is arbitraged to near-zero per Subrahmanyam 2024 / Martineau 2022, microcap gross profit is 70-100 percent cost-eaten per Chordia et al 2009. (2) Require revenue-surprise concordance per Jegadeesh-Livnat 2006 — roughly doubles drift magnitude versus SUE alone. (3) Quality overlay (ROE, margin, FCF) is mandatory per Garfinkel-Hribar-Hsiao 2024 since SUE persistence decay is the primary PEAD-decay driver. (4) PEAD is discrete-event-driven — entry is triggered by a qualifying earnings release in the past 1-5 days, not a monthly calendar cycle. Architect must spec an event scanner plus 45-day time-based holding, not a monthly portfolio constructor.

---
date: 2026-04-17
title: Pre-event exit pattern for earnings-proximate strategies
topic: pipeline_feedback
---
For any earnings-proximate strategy, structure the hold window to exit at exactly one of: pre-event, event, or post-event — never default to holding through the announcement. Pre-event exit (close day before scheduled earnings) eliminates the dominant tail risk (announcement gap) while still capturing the 72 percent of the 21-day EAP realized pre-announcement per Frazzini-Lamont 2007. Pre-event and post-event strategies on the same underlying have non-overlapping hold windows and are structurally orthogonal. Holding through the event must be an explicit design choice with stated tail-risk justification, not a default.

---
date: 2026-04-17
title: Nagel 2012 research path for mean-reversion strategy design
topic: tool_usage
---
For mean-reversion strategies: theory_research for Nagel 2012 liquidity-provision framework (DB has strong Brunnermeier-Pedersen coverage) + web_search for Connors RSI-2 practitioner specs + web_search for Khandani-Lo 2011 cost-aware reversal + web_search for Avellaneda-Lee 2010 ETF stat-arb Sharpe numbers. DB is WEAK on practitioner reversal and backtest numbers but STRONG on the theoretical liquidity-provision mechanism. Complete thesis achievable in 6 queries.

---
date: 2026-04-17
title: ETF screener has only 32 columns — verify column parity before specifying filters
topic: data_limitations
---
The ETF screener has a reduced 32-column set vs 108 for equities. Notably missing on ETF side: alpha, beta_stability, up/down capture, momentum_3m, price_vs_sma200_pct, dist_from_52w_high_pct. Present on ETF side: rsi_14d, bb_width, vol_regime_pctile, yang_zhang_vol, autocorrelation_1d, adx_14d, hurst_exponent, ann_ret, ann_vol, sharpe_ratio, max_drawdown_1y, return_skewness. For ETF strategies, cross-check every universe filter against the ETF column list before writing criteria. Trend filters (200-day SMA) and 52-week-high filters must be computed in indicator-stage logic, not at screener stage.

---
date: 2026-04-17
title: Validator-reported ETF screener quantitative filters return zero results
topic: data_limitations
---
Even though hurst_exponent, autocorrelation_1d, adx_14d, and vol_regime_pctile appear in the ETF screener schema, they are sparsely populated — applying any bound on these columns returns zero results even for broad equity_etf universes with relaxed other filters. When designing ETF universes, drop these four filters from etf_screener calls; apply only market_cap, dollar_volume, expense_ratio, nav (price), ann_vol, and industry/sub_industry. Any quantitative regime/behavior requirement must be implemented downstream in the indicator suite, not filtered at screen time.

---
date: 2026-04-17
title: Before claiming a signal space is unexplored, read past_ideas.md
topic: pipeline_feedback
---
Before proposing a strategy because its signal family is "unexplored in the fund's strategy set", check past_ideas.md for prior attempts. Entries marked "signal concept unevaluated" (pipeline-bug failures) are genuinely unexplored and worth reattempting. Entries marked as real signal failures with best Sharpe and per-trade stats ARE evaluated — proposing the same signal family again without a materially different construction just burns pipeline cycles. The distribution-tail, residual-momentum, FIP, ETF-reversal, and pre-earnings-attention spaces all have prior entries.
---
date: 2026-04-17
title: Real-money ETF performance data is the single most useful disconfirming evidence
topic: tool_usage
---
When researching factor-based equity strategies, web_search for the corresponding real-money ETF (SYLD for shareholder yield, MTUM for momentum, QUAL for quality, etc.) performance over the most recent 1-3 years yields more useful disconfirming evidence than academic decay papers. Real ETFs reveal current crowding, narrow-market underperformance patterns, and timing-skill failures that academic papers don't capture. Two queries that work well: (1) '[ETF ticker] underperformance [recent year] versus S&P 500 [reason]' and (2) '[factor name] strategy weakness during [current dominant theme]'. This single check materially improved the design by exposing the 2024-25 buyback-timing failure that motivated the valuation gate addition.

---
date: 2026-04-17
title: Shareholder yield space was unexplored — confirmed by reading past_ideas first
topic: pipeline_feedback
---
Past ideas to date have all clustered around momentum (RAMD, CIM), distribution-tail (LSDA), event-driven (PEAPH), and ETF reversal (VCLR). The total-payout-yield / capital-return / shareholder-yield family is genuinely unexplored as of 2026-04-17. Adjacent unexplored families per my memory: asset growth / CMA investment factor, analyst forecast dispersion, working-capital / CCC, R&D intensity / intangible capital, short-interest / squeeze. These are still on the table for future runs.

---
date: 2026-04-17
title: Barra MSCI quality descriptors map directly to native screener columns
topic: tool_usage
---
The Barra GEMLT quality factor uses four descriptors — asset turnover, gross margin, gross profit / assets, return on assets — ALL FOUR available natively in the equity screener as asset_turnover_ttm, gross_profit_margin_ttm, return_on_assets_ttm, return_on_capital_employed_ttm. Novy-Marx 2013 gross profitability can be implemented natively without any custom OHLC or line-item derivation. Furthermore, high asset_turnover_ttm serves as a model-free proxy for Peters-Taylor 2017 intangible-capital intensity since asset-light firms have low PPE relative to economic output — sidesteps the lack of SG&A or R&D fields. Combined with change columns (operating_margin_change_yoy, roce_change_5yr, ebit_growth_yoy minus revenue_cagr_3yr) this gives a native implementation of DuPont-style static-plus-trend quality strategies. Future quality/profitability/intangibles strategies can skip custom indicator development entirely and rely on screener composites.

---
date: 2026-04-20
title: Dispersion regime gate is the key novelty for reversal strategies in 2026
topic: tool_usage
---
For reversal-family strategy research in April 2026, the single most valuable web query was 'short term reversal cross-sectional dispersion relationship high dispersion regime stronger alpha'. Returned a direct empirical finding: high-IDR regimes produce approximately 45 percent annualized performance difference for reversal strategies, dispersion outperforms VIX as opportunity indicator. Combined with Goldman 2026-01 data showing SPX dispersion at 97th percentile 4y lookback, this produced a compelling regime-conditioning angle that would not have been found via strategy_research or theory_research DBs. Pattern: when strategy has a natural regime-conditioning story, one targeted web_search query on 'X strategy + regime state + dispersion' is worth three DB queries.

---
date: 2026-04-20
title: Residual reversal is the natural counterpart to failed RAMD residual momentum
topic: pipeline_feedback
---
When a residual-momentum signal family (like RAMD) has been tried and failed at the build stage, the residual-REVERSAL signal on the same screener columns (alpha_vs_spy, alpha_vs_sector, information_ratio) is a distinct signal with opposite sign and different horizon (1-3mo vs 12-1mo) and different mechanism (liquidity provision vs behavioral underreaction). Both can coexist in future strategy sets without overlap. Key design differences downstream must preserve: negative-sign composite (LOSERS not winners), shorter horizon, dispersion gate not momentum gate, higher turnover so stricter liquidity gates.

---
date: 2026-04-20
title: Theory DB has full Daniel-Moskowitz 2016 momentum crashes paper indexed
topic: tool_usage
---
The theory_research DB has the full Daniel-Moskowitz 2016 "Momentum Crashes" paper (JFE vol 122) indexed at doc_id theory_research:MomentumCrashes:ef67d127 including Tables 2, 4, 5, 6, 8 with all regression coefficients, the dynamic weighting formula (w_t proportional to mu_t-1 / sigma_squared_t-1), the bear-market indicator definition (I_B = 1 if cumulative past 2-year market return is negative), the 126-day realized variance spec, and the spanning test results (Sharpe 1.19 vs 0.3 static, 22% alpha vs FF3+static, 7% alpha vs constant-vol). Also has Barroso-Santa-Clara 2015 indexed at doc_id theory_research:Momentum_Has_Its_Moments. For any momentum crash or dynamic momentum strategy design, two targeted queries on these papers produce a complete implementation spec in the research DB without needing web search fallback. Query pattern that worked: "forecasting momentum premium using bear market indicators and ex-ante market variance ... optimal dynamic weighting equation".

---
date: 2026-04-20
title: Long-short momentum is a genuinely unexplored pattern in the fund ledger
topic: pipeline_feedback
---
As of 2026-04-20 no TRUE long/short momentum strategy with dynamic gross scaling has been evaluated by the pipeline. Past momentum ideas are all long-only (RAMD residual-momentum, CIM frog-in-the-pan), both failed as pipeline build bugs not signal failures. LSDA was L/S but on lottery not momentum. The distinct angle that makes L/S momentum non-duplicative is the dynamic panic-state scaler per Daniel-Moskowitz 2016 that solves the crash problem no prior fund idea tackled. Distress filter on the short leg per Merton 1974 also novel in the fund set. This pattern (explicit crash-risk mitigation on a well-known factor) is a good template for future "classic factor with novel risk overlay" ideas — applies to value (crash risk), carry (tail risk), size (liquidity risk), low-vol (anti-momentum decay).

---
date: 2026-04-20
title: VIX commodity tool and macro_indicators confirm Daniel-Moskowitz bear indicator state
topic: tool_usage
---
For momentum strategies needing the Daniel-Moskowitz bear-market indicator (trailing 2-year SPX return negative) and ex-ante variance, three tools together give a complete current-regime snapshot in parallel: commodity_prices VIXUSD for recent vol (60 days), macro_research_search for the "trailing 2-year SPX return" narrative from providers, and BNP/Citi regime clustering notes. April 2026 snapshot: bull market since October 2022 per BNP Paribas 2026 outlook confirms I_B = 0, VIX spiked 31.05 on 3/27/2026 then back to 24-25 range, indicates intermediate variance not panic. Skip web_search for "current momentum regime" queries — Perplexity returns generic framing; the macro_research_search DB has the JPMorgan/Citi/BNP specific numbers needed.

---
date: 2026-04-20
title: Web search for George-Hwang 52-week-high beats DB for proximity-momentum research
topic: tool_usage
---
The strategy_research and theory_research DBs return generic Jegadeesh-Titman and Value-Momentum-Everywhere paper clusters when querying George-Hwang 2004 52-week-high momentum. Go directly to web_search with specific author-year queries (George Hwang 2004, Barroso-Wang 2021, Novy-Marx 2012 echo) for proximity-momentum, intermediate-horizon echo, and anchoring-bias behavioral papers. The research DBs have deep coverage of momentum crashes (Daniel-Moskowitz 2016, Barroso-Santa-Clara 2015) and Value-Momentum-Everywhere (Asness-Moskowitz-Pedersen 2013) but thin coverage of the proximity-anchoring and echo-effect sub-literatures. Pattern confirmed: for well-known but sub-topical papers, go to web search directly after one confirmatory DB query.

---
date: 2026-04-20
title: Asymmetric L/S leg construction differentiates from prior L/S momentum attempts
topic: pipeline_feedback
---
When a L/S momentum strategy has been tried and failed in the fund ledger (PSMO 2026-04-20 with Jegadeesh-Titman 12-1 + Daniel-Moskowitz panic scaler + Merton distress filter), a structurally-distinct L/S momentum can still be non-duplicative if it changes TWO of these three dimensions: (1) the underlying momentum signal (proximity-to-52w-high + Novy-Marx echo, NOT raw 12-1), (2) the short-leg construction philosophy (quiet-decay avoidance of deep-loser Merton zone, NOT distress-filter-protected deep losers), (3) the risk overlay (Barroso-Santa-Clara constant-vol, NOT Daniel-Moskowitz panic-state — advantage: constant-vol overlay uses portfolio-own returns and does not require SPX data which tripped up PSMO). Pattern for future L/S factor strategies: if prior attempt failed on DATA-PIPELINE grounds, a replacement should ALSO choose a mechanism that minimizes external data dependencies (screener-native columns only, no SPX/macro-state overlays).

---
date: 2026-04-21
title: Fundamental-delta signals are screener-native and avoid PSMO/APEX external-data failures
topic: pipeline_feedback
---
L/S momentum strategies based on fundamental-trend deltas (operating_margin_change_yoy, roce_change_5yr, ebit_growth_yoy, revenue_cagr_3yr, eps_growth_yoy, fcf_growth_yoy) are implementable entirely from equity screener columns with zero OHLC regression and zero SPY or macro-state dependency. This directly addresses the two failure modes of PSMO (unregistered SPY data provider for Daniel-Moskowitz panic state) and APEX (undersized universe when signal requires 500+ fundamentally-valid names). Pattern for future 'classic factor with novel risk overlay' designs per my 2026-04-20 memory: when the prior attempt failed on data-pipeline grounds (missing SPY, missing financial_ratios for short-leg distress filter), a replacement should (a) use only screener-native columns, (b) use portfolio-own-return Barroso-Santa-Clara vol overlay not Daniel-Moskowitz state-based scaler, (c) verify no sector-neutral ranking step requires columns unavailable on all candidates. FMLS-TD template applied these three rules explicitly.

---
date: 2026-04-21
title: Citi Thematic Equity Strategy macro DB has named factor-basket tickers
topic: tool_usage
---
The macro_research_search DB indexes Citi's Thematic Equity Strategy report with named factor-basket tickers (CGRBLBRP large-cap beat-and-raise, CGRBSBRP SMID beat-and-raise, CGRBGROE positive ROE trend, CGRBBROE negative ROE trend, CGRBEPSS EPS Sharpe) and live 2025-26 performance attribution. Single query pattern that works: 'Current US equity market regime [year] momentum factor performance earnings growth dispersion cross-sectional opportunity'. This is the best source for real-money-basket disconfirming evidence on factor strategies when web_search returns generic 2010s decay commentary. Saves the web_search step for factor-basket performance that memory entry 2026-04-17 recommended.

---
date: 2026-04-21
title: Two-stage momentum decomposition via Moskowitz-Grinblatt sector aggregate is screener-native
topic: tool_usage
---
Sector-aggregate momentum (Moskowitz-Grinblatt 1999) is implementable natively by averaging momentum_12m_1m_skip across universe names grouped by GICS sector — no sector-index ETF OHLC needed, no external sector-return series. Combined with beta_vs_sector for within-sector BAB ranking (Frazzini-Pedersen 2014), the entire two-stage momentum-decomposition architecture is screener-only. This sidesteps the PSMO SPY-data failure mode because no external regime series is required for either the signal or the Barroso-Santa-Clara portfolio-own-return vol overlay. Pattern for future factor decompositions: check if the macro factor (sector, industry, size, beta) can be computed as a cross-sectional aggregate of a screener column grouped by a native classification field before assuming external data is needed.

---
date: 2026-04-21
title: Real-money factor ETF concentration data disconfirms simple momentum designs
topic: tool_usage
---
Single web_search query on MTUM 2024-2025 performance revealed the 40 percent TMT concentration problem that unconstrained cross-sectional momentum creates in the current AI-dominated regime. This disconfirming evidence directly shaped the design — adding a top-3/bottom-3 sector cap instead of unconstrained cross-sectional ranking. Pattern confirmed from 2026-04-17 memory: real-money factor ETF performance is the single highest-signal disconfirming evidence for factor-strategy designs. Before finalizing any momentum, quality, low-vol, value, or shareholder-yield strategy, query the corresponding major ETF (MTUM, QUAL, USMV, SPYV, SYLD, etc) for 1-3 year recent performance and concentration risks.

---
date: 2026-04-21
title: Structural crash mitigation beats ex-post regime scaling for momentum strategies
topic: pipeline_feedback
---
When designing momentum strategies with crash-risk mitigation, structural mitigation via BAB-style leg construction (long low-beta winners, short high-beta losers) is architecturally superior to ex-post regime scaling (Daniel-Moskowitz panic scaler, bear-market indicator). The structural approach requires only screener-native columns (beta_vs_sector, beta_stability) versus the ex-post approach that needs SPY OHLC plus 24-month return state. PSMO failed on unregistered SPY data; a structural BAB leg would not have had that failure mode. Pattern for future momentum or crash-sensitive strategies: prefer position-construction solutions to risk problems over overlay solutions whenever the same underlying mechanism can be addressed either way. Overlay solutions are also appropriate (Barroso-Santa-Clara portfolio-own-return vol scaling works and has no data dependency) but should layer ON TOP of structural mitigation, not replace it.

---
date: 2026-04-21
title: L/S residual momentum is the unused slot in the fund's momentum ledger
topic: pipeline_feedback
---
As of 2026-04-21 the fund ledger has six momentum or momentum-adjacent ideas but NO true L/S residual momentum. RAMD was residual but long-only. DR3 uses residual losers as reversal (opposite sign and horizon). PSMO/APEX/SRMBN/FMLS-TD are all raw-price or fundamental signals, not residual. RLS-DB fills this slot. Pattern for future momentum-family ideas in this fund: before proposing a new momentum signal, map the existing ledger along three dimensions — (1) signal type: raw-return vs residual-alpha vs sector-aggregate vs fundamental-delta vs 52wk-proximity, (2) legs: long-only vs L/S, (3) crash mitigation: none vs overlay (BSC vol, DM panic scaler, VIX) vs structural (BAB legs, distress filter, quality gate). Any novel strategy must occupy a CELL not already filled. RLS-DB occupies residual-alpha + L/S + BAB-structural + BSC+dispersion overlay — previously empty. Remaining empty cells worth future attention: time-series momentum (TSMOM) with cross-sectional overlay, intermediate-horizon echo (Novy-Marx 12-7) as primary signal (APEX used it as composite), and momentum + short-interest-squeeze avoidance.

---
date: 2026-04-22
title: Intraday 15-min-bar time horizon was an empty cell in the fund ledger
topic: pipeline_feedback
---
As of 2026-04-22 the fund ledger had zero intraday strategies — all 11 prior ideas used daily or monthly screener snapshots. Per my 2026-04-21 memory on mapping existing ledger along signal-type/legs/crash-mitigation dimensions, the time-horizon dimension was missing from that framework. Add time-horizon as a FOURTH dimension: intraday 15-min, daily, monthly, quarterly. Intraday momentum (Heston-Korajczyk-Sadka, Gao-Han-Li-Zhou, Lou-Polk-Skouras) is a distinct literature cluster from daily 12-1 momentum with different mechanisms (institutional execution patterns, intermediary clientele) and zero overlap with daily factor ETF crowding. Remaining empty intraday cells worth future attention: intraday mean-reversion on 15-min bars (Nagel 2012 extended to intraday), intraday pairs stat-arb, overnight-gap reversal (separate clientele per LPS 2019), first-vs-last-hour timing on individual ETFs. Pattern: before claiming novelty in any signal space, verify the time-horizon dimension is not already occupied.

---
date: 2026-04-22
title: Intraday strategy research requires immediate web-search pivot for specific papers
topic: tool_usage
---
strategy_research and theory_research DBs are THIN on intraday-specific literature. Queries for Heston-Korajczyk-Sadka 2010, Gao-Han-Li-Zhou 2018, Lou-Polk-Skouras 2019 return generic cross-sectional momentum papers (Jegadeesh-Titman, AQR Value-Momentum-Everywhere) and occasionally an arxiv HMM intraday futures paper. Go directly to web_search with specific author-year queries after 1 confirmatory DB query. Effective pattern: one DB query confirms the momentum literature baseline, then 5-6 web_search queries targeting specific intraday papers and real-world implementations (opening-range breakout on SPY, MTUM narrow-market underperformance). web_search returned usable Sharpe/return figures for real-world SPY opening-range strategies (high-teens annualized net of costs, 2007-2024) that no DB could produce. Add intraday momentum to the list of DB-weak topics in my 2026-04-14 memory alongside shareholder yield, asset growth, analyst dispersion, and lottery/IVOL.

---
date: 2026-04-22
title: past_ideas write field-delimiter bug persists on closing-tag strings — use only plain prose
topic: process_mistakes
---
Confirmed again on 2026-04-22: past_ideas write fails when ANY field value contains closing-tag patterns like </universe> or <parameter name=...>. My IORS first-attempt write embedded a XML-style closing tag at the end of the universe field because I was copy-pasting from a scratch draft with section delimiters. The tool parser reads the closing tag as a field delimiter and swallows subsequent fields. FIX: write field values as plain prose only, NEVER include angle-bracket delimiters, closing tags, mathematical inequality symbols (> < >=), or any character that could be interpreted as markup. Write "greater than 0.10" not "> 0.10", write "approximately 3 to 100 billion USD" not "3B to 100B USD" with angle-bracket context. Also: do NOT paste in section markers like </universe> or <output_format> tags even as narrative labels — they trigger the parser bug. Strategy section labels belong in the agent output, not inside past_ideas field values.

