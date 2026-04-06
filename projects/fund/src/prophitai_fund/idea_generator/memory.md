---
date: 2026-04-06
title: Negative Gamma Regime Fundamentally Changes Gap Strategy Directionality
topic: regime_observations
---
In a negative dealer gamma regime (VIX 20–40, dealers net short gamma), mechanical delta-hedging amplifies gap moves rather than dampening them. This reverses the standard gap-fade logic: in negative gamma regimes, gap CONTINUATION strategies are structurally favored over gap-fade strategies. The regime is identifiable via the Gamma Exposure Index (GEX) or VIX level as proxy. This insight critically changes strategy design at the regime identification phase — always check dealer gamma positioning before selecting gap-fade vs. gap-continuation. Source: April 2026 JPMorgan macro research + options market structure analysis.

---
date: 2026-04-06
title: Intraday TOD Seasonality Has Strongest Research Score of All HFT Signals
topic: strategy_insights
---
When researching 1-minute bar intraday strategies, time-of-day (TOD) seasonality consistently produces the highest relevance scores (0.6328 in strategy_research). The Hirsch (1987) post-open and post-lunch rise pattern is robustly documented across U-shape market order flow (open+close peaks) and HMM intraday momentum papers. Spline-based TOD models fit on 66 rolling days at T=856 1-min bars/day are the canonical implementation. When designing any intraday HFT strategy, incorporating TOD windows (9:35–10:30 and 12:00–13:30 as active; 10:30–12:00 and 15:30–16:00 as inactive) dramatically improves signal quality. This should be a default consideration for all future intraday strategy designs.

---
date: 2026-04-06
title: Current Intraday Vol Regime Explicitly Labeled as 'HF Noise' by JPMorgan April 2026
topic: regime_observations
---
JPMorgan fixed income weekly (late March 2026) explicitly stated: in elevated policy uncertainty regimes, intraday moves are 'high-frequency noise, which can cause 2-look vol to rise above close-to-close vol'. This is the clearest institutional confirmation that the April 2026 regime is dominated by noise (not informed flow), making mean-reversion strategies structurally favored over momentum at sub-day horizons. VIX 22-25 with 2-look vol > close-to-close vol is the precise signature of a noise-dominant intraday regime. When designing future intraday strategies: this VIX range + 2-look/CC vol divergence is the green flag for mean-reversion; the absence of this signature (or 2-look < CC vol) shifts the edge toward momentum.

---
date: 2026-04-06
title: LETF Rebalancing is a Structurally Larger Force in 2026 Than Prior Years
topic: regime_observations
---
As of April 2026, leveraged ETF AUM reached $132B (30% YoY growth, 552 funds). Citi/Goldman documented $5B+ single-day LETF rebalancing flows in early 2026 — described as 'an additional source of short gamma not present in previous selloffs.' The LETF rebalancing mechanism (buy on up days / sell on down days) is now large enough to mechanically amplify afternoon directional moves in S&P 500 components. When designing intraday breakout or momentum strategies for afternoon sessions (13:00–15:00 PM), the session cumulative SPX return should be used as a LETF direction gate — if SPX ≥ +0.5%, expect LETF buy flows to amplify upside breakouts; if SPX ≤ -0.5%, expect amplified downside. This is a structural market-making force, not informational, and does not decay between sessions. Shum et al. (2015) is the foundational academic paper on LETF-equity volatility transmission.

