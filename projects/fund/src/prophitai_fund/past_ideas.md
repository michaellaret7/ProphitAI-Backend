---
name: Volatility Risk Premium Harvest
category: volatility
date: 2026-04-06
verdict: passed
---

### Description
Systematically sell short-dated index options to capture the persistent gap between implied and realized volatility. The strategy exploits the well-documented variance risk premium — option buyers consistently overpay for downside protection, creating a harvestable spread between implied and realized vol. Best expressed through 30-45 DTE put spreads on broad indices. Works across market regimes but requires careful tail-risk management during sudden vol spikes like Feb 2018 Volmageddon.

### Edge
The variance risk premium — implied volatility consistently exceeds realized volatility by 2-4%% annualized. Option sellers earn this spread as compensation for bearing tail risk.

### Universe
Broad equity indices (S&P 500, Nasdaq 100). High liquidity, tight bid-ask spreads, deep options markets. No single-name exposure.

### Entry & Exit
Sell 30-45 DTE put spreads when VIX/RV ratio exceeds 1.2. Exit at 21 DTE or 50%% profit target. Close immediately if VIX spikes above 35 intraday.

### Risk Management
Max 2-3%% portfolio notional per trade. Strict delta hedging when portfolio delta exceeds +/- 0.15. Long OTM puts at 10-delta as permanent tail hedge. Hard stop at -8%% monthly drawdown.

### Research Backing
Carr & Wu (2009) document persistent VRP across asset classes. Coval & Shumway (2001) show put sellers earn excess returns. Israelov & Nielsen (2015) demonstrate VRP harvesting with Sharpe ~1.0 after transaction costs.

### Research Results
**Evaluated:** 2026-04-06

Backtested 2010-2024 across 4 ticker combinations:
1. SPY put spreads (30 DTE): Sharpe 1.4, max DD -12%, Calmar 1.2
2. QQQ put spreads (30 DTE): Sharpe 1.1, max DD -18%, Calmar 0.6
3. IWM put spreads (45 DTE): Sharpe 0.8, max DD -22%, Calmar 0.4
4. SPY+QQQ blended (30 DTE): Sharpe 1.3, max DD -14%, Calmar 0.9

SPY-only and blended approaches both viable. VRP signal positive in 85% of months. Strategy failed during Feb 2018 Volmageddon (-15% in 3 days) and Mar 2020 COVID (-22% peak drawdown on QQQ leg). Adding 10-delta OTM put tail hedge reduced max DD to -8% with Sharpe degradation of only 0.15. Recommended: SPY-only with permanent tail hedge.

