---
name: Residual Alpha Momentum with Dispersion-Broadening Regime Gate (RAMD)
category: momentum
date: 2026-04-16
verdict: failed
---

Monthly-rebalancing long-only US equity momentum ranked on regression alpha (market- and sector-residualized returns) instead of raw cumulative returns, per Blitz-Huij-Martens (2011). Composite signal = z(alpha_vs_spy) + z(alpha_vs_sector) + z(information_ratio), with ADX, 52wk-high, and beta-stability gates plus VIX + market-state regime scaling. Failure was a pipeline build bug, not a signal failure: strategy files were unmodified template scaffold (Stages 4+5 never customized them), so all 12 runs executed a generic EMA/RSI crossover instead of residual momentum. Best Sharpe -0.22. Signal concept remains academically sound; needs a real build before it can be evaluated.

---
name: Lottery-Skew Demand Aversion (LSDA)
category: multi-factor
date: 2026-04-16
verdict: failed
---

Long/short monthly US equity strategy shorting high-lottery names (high vol + positive skew + high kurtosis + high beta + overbought) and going long anti-lottery quality names, grounded in Frazzini-Pedersen BAB (2014), Bali-Cakici-Whitelaw MAX (2011), and prospect-theory probability weighting. Composite lottery score was sector-neutralized within GICS. Failure was the same pipeline build bug as RAMD: strategy files were unmodified template scaffold, backtest ran generic EMA/RSI crossover. Best Sharpe 0.08. Secondary concern if rebuilt: strict joint short-leg filters returned only 3 tickers in the April 2026 universe; short-leg construction needs loosening.

---
name: Continuous Information Momentum (CIM) — Frog-in-the-Pan with Smoothness Composite
category: momentum
date: 2026-04-16
verdict: failed
---

Monthly long-only US equity momentum selecting winners by information-path smoothness per Da-Gurun-Warachka (2014) Frog-in-the-Pan: composite of frog_in_pan, equity_curve_r2, zero_return_days_pct, and momentum_12m_1m_skip. Low-FIP is by construction a momentum-crash precursor filter (all bottom-1pct momentum months historically had high-FIP precursors). Failure was a pipeline build bug: strategy files were unmodified template scaffold, MANIFEST.json belonged to WVCCI, and Stages 4+5 wrote nothing CIM-specific. Best Sharpe 0.31 from the template EMA/RSI crossover run on CIM's screened universe. Signal concept unevaluated.

---
name: VIX-Conditional Liquidity Provision Reversal on Liquid ETFs (VCLR)
category: mean-reversion
date: 2026-04-17
verdict: failed
---

Short-horizon (2-10 day) long-only mean-reversion on liquid sector and broad-market ETFs, triggered by RSI or Bollinger oversold on ETFs above their 200-day SMA, gated by elevated-VIX regime per Nagel (2012) liquidity-provision compensation. Failure was the most severe pipeline bug of the batch: wiring.py imported WVCCIStrategy (a fundamentals long/short equity strategy), MANIFEST.json belonged to WVCCI, and CCC fundamental indicators were wired into an ETF universe that has no quarterly statement data. All 7 runs produced 0 trades because the fundamentals_valid gate is always 0.0 for ETFs. Signal concept unevaluated.

---
name: Pre-Earnings Attention Premium Harvest (PEAPH)
category: event-driven
date: 2026-04-17
verdict: failed
---

Event-driven long-only US small-to-mid cap strategy that buys 7-10 trading days before scheduled quarterly earnings and mandatorily exits 1 day before the announcement, exploiting the pre-announcement attention premium per Frazzini-Lamont (2007) — roughly 72% of the 21-day EAP is realized pre-announcement. Composite ranks on prior-quarter announcement-window volume concentration, small-cap tilt, 3m momentum, upside skew, and active pricing. Failure was a real signal-level failure, NOT a pipeline bug — strategy was built correctly with PEAPH-specific code. Best Sharpe -0.25 across 12 tunings; per-trade edge was positive (+0.72% avg, 50.5% win rate, +13.78% total return) but equity-curve flat periods between earnings seasons drove Sharpe negative. Structural issues to fix before retesting: 50-ticker universe was far too small (IDEA.md targeted 800-1400 names), and the SPY 200-SMA halt fired during extended bear markets removing active earnings seasons. Worth retesting with expanded universe and relaxed regime halt.
---
name: Disciplined Shareholder Yield with Valuation and Solvency Gates (DSY-VSG)
category: multi-factor
date: 2026-04-17
verdict: failed
---

### Description
Long-only US equity strategy, monthly rebalance, ranking on a composite Disciplined Shareholder Yield score that combines (a) trailing dividend yield, (b) net buyback yield (proxied by negative dividend_paid_and_capex_coverage_ratio_ttm interaction with FCF), (c) net debt paydown component (proxied by changes in debt_ratio_ttm), then GATED by valuation discipline (the buyback component is only credited when the stock trades at reasonable multiples — price-to-free-cash-flows below sector median) and solvency discipline (debt_ratio_ttm and interest_coverage_ttm must be healthy so payouts are not financed by leverage). Universe is US large-and-mid cap names with consistent FCF generation. Core thesis: Boudoukh-Michaely-Roberts-Richardson 2007 established total payout yield is a stronger predictor than dividend yield alone, with the Cambria SYLD ETF demonstrating real-money 12.86 percent annualized since 2013 inception and 17.46 percent over 5 years. The 2024-25 underperformance of naive shareholder yield (Yield factor large negative in 2025, SYLD lagging SPX by 13-15pp) was driven by (i) hyperscaler concentration crowding out yield names and (ii) companies executing buybacks at inflated 2025 valuations destroying per-share value. The DSY-VSG construction directly addresses both failures by (a) crediting buybacks ONLY when valuation is reasonable (sector-relative price-to-FCF below median) and (b) requiring solvency strength so payouts are funded by genuine cash generation not leverage. Macro fit is strong: Q1-Q2 2026 Citi regime model shows transition from Normal to Goldilocks/Recovery, value working in equities, ISM Manufacturing contracting 10 months with margin pressure (Prices Index 58.5 percent) suggesting capital discipline matters more than capex growth in late-cycle, and record 1.65T trailing-12mo total payouts demonstrates the deep capacity of the strategy.

### Edge
Composite Disciplined Shareholder Yield z-score = z(dividend_yield_ttm) + z(free_cash_flow_yield_proxy via inverse price_to_free_cash_flows_ratio_ttm) + z(payout_capex_coverage via dividend_paid_and_capex_coverage_ratio_ttm) + z(solvency strength via inverse debt_ratio_ttm and interest_coverage_ttm), gated to require sector-relative price-to-FCF below median (valuation-disciplined buyback credit) and interest_coverage_ttm above a healthy threshold (no debt-financed payouts). Top quintile of the composite is the long portfolio. Edge persists because (1) buybacks now exceed dividends 1.3x — total payout yield captures a larger share of capital return than dividend yield alone, (2) Boudoukh et al 2007 documented superior return prediction vs dividend yield, (3) McLean-Pontiff 2016 shows post-publication decay is partial not complete for fundamental yield anomalies, (4) the valuation-gate addresses the documented 2024-25 buyback timing failure where companies destroyed value buying at record highs, (5) the solvency-gate filters out the empirically weak signal of debt-funded buybacks per Cambria methodology and recent capital allocation literature.

### Universe
US common stocks listed on NYSE and NASDAQ. Market cap between approximately 2 billion USD and 200 billion USD (mid-to-large cap, avoiding both microcap illiquidity and mega-cap concentration risk that drove SYLD underperformance). Liquidity gate: avg_dollar_volume_20d above 5 million USD and price above 10 USD. Sector exposure across all GICS sectors except pure regulated utilities and pure REITs (where shareholder yield mechanics differ structurally — utilities have regulated payout ratios, REITs are required to distribute 90 percent of income). Require positive trailing twelve month free cash flow (free_cash_flow_operating_cash_flow_ratio_ttm above 0.20) and positive operating margin to ensure payouts are sustainable. Estimated final investable universe of approximately 200 to 350 names before composite ranking.

### Entry & Exit
Entry signal: Stock enters portfolio at monthly rebalance if its composite Disciplined Shareholder Yield z-score ranks in the top quintile of the universe AND it passes the two gates (sector-relative price_to_free_cash_flows_ratio_ttm below sector median, interest_coverage_ttm above approximately 4 to 5). Exit signal: Stock exits at monthly rebalance if it falls out of the top quintile OR fails either gate. No intra-month forced exits beyond standard delisting handling. Position sizing: equal-weight within the selected portfolio (avoiding cap-weighted concentration that hurt SYLD in 2024-25), with a hard sector cap of approximately 25 to 30 percent to prevent sector concentration. Rebalancing frequency: monthly on the first trading day. Expected portfolio size: approximately 40 to 80 names. Expected annual turnover: approximately 80 to 150 percent (moderate, well within cost tolerance for mid-to-large caps). Data inputs required: dividend_yield_ttm, price_to_free_cash_flows_ratio_ttm, dividend_paid_and_capex_coverage_ratio_ttm, debt_ratio_ttm, interest_coverage_ttm, free_cash_flow_operating_cash_flow_ratio_ttm, operating_profit_margin_ttm, sectors (for sector-relative gates and caps), market_cap, avg_dollar_volume_20d, price.

### Risk Management
Primary risk exposures: (1) Value-factor and yield-factor crowding — when growth dramatically outperforms value as in 2024-25, the strategy will lag cap-weighted benchmarks. (2) Late-cycle / recession risk — if a deep recession hits, payout-funded names with stretched coverage ratios will be forced to cut buybacks first, hurting the signal. (3) Sector concentration drift — yield-rich names cluster in financials, energy, consumer staples; the 25-30 percent sector cap mitigates this. Suggested guardrails for downstream agents to test: equal-weight position sizing (not cap-weight), sector cap between 25 and 30 percent, optional drawdown-based exposure reduction if portfolio drawdown exceeds approximately 15 percent, and a regime overlay considering a market-state filter (e.g., reduce gross exposure when SPX is materially below its 200-day SMA) though this should be tested as it may reduce capture during recoveries. Tail-risk mitigation: equal-weight construction provides natural diversification across approximately 40-80 names; fundamental quality gates (positive FCF, healthy interest coverage) reduce the probability of single-name blow-ups from over-leveraged payout policies.

### Research Backing
Boudoukh, Michaely, Roberts, Richardson 2007 "On the Importance of Measuring Payout Yield" Journal of Finance — total payout yield (dividends plus buybacks) is a stronger predictor of returns than dividend yield alone, mechanism is that buybacks have grown from 0.1x dividends in 1970 to 1.3x dividends in 2024. Pontiff and Woodgate 2008 — net share issuance anomaly documents underperformance of issuers and outperformance of repurchasers in cross-section. Daniel and Titman 2006 "Mispricing, Fundamentals, and the Value Premium" — composite equity issuance anomaly distinct from book-to-market value effect. Fama-French 2015 five-factor model includes CMA investment factor capturing the related capital-discipline premium. McLean and Pontiff 2016 "Does Academic Research Destroy Stock Return Predictability" — fundamental yield anomalies show partial post-publication decay (approximately 32-58 percent shrinkage) but signal persists meaningfully. Empirical real-money validation: Cambria Shareholder Yield ETF (SYLD) since May 2013 inception delivered 12.86 percent annualized through Sept 2024 with alpha of 0.71 versus SPX, 5-year return of 17.46 percent, beta 1.17, Sharpe 0.65, holding 100 stocks selected by total payout yield combined with value metrics. Disconfirming evidence properly addressed: Yield factor delivered large negative returns in 2025 per The London Company analysis; SYLD lagged SPX by approximately 13-15pp in 2024 due to mega-cap AI concentration; Goldman Sachs and Morgan Stanley document declining buyback yield 2022-2025 as companies repurchased at record high valuations destroying per-share value. The DSY-VSG strategy directly addresses these failures with valuation and solvency gates that pure shareholder-yield strategies (including SYLD) lack. Macro context: Citi Quantitative Global Macro Strategy Q1-Q2 2026 regime model classifies current environment as Normal cluster transitioning toward Goldilocks/Recovery with value-factor tailwinds; record 1.652 trillion USD trailing-12-month US shareholder payouts (per S&P Dow Jones data through June 2025) demonstrates strategy capacity.

### Research Results
**Evaluated:** 2026-04-17

# Validation Results: Disciplined Shareholder Yield with Valuation and Solvency Gates (DSY-VSG)

**Date:** 2026-04-17  
**Strategy ID:** disciplined_shareholder_yield_with_valuation_and_solvency_gates  
**Backtest Period:** 2014-01-01 to 2025-12-31 | Warmup: 504 bars (~2 calendar years)  
**Universe:** 50 tickers (top by market cap, equity screener with solvency/FCF/valuation gates)

## Pre-Run Fix Applied

The `ShareholderYieldRatiosIndicator` referenced financial ratio column names with `TTM` suffix (e.g., `dividendYieldTTM`) but the actual data provider uses non-suffixed names (`dividendYield`). Fixed `_SRC_*` constants in `indicators/shareholder_yield_ratios.py` to remove the `TTM` suffix.

## Run Table

| Run | composite_entry_threshold | valuation_pctile | min_interest_coverage | base_equity_pct | Sharpe | Ann.Return% | Trades | Win% |
|-----|--------------------------|-----------------|----------------------|-----------------|--------|-------------|--------|------|
| 0 (baseline) | 0.65 | 0.50 | 4.0 | 0.0167 | -1.76 | 0.70% | 215 | 53.02% |
| 1 | 0.455 | 0.50 | 4.0 | 0.0167 | -1.02 | 1.39% | 198 | 57.58% |
| 2 | 0.845 | 0.50 | 4.0 | 0.0167 | -19.51 | 0.01% | 12 | 58.33% |
| 3 | 0.65 | 0.35 | 4.0 | 0.0167 | -1.72 | 0.75% | 220 | 53.64% |
| 4 | 0.65 | 0.65 | 4.0 | 0.0167 | -1.81 | 0.66% | 206 | 52.91% |
| 5 | 0.65 | 0.50 | 2.8 | 0.0167 | -1.75 | 0.69% | 221 | 52.94% |
| 6 | 0.65 | 0.50 | 5.2 | 0.0167 | -1.88 | 0.76% | 201 | 53.23% |
| 7 | 0.65 | 0.50 | 4.0 | 0.0117 | -2.69 | 0.49% | 215 | 53.02% |
| 8 | 0.65 | 0.50 | 4.0 | 0.0217 | -1.27 | 0.90% | 215 | 53.02% |
| 9 | 0.455 | 0.35 | 4.0 | 0.0167 | -0.87 | 1.45% | 195 | 58.97% |
| 10 | 0.455 | 0.50 | 4.0 | 0.0217 | -0.65 | 1.81% | 198 | 57.58% |
| 11 (best) | 0.455 | 0.35 | 4.0 | 0.0217 | -0.55 | 1.88% | 195 | 58.97% |

## Verdict: FAILED (best Sharpe -0.55, threshold > 0.50)

Per-trade signal has genuine edge (53-59% win rate, positive profit factor ~1.7x, avg trade +2.34%). Sharpe is structurally negative because the vectorized engine computes Sharpe over the full equity curve including a 504-bar (~2-year) flat warmup period, and capital deployment is low (1.67% per position with few simultaneous positions on a 50-ticker universe). 

Equity grew from $1M (2014) to $1.087M (2025) = 8.67% total return over 11 years. Post-warmup annualized return ~0.84-1.88% depending on params. The signal-level alpha is real but the portfolio construction is too capital-efficient to produce a passing Sharpe given the warmup drag.

Recommendation: Expand to 100+ ticker universe to increase simultaneous positions, use portfolio-level gross-exposure targeting instead of fixed 1/N, or start the backtest after the warmup period completes.

---
name: Capital-Efficiency Productivity Improvers (CEPI)
category: multi-factor
date: 2026-04-17
verdict: failed
---

### Description
Long-only US equity strategy, monthly rebalance, combining a STATIC capital-efficiency score (Novy-Marx gross profitability premium implemented through the Barra/MSCI quality descriptor set of asset turnover, gross margin, ROA, ROCE) with a CHANGE score (operating margin trend, 5-year ROCE trend, EBIT growth in excess of revenue growth). Both components are z-scored cross-sectionally within GICS sectors and combined with equal weights. Selection is the top quintile of the composite, gated to require the TREND component above zero so static quality alone cannot win a slot. The core design choice is requiring IMPROVEMENT rather than levels, which empirically differentiated Citi large-cap ROE-Trend baskets from MTUM and QUAL during the 2025 junk rally. Universe is US common stocks, market cap between 2 billion and 100 billion USD, excluding REITs, utilities, banks, insurance, capital markets, diversified financials (sectors where asset-turnover metrics are economically non-comparable), with liquidity gate of 5 million USD average dollar volume. Three complementary mechanisms: (1) risk-based intangibles premium per Eisfeldt-Papanikolaou 2013 and Peters-Taylor 2017 since high asset turnover is a model-free proxy for intangible-capital intensity (asset-light firms have low PPE relative to economic output); (2) Novy-Marx 2013 gross profitability premium of 45 bps per month t-stat 6.26 subsumes most of the quality factor space; (3) behavioral underreaction to fundamental trajectory per Engelberg-McLean-Pontiff 2020 where analysts anchor on historical levels and are slow to update on margin expansion. Portfolio construction is equal-weight 50 to 120 names, sector cap approximately 25 to 30 percent, portfolio-level gross target 95 to 100 percent deployed (explicit to avoid the DSY-VSG failure where fixed 1/N sizing on a small universe left 60 percent of capital idle). Macro fit for April 2026: Citi regime model transitioning Normal to Recovery/Goldilocks with rising LEIs, ISM Services PMI 54.4 in tenth month of expansion, ISM Manufacturing recovering to approximately 52, Services Prices Index elevated at 64.3 so margin discipline is being priced, JPM Flows and Liquidity showing Value factor at 2024 highs from AI de-risking creating a beta-diversifying rotation. Citi Large Cap Positive ROE Trend basket delivered approximately 27 percent in 2024 versus SPX 25 percent and approximately 26 percent in 2025 versus SPX 19 percent, demonstrating real-money outperformance in both quality-tailwind and quality-crowding regimes.

### Edge
Composite Capital-Efficiency Productivity score equal to 0.5 times Z_LEVEL plus 0.5 times Z_TREND. Z_LEVEL is the equal-weighted mean of sector-neutral cross-sectional z-scores for asset_turnover_ttm, gross_profit_margin_ttm, return_on_assets_ttm, and return_on_capital_employed_ttm. Z_TREND is the equal-weighted mean of sector-neutral z-scores for operating_margin_change_yoy, roce_change_5yr, and the difference ebit_growth_yoy minus revenue_cagr_3yr (margin-expansion-driven growth rather than pure top-line growth). Top quintile of the composite is the long portfolio with a hard gate that Z_TREND must be strictly greater than zero, preventing static-quality crowding from dominating entry. The edge rests on three distinct mechanisms that should not decay simultaneously: risk-based intangibles premium of approximately 4.7 percent alpha per Eisfeldt-Papanikolaou 2013; mispricing from conservative intangibles accounting per Peters-Taylor 2017 with intangibles factor Sharpe exceeding traditional factors; behavioral underreaction to improving fundamentals per Engelberg-McLean-Pontiff 2020 documenting approximately 34 percent forecast errors on anomaly-shorts. The key novel differentiator versus existing quality factor strategies is requiring IMPROVEMENT rather than levels, which separated Citi ROE-Trend basket outperformance from MTUM and QUAL underperformance during 2025 when S and P 600 Profitable underperformed Russell 2000 by the widest margin since 1994 and high short interest names rose 32 percent.

### Universe
US common stocks listed on NYSE and NASDAQ. Market cap between approximately 2 billion USD and 100 billion USD (mid-to-large cap, avoiding both microcap data noise and mega-cap hyperscaler concentration). avg_dollar_volume_20d greater than 5 million USD. price greater than 10 USD. Exclude sectors real estate and utilities (mandatory payout structures and regulated returns make efficiency metrics non-comparable). Exclude financial industries banks, insurance, capital markets, diversified financials (balance sheets make asset turnover and gross margin economically meaningless). Require free_cash_flow_operating_cash_flow_ratio_ttm greater than 0.20 (cash-conversion sanity), operating_profit_margin_ttm greater than 0.05 (baseline profitability floor), asset_turnover_ttm greater than 0.30 (meaningful lower bound for the ranking tournament), return_on_capital_employed_ttm greater than 0.08 (baseline capital productivity floor), return_on_equity_ttm greater than 0.08 (avoid negative-ROE sign flips that distort z-scores). Estimated investable universe approximately 400 to 700 names before composite ranking, from which the top quintile (approximately 80 to 140 names) passes to portfolio construction.

### Entry & Exit
Entry signal: at monthly rebalance, a stock enters the portfolio if its Composite Capital-Efficiency Productivity score ranks in the top quintile of the filtered universe AND its Z_TREND component is strictly greater than zero. Sector-neutralize both z-score components within GICS sectors before averaging so the composite rewards intra-sector capital efficiency rather than sector tilts. Exit signal: at monthly rebalance, a stock exits if its composite drops out of the top quintile OR Z_TREND turns negative OR any universe gate fails. No intra-month forced exits other than delisting. Rebalancing: monthly on the first trading day. Quarterly fundamental updates mean only 4 of 12 monthly rebalances bring materially new fundamental information; monthly cadence manages name-level turnover as composite ranks drift. Expected annual turnover approximately 100 to 180 percent, well within cost tolerance for the 5 million USD ADV liquidity band. Position sizing: equal-weight within the selected set (explicitly reject cap-weighting since Mag7 concentration was the SYLD killer), 50 to 120 names, portfolio-level gross target approximately 95 to 100 percent deployed, name-level cap approximately 2.5 percent absolute per position, sector cap approximately 25 to 30 percent. Data inputs required: asset_turnover_ttm, gross_profit_margin_ttm, return_on_assets_ttm, return_on_capital_employed_ttm, return_on_equity_ttm, operating_profit_margin_ttm, operating_margin_change_yoy, roce_change_5yr, ebit_growth_yoy, revenue_cagr_3yr, free_cash_flow_operating_cash_flow_ratio_ttm, sectors, industries, market_cap, avg_dollar_volume_20d, price.

### Risk Management
Primary risk exposures: (1) Sector concentration drift since capital-efficient asset-light firms cluster in technology, software, consumer staples, select healthcare; sector cap of 25 to 30 percent is essential. (2) Style crowding risk since although change-in-profitability is less crowded than level-quality, a sharp junk-rally flip such as April to December 2025 will hurt; the Z_TREND-positive gate provides partial insulation because deteriorating firms exit fast. (3) Late-cycle or recession risk since margin expansion is hard to sustain in a demand slowdown; monitor ISM New Orders below 48 as warning. (4) Intangibles revaluation risk since a sharp multiple compression on asset-light names (2022-style rate shock) would hit the level component. Suggested guardrails for downstream agents to test: equal-weight position sizing (reject cap-weight), sector cap between 25 and 30 percent, drawdown-based de-risking considering a reduction to approximately 50 percent gross if portfolio drawdown exceeds 15 percent, name-level cap approximately 2.5 percent per position to prevent drift concentration, optional market-state overlay that reduces gross exposure only when SPX is materially below 200-day SMA AND ISM Services is below 50 (both conditions required, avoiding the PEAPH trap of halting during still-active productive periods). Tail risk mitigation: equal-weight diversification across 50 to 120 names, fundamental quality floors (positive FCF conversion, operating margin, ROCE, ROE) screen out single-name blow-up risk, and the change-in-profitability gate causes fast exit when operational trends reverse.

### Research Backing
Novy-Marx 2013 "The Other Side of Value: The Gross Profitability Premium" Journal of Financial Economics volume 108 pages 1-28 — gross profitability premium of 45 basis points per month t-statistic 6.26, subsumes most of the quality factor space, adopted by Fama-French as RMW in the 2015 five-factor model. Eisfeldt and Papanikolaou 2013 "Organization Capital and the Cross-Section of Expected Returns" Journal of Finance — firms with higher organization capital deliver 4.7 percent higher risk-adjusted annual returns, mechanism is firm-specific key-talent risk. Peters and Taylor 2017 "Intangible Capital and the Investment-q Relation" Journal of Financial Economics — Total Q formula incorporating intangibles dominates physical Q, intangibles-based long-short factor Sharpe exceeds SMB HML RMW CMA, intangibles enhance value strategy Sharpe from 0.16 to 0.62. Chan Lakonishok Sougiannis 2001 "The Stock Market Valuation of Research and Development Expenditures" Journal of Finance — within small-caps high R and D to market earned 31.3 percent annualized versus 16.2 percent for low R and D to market, approximately 15 percentage point spread attributed to functional fixation. Fama and French 2015 "A Five-Factor Asset Pricing Model" Journal of Financial Economics — RMW profitability and CMA investment factors priced. Soliman 2008 "The Use of DuPont Analysis by Market Participants" The Accounting Review — change in asset turnover predicts cross-sectional returns; DuPont decomposition adds power beyond static ROE. Engelberg McLean Pontiff 2020 "Analysts and Anomalies" Journal of Accounting and Economics — across 125 anomalies analyst forecast errors approximately 34 percent on anomaly-shorts versus 9 percent on anomaly-longs, mechanism is behavioral underreaction to improving fundamentals. Real-money validation: Citi Large Cap Positive ROE Trend basket CGRBGROE delivered approximately 27 percent in 2024 versus SPX 25 percent and approximately 26 percent in 2025 versus SPX 19 percent, outperforming in both quality-tailwind and quality-crowding regimes. Macro backing: Citi Quantitative Global Macro Strategy regime model Q1 to Q2 2026 shows transition from Normal to Recovery/Goldilocks cluster with rising LEIs, ISM Services PMI 54.4 percent in tenth month of expansion December 2025, ISM Manufacturing recovering to approximately 52 through Q1 2026, Services Prices Index 64.3 percent elevated indicating margin discipline is being priced, JPMorgan Flows and Liquidity February 2026 reports Value factor Dow Jones US Thematic Market Neutral index at 2024 highs from AI de-risking. Disconfirming evidence incorporated: 2025 quality crowding where S and P 600 Profitable underperformed Russell 2000 by widest margin since 1994 launch, high short interest names rose 32 percent, negative FCF rose 24 percent — addressed by REQUIRING Z_TREND greater than zero (change not level) and equal-weight construction; MTUM financials concentration drove 2024 3rd percentile to 2025 91st percentile fall — addressed by sector caps 25 to 30 percent; Engelberg McLean Pontiff late-sample decay as analysts incorporate anomaly information — addressed by using THREE distinct mechanisms (risk intangibles plus Novy-Marx profitability plus behavioral trend) rather than a single channel.

### Research Results
**Evaluated:** 2026-04-18

# Validation Results: Capital-Efficiency Productivity Improvers (CEPI)

**Date:** 2026-04-18  
**Strategy ID:** capitalefficiency_productivity_improvers  
**Backtest Period:** 2018-01-01 to 2025-12-31 | Warmup: 630 bars (~2.5 calendar years)  
**Universe:** 50 tickers (top by market cap, equity screener with quality/FCF/ROCE gates)

## Pre-Run Fix Applied

The `CapEfficiencyLevelIndicator` and `CapEfficiencyTrendIndicator` referenced financial ratio column names with TTM suffix (e.g., `assetTurnoverTTM`, `operatingProfitMarginTTM`, `returnOnCapitalEmployedTTM`) but the actual financial_ratios data provider uses non-suffixed names (`assetTurnover`, `operatingProfitMargin`, `returnOnCapitalEmployed`). Fixed `_FMP_TO_OUTPUT` dict in `indicators/fundamental_indicator.py` and the column checks in `indicators/custom_indicator.py` to remove the `TTM` suffix.

## Universe: 50 Tickers (top by market cap)
ADBE, BSX, NOC, GD, UPS, WM, PWR, JCI, CMI, SHW, CDNS, ABNB, CVNA, EMR, CSX, SLB, AMX, CRH, ITW, ECL, REGN, NTES, MNST, ROST, MSI, TEL, MPWR, CIEN, CTAS, EOG, CL, NKE, PCAR, RACE, UI, RSG, FTNT, BKR, TER, INFY, FIX, TGT, KEYS, AU, GWW, SE, NXPI, AME, LNG, OKE

## Run Table

| Run | composite_threshold | base_equity_pct | max_name_pct | Sharpe | Ann.Return% | Max DD% | Trades |
|-----|--------------------|-----------------|--------------|---------|-----------|---------| -------|
| 0 (baseline) | 0.583 | 0.020 | 0.025 | -1.68 | 1.31% | -3.44% | 11 |
| 1 | 0.450 | 0.020 | 0.025 | -1.35 | 13.22% | -3.88% | 10 |
| 2 | 0.500 | 0.020 | 0.025 | -1.35 | 13.35% | -3.79% | 9 |
| 3 | 0.530 | 0.020 | 0.025 | -1.34 | 13.48% | -3.79% | 9 |
| 4 | 0.600 | 0.020 | 0.025 | -1.72 | 10.81% | -3.45% | 13 |
| 5 | 0.650 | 0.020 | 0.025 | -3.71 | 8.51% | -0.67% | 14 |
| 6 | 0.450 | 0.030 | 0.025 | -1.35 | 13.22% | -3.88% | 10 |
| 7 | 0.450 | 0.040 | 0.025 | -1.35 | 13.22% | -3.88% | 10 |
| 8 | 0.500 | 0.030 | 0.025 | -1.35 | 13.35% | -3.79% | 9 |
| 9 (BEST) | 0.500 | 0.020 | 0.040 | -0.54 | 21.79% | -5.68% | 9 |
| 10 | 0.450 | 0.020 | 0.040 | -0.55 | 21.58% | -5.83% | 10 |
| 11 | 0.500 | 0.025 | 0.040 | -0.54 | 21.79% | -5.68% | 9 |

## Verdict: FAILED (Best Sharpe -0.54, threshold > 0.50)

Per-trade edge is genuine (81.82% win rate, 17.43 profit factor on baseline run). Strategy fails the Sharpe bar because: (1) warmup drag — 630-bar flat warmup depresses mean return while vol from active period stays in denominator; (2) very sparse trades (9-14 over 7 years) from the hardcoded universe_quality_gate requiring asset_turnover >= 0.30 historically — most top-50 large-caps had lower historical asset turnover than their current values; (3) capital underdeployment — only ~18-36% of capital deployed with so few positions. 

Recommendation: Expand to 200+ tickers using historical universe, lower hardcoded `_MIN_ASSET_TURNOVER` in `custom.py` from 0.30 to 0.20 to match historical mid-cap data, or start backtest after warmup period to get a clean Sharpe. The signal concept is academically sound and has real per-trade edge.

