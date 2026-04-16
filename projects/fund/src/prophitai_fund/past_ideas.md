---
name: Residual Alpha Momentum with Dispersion-Broadening Regime Gate (RAMD)
category: momentum
date: 2026-04-16
verdict: failed
---

### Description
A monthly-rebalancing, long-only (optional long/short variant) US equity momentum strategy that ranks stocks on their REGRESSION ALPHAS against both the market (SPY) and their sector — i.e., a composite idiosyncratic/residual return — instead of their raw cumulative returns. This is a direct, screener-native implementation of the Blitz-Huij-Martens (2011) residual momentum anomaly, which has delivered Sharpe ~0.96 and t-stats >20 out-of-sample, and which by construction avoids the Daniel-Moskowitz momentum crash mechanism (past-loser conditional beta blow-ups in rebound markets). The strategy is explicitly designed for the April 2026 regime where: (a) raw momentum has just suffered a -31.8% drawdown (Sep 2024–Apr 2025) as AI-concentrated leaders whipsawed; (b) market breadth is broadening (65% of S&P 500 outperforming = 97th percentile); (c) capital is rotating away from the narrow mega-cap monolith toward cyclicals; (d) cross-sectional single-stock dispersion is at its 97th percentile (Goldman Jan 2026) — the maximum stock-picking alpha environment. Raw-momentum vehicles like MTUM hold ~40% TMT and are structurally crowded into the crowded trade; residual momentum, by construction, is SECTOR- and MARKET-neutral and captures firm-specific price momentum AFTER stripping out those exposures, precisely the idiosyncratic alpha that dispersion-broadening regimes reward. The core signal = composite z-score of alpha_vs_spy (market-residual) and alpha_vs_sector (sector-residual), confirmed by information_ratio (alpha/vol = risk-adjusted residual) and risk_adj_momentum (Sharpe-style momentum). A 52-week-high proximity sanity filter and ADX trend filter ensure the residual alpha is supported by real price trend (not a measurement artifact). The strategy is explicitly ORTHOGONAL to every existing fund strategy: AQM-52 ranks by price/52wk-high (a bounded LEVEL measure), while RAMD ranks by IDIOSYNCRATIC return AFTER neutralizing market AND sector exposures — the two produce substantially different portfolios. It is distinct from all fundamental-trajectory strategies (CBERM/RACEQ/DQROE/OLIGA/WVCCI/IIMM, which use fundamentals), from LDLVQ (which uses distribution-tail shape), and from intraday strategies (OMFM-15, IVCCM). A market-state regime gate (trailing 12-month market return, VIX) scales exposure, reflecting Cooper-Gutierrez-Hameed (2004) and Stivers-Sun (2010).

### Core Thesis
Residual (idiosyncratic) momentum exploits firm-specific underreaction to company news, while raw momentum is contaminated by reactive exposure to factor/sector drift. Removing that contamination (a) delivers higher Sharpe (0.96 vs ~0.5 for raw per Blitz-Huij-Martens 2011), (b) eliminates the primary crash mechanism — past-loser conditional beta spikes documented by Daniel-Moskowitz (2016) — and (c) produces a portfolio uncorrelated with the crowded factor-momentum trade currently concentrated in AI mega-caps. In a broadening-breadth, dispersion-rich environment (April 2026: 97th-pctile breadth, 97th-pctile dispersion, Fed cutting, stable macro), the firm-specific idiosyncratic alpha signal is at its strongest relative regime.

### Signals & Edge
CORE SIGNAL: Residual Momentum Composite = z(alpha_vs_spy) × 0.40 + z(alpha_vs_sector) × 0.40 + z(information_ratio) × 0.20. This IS the residual momentum signal — alpha_vs_spy is by definition the market-residual return, alpha_vs_sector is the industry-residual return, and information_ratio (no rf) is the risk-adjusted residual. The combination produces a stock that has (a) outperformed the market on an alpha basis, (b) outperformed its sector peers on an alpha basis, and (c) achieved that alpha with reasonable risk-adjustment.

CONFIRMATION GATES:
- risk_adj_momentum > 0 (risk-adjusted momentum support)
- adx_14d > 20 (real trend, not noise)
- dist_from_52w_high_pct > -0.15 (not deeply off highs — filters stale alpha)
- beta_stability < 0.30 (stable factor loadings; ensures the alpha measurement is meaningful, not from beta drift)

Key mechanism: Blitz-Huij-Martens (2011) — residual momentum delivered Sharpe 0.96 vs ~0.5 raw; t-stats >20 out-of-sample. Chaves (2012) replicated internationally. Daniel-Moskowitz (2016) — momentum crashes driven by conditional beta of past-loser portfolio (betas above 3 in bear markets); residual construction eliminates this by design. Barroso-Santa-Clara (2015) — vol scaling reduces kurtosis 18.24 → 2.68, skew -2.47 → -0.42. Combining residual construction AND vol scaling produces the cleanest momentum variant documented in the literature. In April 2026, MTUM ~40% TMT concentration + 65% SPX members outperforming (97th pctile breadth) = maximum regime dispersion between crowded raw momentum and broad idiosyncratic leadership.

### Universe
US equities (not ETFs — residual alpha relies on single-stock idiosyncratic measurement). Market cap $2B to $200B. avg_dollar_volume_20d > 10_000_000. price > 10. information_ratio > 0 (only stocks with POSITIVE trailing risk-adjusted return are eligible — ensures we're not catching a falling knife). Minimum 252 trading days of history required for stable alpha/beta estimation. Sector exclusions: Financials (beta/alpha distortion from leverage), Utilities (low-dispersion regulated returns reduce residual signal quality), Real Estate/REITs (different capital structure). Exclude: ADRs, SPACs, BDCs, CEFs, leveraged/inverse ETFs. Not reporting earnings within ±3 trading days. Estimated universe: 400-700 eligible names pre-signal; active portfolio 40-80 positions.

### Entry & Exit
ENTRY (monthly, at open 2 days after month-end):
- Residual Momentum Composite in top quintile (sector-neutral ranking within GICS sectors to avoid any residual sector tilt from entering through the ranking) AND
- alpha_vs_spy > 0 AND alpha_vs_sector > 0 (directional confirmation — both alphas must be positive, not just composite) AND
- risk_adj_momentum > 0 AND
- adx_14d > 20 AND
- dist_from_52w_high_pct > -0.15 (price within 15% of 52-week high — filters stocks where the alpha is stale and momentum has already decayed) AND
- beta_stability < 0.30.

EXITS:
- E1 Scheduled: next monthly rebalance if composite falls below sector 50th percentile (primary exit).
- E2 Alpha reversal: either alpha_vs_spy OR alpha_vs_sector turns negative mid-month — exit at next open (residual alpha consumed).
- E3 Trend failure: adx_14d falls below 15 (trend dissipated) — exit at next open.
- E4 Hard drawdown stop: 12% adverse move from entry.
- E5 Earnings buffer: mandatory exit 2 trading days before scheduled earnings; re-entry only allowed 2 days after if signal still qualifies.
- E6 Regime halt: trailing 12-month market return < -15% → reduce gross by 50%; < -25% → close all positions (market-state momentum conditioning per Cooper et al. 2004).
- E7 VIX spike halt: VIX > 40 sustained 5+ days → reduce gross by 50% and skip new entries.

Rebalancing: monthly. Expected annual turnover: 100-150% (higher than raw momentum because residual signal decays faster; multiple 2-signal exits possible). Expected average hold: 30-60 trading days.

### Risk Management
Volatility scaling (PRIMARY crash mitigant, Barroso-Santa-Clara 2015): target 10% annualized vol via trailing 6-month realized variance scaling of gross exposure. VIX-scaling on top: VIX <18 = 100%; 18-25 = 85%; 25-35 = 65%; 35-40 = 45%; >40 = halt new entries. Market-state scaling (Cooper et al. 2004): trailing 12M market return > 0 = full exposure; < 0 = 60%; < -15% = 30%; < -25% = close. Single-name cap: 3-5% gross exposure. Sector cap: 20-25% gross exposure per GICS sector (prevents the signal from concentrating into one hot sector even after sector-neutral ranking). Long-only baseline with optional long/short extension (bottom-quintile residual alpha = shorts; if L/S, apply LDLVQ-style borrow-cost and liquidity gates on short leg; net exposure cap -10% to +30%). Primary crash scenario addressed: the 2024-2025 raw-momentum drawdown (-31.8%) was driven by AI mega-cap sector rotation — residual momentum construction would have partially (not fully) insulated by removing sector exposure from the signal; further reduction via VIX scaling + earnings buffer + trend filter (adx).

### Research Backing
1. Blitz, Huij & Martens (2011) "Residual Momentum" — Sharpe 0.96 vs ~0.5 for raw momentum, t-stats >20, robust internationally, works over longer horizons (lower turnover than raw momentum); residuals remove factor exposure and reduce crash risk. 2. Chaves (2012) — extends residual momentum internationally; confirms single-factor (market) residualization captures most of the benefit. 3. Daniel & Moskowitz (2016) "Momentum Crashes" — raw momentum crashes driven by conditional beta of past-loser portfolio reaching above 3 in bear market rebounds; residual construction eliminates this by definition. 4. Grundy & Martin (2001) — dynamic beta-hedged momentum delivers higher Sharpe; residual momentum is an ex-ante implementable version of this. 5. Barroso & Santa-Clara (2015) "Momentum Has Its Moments" — vol-scaling reduces momentum kurtosis 18.24→2.68, skew -2.47→-0.42, max drawdown -96.69%→-45.20%; combining with residual construction is expected to compound the crash-risk reduction. 6. Jegadeesh & Titman (1993) — foundational price momentum: winners-minus-losers 1.49%/month; established 12-1 month horizon. 7. Cooper, Gutierrez & Hameed (2004) — momentum premium conditional on market state (DOWN states = negative momentum); validates trailing 12M market return gate. 8. Stivers & Sun (2010) — momentum premium negatively correlated with market volatility; validates VIX scaling. 9. Huij & Lansdorp — residual short-term reversal research; confirms residual framework robustness across horizons. 10. Citi Thematic Strategy (Jan 2026) — EPS Sharpe (risk-adjusted earnings momentum) delivering best returns YTD with Minimum Volatility-like risk profile — analogous risk-adjusted cross-sectional signal validation. 11. MSCI momentum factor analyses — momentum recovered H2 2025; negative correlation -0.47 with Low Risk factor in 2025 (vs historical -0.07) = factor crowding signal for raw momentum. 12. April 2026 macro context: Fed Funds 3.64% (cutting from 5.33% peak), 10Y 4.29%, 30Y 4.89%, unemployment 4.3%, inflation 2.35% stable, initial claims healthy 200-220K, VIX 18-31 range (currently ~25), 2s10s bear-steepening +50bp. April 2026 breadth data: 65% of S&P 500 outperforming (97th percentile); single-stock dispersion at 97th percentile (Goldman Jan 2026); MTUM 40% TMT = raw-momentum structurally crowded. Regime is THE ideal environment for residual momentum: broadening leadership + elevated dispersion + stable fundamentals + moderate vol = maximum idiosyncratic alpha dispersion with contained crash risk. Flip conditions: (a) Severe broad-market selloff (trailing 12M < -20%) → residual momentum still suffers in correlation regimes where everything moves together; regime halt handles this. (b) Return to narrow-leadership regime (e.g., 2023-early 2024 AI-only) → residual signal weakens as dispersion collapses; sector-neutral ranking and ADX gate partially compensate. (c) Widespread earnings disappointment across sectors → alpha measurements become unstable; earnings buffer partially handles.

### Edge
Residual momentum signal = composite of alpha_vs_spy (market-residualized return) + alpha_vs_sector (sector-residualized return) + information_ratio (risk-adjusted residual). By definition (per finance theory), regression alpha IS the component of returns not attributable to market factors — this is the exact Blitz-Huij-Martens construction implementable natively in the fund's screener. The edge comes from three compounding mechanisms: (1) Removing market/sector exposure eliminates the conditional-beta crash mechanism documented by Daniel-Moskowitz (2016); (2) Idiosyncratic alpha persists 2-6 months due to firm-specific underreaction while factor momentum is faster-fading and crowded; (3) In broadening-breadth regimes (April 2026: 97th percentile breadth, 97th percentile dispersion), residual alpha spread is maximized. Empirical edge: Sharpe 0.96 vs ~0.5 raw (Blitz-Huij-Martens 2011), t-stats >20, Carhart 4-factor alpha of 1.35%/month historically. Modern evidence: vol-scaled multi-signal momentum delivered ~18% ann returns 2006-2025 with drawdowns cut nearly in half vs raw. The 2024-2025 raw-momentum drawdown of -31.8% was driven by exactly the sector/beta contamination that residual construction removes. Orthogonality to existing strategies: AQM-52 picks near-52-week-high names (bounded level measure) — residual momentum picks firm-specific outperformers regardless of absolute price level, producing substantially different portfolios.

### Universe
US equities only. Market cap $2B to $200B (mid-to-large cap — mega-cap excluded to avoid concentration in crowded mega-cap momentum; small-cap excluded for beta/alpha measurement stability). avg_dollar_volume_20d > 10_000_000. price > 10. information_ratio > 0 (positive risk-adjusted return required — filters falling knives). Minimum 252 days of history for stable alpha/beta estimation. Sector exclusions: Financials (leverage-driven alpha distortion), Utilities (regulated returns → low residual signal quality), Real Estate/REITs (different capital structure). Exclude ADRs, SPACs, BDCs, closed-end funds, leveraged/inverse ETFs. No earnings within ±3 trading days. Estimated universe 400-700 eligible names; active portfolio 40-80 positions per leg.

### Entry & Exit
ENTRY (monthly, open 2 days after month-end): Residual Momentum Composite [0.40×z(alpha_vs_spy) + 0.40×z(alpha_vs_sector) + 0.20×z(information_ratio)] in top quintile within GICS sector AND alpha_vs_spy > 0 AND alpha_vs_sector > 0 AND risk_adj_momentum > 0 AND adx_14d > 20 AND dist_from_52w_high_pct > -0.15 AND beta_stability < 0.30. DATA INPUTS: screener alpha_vs_spy, alpha_vs_sector, information_ratio, risk_adj_momentum, adx_14d, dist_from_52w_high_pct, beta_stability (all computed nightly from daily price data); monthly refresh. EXITS: E1 Scheduled rebalance if composite falls below sector 50th pctile; E2 Alpha reversal — either alpha_vs_spy OR alpha_vs_sector turns negative mid-month; E3 Trend failure — adx_14d falls below 15; E4 Hard stop — 12% adverse move from entry; E5 Earnings buffer — exit 2 days before scheduled earnings, re-enter 2 days after if signal confirms; E6 Regime halt — trailing 12M market return < -15% reduce gross 50%, < -25% close; E7 VIX halt — VIX > 40 sustained 5+ days reduce gross 50%. Rebalancing monthly. Expected annual turnover 100-150%. Expected hold 30-60 trading days.

### Risk Management
Volatility scaling (primary crash mitigant, Barroso-Santa-Clara 2015): target 10% annualized portfolio vol via trailing 6M realized variance scaling of gross exposure. VIX scaling: <18=100%, 18-25=85%, 25-35=65%, 35-40=45%, >40=halt. Market-state scaling (Cooper et al. 2004): trailing 12M market return > 0 = full, < 0 = 60%, < -15% = 30%, < -25% = close. Single-name cap 3-5% gross exposure. GICS sector cap 20-25% gross (even after sector-neutral ranking, prevent concentration). Long-only baseline; optional L/S extension with bottom-quintile residual alpha as shorts plus LDLVQ-style borrow/liquidity gates. Net exposure -10% to +30% if L/S. Primary crash scenario: broad correlation regime where residual signal weakens AND market falls (regime halt handles). Secondary: earnings surprise wave that destabilizes alpha measurement (earnings buffer). Tertiary: return to narrow AI-only leadership regime that collapses dispersion (ADX + info_ratio gates partially compensate, but signal weakens).

### Research Backing
Primary: Blitz, Huij & Martens (2011) "Residual Momentum" — Sharpe 0.96, t-stats >20, reduced crash risk, works at longer horizons. Chaves (2012) international replication. Daniel & Moskowitz (2016) "Momentum Crashes" — conditional beta mechanism that residual construction eliminates. Barroso & Santa-Clara (2015) "Momentum Has Its Moments" — vol scaling reduces kurtosis 18.24→2.68, skew -2.47→-0.42, drawdown -96.69%→-45.20%. Grundy & Martin (2001) — beta-hedged momentum. Jegadeesh & Titman (1993) — original momentum paper. Cooper, Gutierrez & Hameed (2004) — market-state conditioning. Stivers & Sun (2010) — volatility conditioning. Huij & Lansdorp — residual reversal research. Modern: Citi Thematic Jan 2026 (EPS Sharpe); MSCI factor analyses (momentum -0.47 corr with Low Risk in 2025 vs -0.07 historical = crowded); April 2026 regime data (97th pctile breadth, 97th pctile dispersion, MTUM 40% TMT); -31.8% raw momentum drawdown Sep2024-Apr2025 driven by sector/beta contamination that residual construction removes.

### Research Results
**Evaluated:** 2026-04-16

# Validation Results — Residual Alpha Momentum with Dispersion-Broadening Regime Gate (RAMD)

**Strategy ID:** `residual_alpha_momentum_with_dispersionbroadening_regime_gate`
**Validation Date:** 2026-04-16
**Verdict:** ❌ FAILED — Best Sharpe: -0.22 (threshold: > 0.8)

## Universe
- Asset Class: US Equities (single-stock)
- Filters: market_cap [2B, 200B], avg_dollar_volume_20d [10M, None], price [10, None], information_ratio [0, None], sectors (no financials/utilities/real_estate), alpha_vs_spy > 0, alpha_vs_sector > 0, risk_adj_momentum > 0, adx_14d > 20, dist_from_52w_high_pct > -0.15, beta_stability < 0.30
- Tickers (53): TIGO, VALE, GATX, CHT, T, DBD, SFD, DAR, KOF, CCEP, PBR, FMX, AVT, RL, R, WCC, NGVT, KT, EA, AMX, VZ, CCK, STLD, NUE, GD, EPD, NOC, CTVA, BA, ESE, RBC, PH, F, ITT, PSMT, RVMD, MLI, JCI, TDY, FLS, GRMN, MCK, CGON, DRI, KR, TDW, MPLX, WTS, GVA, WAB, CVS, SEB, RPRX

## Critical Build Issue
The strategy code files (strategy.py, wiring.py, signals/model.py, indicators/suite.py, config.py) are unmodified template scaffold copies importing from strategies.template.*. The RAMD-specific logic (residual momentum composite, sector-neutral ranking, alpha_vs_spy/sector gates) was never implemented. MANIFEST.json belongs to a different strategy (WVCCI). Backtest ran cleanly but on template EMA/RSI crossover logic, not RAMD.

## All Runs (12 total)
| Run | FAST_EMA | SLOW_EMA | RSI_LONG | ALLOW_SHORTS | Sharpe | Max DD | Return | Trades |
|-----|----------|----------|----------|--------------|--------|--------|--------|--------|
| 0 baseline | 20 | 50 | 55.0 | True | -0.84 | -97.78% | -97.22% | 1915 |
| 1 | 20 | 50 | 55.0 | False | -0.48 | -54.29% | -38.60% | 813 |
| 2 | 20 | 50 | 60.0 | False | -0.36 | -45.75% | -20.08% | 564 |
| 3 | 20 | 50 | 65.0 | False | -0.29 | -40.05% | -5.38% | 314 |
| 4 | 20 | 50 | 70.0 | False | -0.56 | -37.42% | -16.25% | 122 |
| 5 | 50 | 200 | 60.0 | False | -0.46 | -26.90% | -11.29% | 287 |
| 6 | 50 | 200 | 65.0 | False | -0.50 | -23.51% | -8.35% | 193 |
| 7 | 14 | 50 | 60.0 | False | -0.38 | -27.73% | -5.30% | 762 |
| 8 | 10 | 30 | 60.0 | False | -0.45 | -55.04% | -31.85% | 585 |
| 9 | 20 | 50 | 65.0 | False | -0.51 | -28.97% | -7.76% | 351 |
| 10 BEST | 26 | 65 | 65.0 | False | -0.22 | -32.90% | +4.46% | 308 |
| 11 | 26 | 65 | 63.0 | False | -0.40 | -48.03% | -19.55% | 402 |

## Root Cause
Pipeline Stages 4+5 never customized the template files for RAMD. All 12 runs used the generic EMA/RSI crossover (not the intended residual alpha composite). The RAMD concept (Blitz-Huij-Martens 2011, documented Sharpe ~0.96) remains academically sound and deserves a proper implementation.

