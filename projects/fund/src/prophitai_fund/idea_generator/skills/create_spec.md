---
name: create-spec
description: Write strategy specifications precise enough for a screener and portfolio construction agent to implement without ambiguity. Covers universe filters, entry/exit rules, risk management, and data requirements with quantitative thresholds.
---

# Create Spec

Write strategy specifications that a screener and portfolio construction agent can implement
without ambiguity. Every field must be quantitative, measurable, and map to real data.

## Spec Quality Standard

A spec is complete when a developer could implement it with zero follow-up questions.
Each section below has a purpose — if your output doesn't satisfy that purpose, rewrite it.

## Section-by-Section Requirements

### Core Thesis (purpose: explain WHY the edge exists)

State three things and nothing else:
1. **The signal** — what observable data pattern predicts returns
2. **The mechanism** — the behavioral, structural, or risk-based reason it persists
3. **The evidence** — 2-3 specific research citations with empirical results (Sharpe, alpha, t-stat)

Bad: "Momentum stocks tend to continue trending due to behavioral biases."
Good: "12-1 month cross-sectional momentum in large-caps produces ~6% annual alpha (Jegadeesh-Titman 1993, t=3.6). The mechanism is gradual information diffusion (Hong-Stein 1999): analyst coverage and institutional ownership predict momentum speed. The signal survives Fama-French 5-factor adjustment (alpha = 0.4%/month, t=2.8)."

### Universe Definition (purpose: produce a filterable stock list)

Every filter must map to a concrete screener metric. Use this format:

```
- [metric_name] [operator] [threshold] — [reason for this threshold]
```

Operators: >, <, >=, <=, between [x] and [y], in [list]

Bad: "Large-cap liquid US equities with momentum characteristics"
Good:
- market_cap >= $5B — liquidity floor, ensures institutional tradability
- avg_daily_dollar_volume_20d >= $50M — execution capacity for $1M+ positions
- exchange in [NYSE, NASDAQ] — US-listed only
- sector not in [Utilities, Real Estate] — low beta sectors incompatible with signal
- price >= $10 — avoids penny stock microstructure noise
- 12_1_month_return > 60th percentile cross-section — momentum signal threshold
- roa > 0% — excludes distressed names where momentum = falling knife

The filters should produce a universe of 50-500 names. If your filters produce <30 or >1000,
recalibrate your thresholds.

### Inclusion & Removal Rules (purpose: define portfolio turnover)

Separate these clearly:
- **Rebalance inclusion**: what gets a stock INTO the portfolio at the next rebalance
- **Rebalance removal**: what kicks a stock OUT at the next rebalance
- **Intra-period signals** (if applicable): discrete triggers between rebalances (stops, events)

Each rule must specify: the metric, the threshold, and whether it's evaluated at rebalance
or continuously.

Bad: "Remove stocks that lose momentum"
Good: "At monthly rebalance, remove any position where 12-1 month return has dropped below
the 40th percentile cross-section. Between rebalances, exit any position that gaps down >5%
on 3x average volume (informed adverse signal)."

### Rebalancing (purpose: define execution cadence)

Specify:
- **Frequency**: daily / weekly / monthly / quarterly
- **Day/time**: e.g., "close of third Friday each month"
- **Out-of-cycle triggers**: what forces an early rebalance (with thresholds)
- **Expected turnover**: percentage of portfolio replaced per rebalance (estimate)
- **Execution window**: how long to fill (e.g., "TWAP over 30 minutes at close")

### Risk Management (purpose: define hard constraints, not guidelines)

Every risk rule must have a numeric threshold and a defined action. Format:

```
- [condition] -> [action]
```

Bad: "Maintain diversification across sectors"
Good:
- single_name_weight > 5% -> trim to 5% at next rebalance
- gics_sector_weight > 25% -> cap new entries in that sector
- portfolio_drawdown from 20d_high > 10% -> reduce gross exposure by 50%
- VIX > 35 -> halt new entries, tighten stops to 50% of normal width
- rolling_20_trade_win_rate < 35% -> reduce position sizes by 40%

### Data Requirements (purpose: confirm implementability)

For each data input the strategy needs, specify:
- **Data type**: price bars, fundamentals, screener metric, macro indicator, options
- **Granularity**: tick, 1-min, daily, quarterly
- **Source**: which system provides it (price DB, screener, FMP, macro DB)
- **Lookback**: how much history is needed (e.g., "252 trading days of daily bars")
- **Update frequency**: real-time, daily EOD, quarterly

Flag anything that pushes the boundary of available data. If the strategy "works better"
with data we don't have, note it as a limitation — don't pretend the fallback is equivalent.

### Regime Dependencies (purpose: define when to NOT run the strategy)

Specify:
- **Favorable regime**: macro conditions where the strategy has edge (with metrics)
- **Unfavorable regime**: macro conditions where the strategy breaks (with metrics)
- **Kill switch**: the specific condition that should halt the strategy entirely

Bad: "Strategy may underperform in volatile markets"
Good: "Favorable: VIX 15-30, positive credit impulse (IG spread narrowing), earnings
dispersion > 60th percentile historical. Unfavorable: VIX > 35 or < 12 (momentum crashes
in extreme vol; no dispersion in low vol). Kill switch: correlation of S&P 500 constituents
> 0.7 rolling 20d (risk-off regime, all stocks move together, cross-sectional signal collapses)."

## Anti-Patterns to Avoid

1. **Narrative padding** — Don't explain how Bollinger Bands work or what VIX measures.
   The reader knows finance. State the parameter, not the textbook definition.

2. **Redundant risk rules** — If you have VIX-based sizing AND a drawdown stop AND a
   per-position stop AND a win-rate monitor AND an event-day reduction, you have too many
   overlapping safety nets. Pick the 3-4 that matter most and define them precisely.

3. **Copy-paste risk sections** — Every strategy has different risk characteristics.
   A mean-reversion strategy's risk rules should look nothing like a momentum strategy's.
   If your risk section could be swapped between strategies without changing anything,
   it's too generic.

4. **Over-specified entry signals** — A 4-layer composite signal with 6 gates is not
   more robust than a 2-layer signal. Each additional filter adds overfitting risk and
   reduces the number of tradeable signals. Ask yourself: "Which of these gates actually
   adds alpha vs. just reducing sample size?"

5. **Missing capacity analysis** — How many names pass your filters? How much daily
   volume is available? If your universe is 30 stocks with $50M ADV each, your strategy
   capacity is ~$15M before market impact matters. State this.

## Self-Check Before Submitting

Before calling past_ideas(operation="write"), verify:

- [ ] Every universe filter maps to a real screener metric or data field
- [ ] Entry rules can be evaluated programmatically (no subjective judgment)
- [ ] Exit rules have numeric thresholds, not qualitative conditions
- [ ] Risk rules specify both the trigger condition AND the action
- [ ] Data requirements are all within the available_data constraints
- [ ] The regime dependency section names specific metrics and thresholds
- [ ] The strategy produces enough signals to be statistically meaningful (>50 trades/year)
- [ ] Estimated capacity is stated
