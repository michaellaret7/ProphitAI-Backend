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

Long-only monthly-rebalancing US equity strategy ranking on composite Disciplined Shareholder Yield = z(dividend_yield) + z(FCF yield via inverse P/FCF) + z(payout-capex coverage) + z(solvency strength), gated by sector-relative P/FCF below median and healthy interest coverage, per Boudoukh-Michaely-Roberts-Richardson (2007) total-payout-yield anomaly. The valuation and solvency gates were explicitly designed to fix SYLD's 2024-25 underperformance by only crediting buybacks at reasonable valuations and requiring FCF-funded rather than debt-funded payouts. Failure was a real signal-level failure layered on a portfolio-construction bug: per-trade edge is genuine (53-59% win rate, profit factor ~1.7x, avg trade +2.34%) but best Sharpe -0.55 because the vectorized engine dragged a 504-bar flat warmup into the Sharpe denominator while sizing deployed only 1.67% per position on a 50-ticker universe, and equity grew just 8.67% over 11 years. Structural issue: capital underdeployment on an undersized universe. Worth retesting with 100+ ticker universe, portfolio-level gross-exposure targeting instead of fixed 1/N, and backtest starting after warmup.

---
name: Capital-Efficiency Productivity Improvers (CEPI)
category: multi-factor
date: 2026-04-17
verdict: failed
---

Long-only monthly-rebalancing US equity strategy with composite 0.5*Z_LEVEL + 0.5*Z_TREND on sector-neutralized capital-efficiency metrics (asset turnover, gross margin, ROA, ROCE for level; operating-margin trend, 5y ROCE trend, EBIT-minus-revenue growth for trend), with a hard gate that Z_TREND>0, per Novy-Marx (2013) gross-profitability premium combined with Engelberg-McLean-Pontiff (2020) analyst trend-underreaction. The key differentiator versus MTUM/QUAL was requiring IMPROVEMENT rather than levels to avoid static-quality crowding. Failure was a real signal-level result on a constrained pipeline: per-trade edge is strong (81.82% win rate, 17.43 profit factor on baseline) but best Sharpe -0.54 from three compounding structural issues — 630-bar (~2.5yr) flat warmup in the Sharpe denominator, a hardcoded asset_turnover>=0.30 universe gate that historically excluded most top-50 large caps producing only 9-14 trades over 7 years, and only ~18-36% capital deployed on a 50-ticker universe. Worth retesting with 200+ historical tickers, lowered _MIN_ASSET_TURNOVER (0.30→0.20), and post-warmup Sharpe measurement.

---
name: Dispersion-Regime Residual Reversal on Liquid US Equities (DR3)
category: mean-reversion
date: 2026-04-20
verdict: pending
---

Long-only monthly-rebalancing cross-sectional residual reversal on liquid US mid-to-large-cap equities (2-150B USD market cap), ranking the top quintile of residual LOSERS on composite -[z(alpha_vs_spy) + z(alpha_vs_sector) + z(information_ratio)] per Da-Liu-Schaumburg (2014) with Nagel (2012) liquidity-provision mechanism. Novel design element is a dispersion regime gate that scales gross exposure from zero (below 40th pctile of 252-day trailing cross-sectional dispersion) to full (above 60th pctile), plus autocorrelation_1d<0 reversal-propensity filter and mandatory 5-day pre-earnings exit. Strict 10M USD ADV liquidity gate is required because expected 200-350% annual turnover makes short-term reversal among the most cost-sensitive factors per Khandani-Lo (2011). Positioned as structurally orthogonal to RAMD (opposite sign and horizon: residual LOSERS, 1-3mo, vs residual WINNERS, 12-1mo). Not yet evaluated.

---
name: Panic-Scaled Long-Short Momentum with Distress-Filtered Short Leg (PSMO)
category: momentum
date: 2026-04-20
verdict: failed
---

Long/short monthly-rebalancing US mid-to-large-cap momentum on Jegadeesh-Titman 12-1 with two structural innovations: (a) distress-filtered short leg (no top-sector-decile debt_ratio, interest_coverage>~3, cash_ratio>~0.3) to avoid the Merton-written-call loser setup that drives momentum crashes per Daniel-Moskowitz (2016), and (b) a Daniel-Moskowitz panic-state gross scaler combining trailing 24mo SPX bear-indicator with 126d realized variance, targeting 150-180% gross in calm regimes and scaling to zero in severe panic. Failure was driven by three concurrent pipeline failures that crippled the intended architecture rather than any signal-level problem: financial_ratios data was missing for all 50 tickers so distress_filter_pass=0 meant the short leg produced 0 trades across 18 years (run-2 without the distress filter confirmed the design intent — naive deep-loser shorts delivered Sharpe -0.31), the SPY equity_price provider was unregistered so panic_state_gate defaulted to 1.0 with no dynamic scaling functional, and max_name_pct=2.5% with ~20 simultaneous positions yielded only ~50% gross versus the intended 150-180%. Best Sharpe 0.44 (run #11 at max_name_pct=0.06, still long-only and warmup-dragged); per-trade edge is genuine (58% win rate, 2.4x profit factor). Structural issues: financial_ratios pipeline gap and SPY data registration. Worth retesting after those data-pipeline fixes.

---
name: Anchor-Proximity Echo Momentum with Quality-Trend Asymmetric Legs (APEX)
category: momentum
date: 2026-04-20
verdict: failed
---

Long/short monthly-rebalancing US mid-to-large-cap momentum composite on George-Hwang (2004) proximity-to-52-week-high + Novy-Marx (2012) 12-7 echo + fundamental-trend (operating_margin_change_yoy, roce_change_5yr), with an asymmetric short leg targeting "quiet-decay" names (intermediate equity_curve_r2, no-distress gate, bottom echo-composite) to explicitly avoid the Merton-written-call zone that drove the 1932 and 2009 momentum crashes per Daniel-Moskowitz (2016), and a Barroso-Santa-Clara (2015) constant-vol overlay targeting ~12% annualized portfolio vol. Designed to replace the PSMO SPX-state scaler (which tripped on unregistered SPY data) with a portfolio-own-return vol overlay. Per-trade edge is genuinely positive (profit factor 1.36, win rate 48.86%, avg trade +1.39%, with both legs firing — 132 longs and 87 shorts over 21 years) but best Sharpe -2.54 driven by measurement methodology, not signal absence: a 650-bar (~2.5yr) warmup flat-period in the Sharpe denominator combined with only ~50% peak capital deployment on a 50-ticker universe when the strategy was designed for 500-800 names. Structural issues: undersized universe and warmup-inclusive Sharpe computation. Worth retesting with 150+ tickers, post-warmup Sharpe measurement, and raised target_gross_pct.
---
name: Fundamental Momentum Long-Short with Twin-Deterioration Short Leg (FMLS-TD)
category: momentum
date: 2026-04-21
verdict: pending
---

### Description
Long-short monthly-rebalancing US mid-to-large-cap equity strategy ranking on a realized fundamental-trend composite rather than price momentum. Long leg targets the top quintile of improving operators (rising EBIT growth, expanding operating margin, rising ROCE, accelerating revenue); short leg targets the bottom quintile of twin-deteriorators (falling operating margin AND contracting revenue AND falling ROCE). Signal is native to the equity screener via operating_margin_change_yoy, roce_change_5yr, ebit_growth_yoy, revenue_cagr_3yr, eps_growth_yoy, fcf_growth_yoy — no external market-state data required, no raw OHLC regression, no SPY dependency. Grounded in Novy-Marx (2014) fundamental-momentum-subsumes-price-momentum, Chan-Jegadeesh-Lakonishok (1996) SUE earnings momentum, and Engelberg-McLean-Pontiff (2018) biased-expectations mechanism. Structurally distinct from all three prior momentum failures (RAMD residual price, PSMO raw 12-1 price, APEX 52wk-high proximity) because the signal is a fundamental delta rather than any price function. Current April 2026 regime (broadening EPS growth, SPX dispersion at 97th percentile per Goldman, Fed easing into Goldilocks cluster per quant macro) is maximally favorable for cross-sectional fundamental ranking. Risk overlay is a Barroso-Santa-Clara constant-vol scaler on portfolio-own returns (no external data) with a sector-concentration cap. Short leg avoids Merton-written-call distressed zone by requiring healthy-balance-sheet deteriorators (cash ratio above median, interest coverage above approximately 3) so shorts are slow-melt quality decliners, not deep-distressed levered losers.

### Edge
Realized fundamental-trend deltas (operating margin change, ROCE change, EBIT growth yoy, revenue growth) rank stocks on analyst/investor underreaction to the rate of change of operating performance. Per Novy-Marx 2014, earnings-announcement CAR held 12 months subsumes most of the cross-sectional price-momentum alpha, demonstrating that fundamental trend is the true underlying driver. Per CJL 1996, SUE-based long-short earnings momentum delivered roughly 8 percent per quarter gross (approximately 32 percent annualized) with t-stat exceeding 4 in US equities. Per EMP 2018, anomaly mispricing concentrates around information events and short legs are characterized by excessively optimistic forecasts. The twin-deterioration short-leg construction (requiring BOTH revenue and margin to contract, following Jegadeesh-Livnat 2006 revenue-concordance logic which roughly doubles PEAD drift versus SUE alone) isolates slow-fading quality declines rather than price-momentum losers — orthogonal to the Merton 1974 option-like behavior of leveraged distressed losers that drove every major momentum crash per Daniel-Moskowitz 2016. Because the signal is computed from fundamentals not price, it cannot be front-run by price-momentum crowding and is less arbitraged than raw 12-1 (the signal requires assembling a multi-column TTM-change composite rather than just trailing price returns).

### Universe
US common equity. Market cap between 3 billion USD and 100 billion USD (mid-to-large-cap focus; avoids microcap fundamental-data-gap issues and mega-cap near-zero-alpha crowding per Subrahmanyam 2024). Average 20-day dollar volume greater than 10 million USD (strict liquidity gate because monthly rebalance and long-short doubles effective turnover). Price greater than 5 USD. Exclude financials and REITs (GICS Financials and Real Estate sectors — fundamentals-trend metrics are non-comparable because banks mark loans and REITs capitalize rent differently). Require non-null fundamental trend columns (operating_margin_change_yoy, ebit_growth_yoy, revenue_cagr_3yr, roce_change_5yr, eps_growth_yoy, fcf_growth_yoy) — eliminates IPOs under 3 years old and stale-data stocks. Target universe size is approximately 300 to 600 names pre-signal-ranking.

### Entry & Exit
Monthly rebalance on first trading day of month. Signal construction: Long composite = z(operating_margin_change_yoy) + z(ebit_growth_yoy) + z(roce_change_5yr) + z(revenue_cagr_3yr) + z(eps_growth_yoy) + z(fcf_growth_yoy), all sector-neutralized within GICS sector before ranking. Long entry: top quintile of long composite AND positive revenue_cagr_3yr (concordance gate — margins expanding on growing revenue, not on shrinking revenue). Short composite = negative of long composite PLUS twin-deterioration gate (revenue_cagr_3yr less than zero AND operating_margin_change_yoy less than zero). Short entry: bottom quintile of short composite AND healthy-balance-sheet gate (cash_ratio_ttm above sector median AND interest_coverage_ttm greater than approximately 3) to avoid shorting already-distressed Merton-zone losers. Exit triggers: (a) scheduled monthly rebalance — name drops out of quintile, (b) position loss exceeds approximately 3 ATR on short leg to cap short-squeeze tail, (c) pre-earnings flat — close 2 trading days before announcement and re-enter day after (eliminates gap risk, separates this from a PEAD strategy). Rebalancing cadence monthly; expected annualized gross turnover approximately 400 to 600 percent (200 to 300 percent per leg).

### Risk Management
Portfolio sizing: equal-weight within each leg with a per-name cap around 2 percent of gross. Gross exposure targeted via Barroso-Santa-Clara constant-vol overlay — scale gross exposure inversely to trailing 126-day realized portfolio volatility, targeting roughly 12 percent annualized ex-ante portfolio vol, with gross capped around 180 percent (90/90 long/short) and floored around 40 percent. Vol overlay uses portfolio-own returns only, no SPY or macro series dependency (the failure mode of PSMO). Sector concentration cap: maximum approximately 25 to 30 percent gross per GICS sector on each leg. Drawdown guardrail: if trailing 60-day portfolio return falls below approximately negative 10 percent, halve gross for 20 trading days before restoring. Short-leg-specific: borrow cost filter — exclude names with hard-to-borrow flags or implied borrow cost above roughly 200 basis points annualized (avoids the crowded-short cost drag that hurt many 2020-2021 short books). Primary tail risks to monitor: (1) earnings-season clustered reversal days when many longs and shorts report concurrently — partially mitigated by pre-earnings flat rule, (2) sector-wide margin-shock events (tariff surprises, wage re-acceleration) that invalidate cross-sectional margin ranking — mitigated by sector-neutral ranking construction, (3) momentum-crash-style rebound of distressed shorts in bear-market recoveries — mitigated by healthy-balance-sheet gate on short leg.

### Research Backing
Novy-Marx, R. (2014/2015) "Fundamentally, Momentum is Fundamental Momentum" NBER WP 20984 — 3-day CAR around earnings announcements held 12 months explains a large portion of cross-sectional price-momentum alpha; fundamental-news signal dominates price signal in spanning tests. Chan, L., Jegadeesh, N., Lakonishok, J. (1996) "Momentum Strategies" Journal of Finance 51(5): 1681-1713 — SUE-based long-short earnings momentum delivered approximately 8 percent per quarter in US equities. Jegadeesh, N. and Livnat, J. (2006) "Revenue Surprises and Stock Returns" Journal of Accounting and Economics 41(1-2): 147-171 — revenue concordance roughly doubles PEAD drift magnitude versus SUE alone. Engelberg, J., McLean, D., Pontiff, J. (2018) "Anomalies and News" Journal of Finance 73(5): 1971-2001 — anomaly returns concentrate around earnings announcements and short legs feature excessively optimistic consensus forecasts. Daniel, K. and Moskowitz, T. (2016) "Momentum Crashes" Journal of Financial Economics 122(2): 221-247 — crash mechanism is Merton-1974 option-like behavior of leveraged distressed losers in bear-market rebounds; avoidable by excluding distressed balance sheets from short leg. Barroso, P. and Santa-Clara, P. (2015) "Momentum Has Its Moments" Journal of Financial Economics 116(1): 111-120 — constant-vol overlay on portfolio-own 126-day realized vol nearly doubles momentum Sharpe and cuts kurtosis from 18.24 to 2.68 without increasing turnover materially. Current April 2026 macro regime snapshot: Columbia Threadneedle 2025-26 outlook documents EPS growth broadening across sectors and regions; Citi Thematic Equity Strategy confirms Positive ROE Trend basket persistently outperforms Negative ROE Trend basket across 2025-26 factor rotations; Goldman Sachs Flows Desk 1/21/26 reports SPX single-stock dispersion at 97th percentile on 4-year lookback (peak stock-picker regime); JPMorgan 1/23/26 reports Q4'25 consensus 9 percent EPS growth and 15 percent 2026 guidance; Quantitative Global Macro Strategy regime model places current economy in Normal cluster transitioning toward Recovery and Goldilocks — historically the strongest cross-sectional fundamental-dispersion regime.

