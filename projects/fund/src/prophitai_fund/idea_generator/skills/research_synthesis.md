---
name: research-synthesis
description: Synthesize RAG research results into an evidence-backed thesis. Covers query formulation, evidence evaluation tiers, red flags, the 4-step synthesis process, and common failures like kitchen-sink signals and cost blindness.
---

# Research Synthesis

How to go from raw RAG research results to an evidence-backed thesis. This skill governs
Phase 1 (Deep Strategy Research) and the transition into Phase 3 (Strategy Specification).

## The Problem This Solves

RAG tools return chunks of research papers with relevance scores. The default failure mode
is treating these as a bibliography — listing what each paper says and stitching them together
with narrative glue. That produces strategies that sound academically justified but have no
real edge, because the agent never critically evaluated whether the evidence actually supports
the proposed implementation.

## Research Query Strategy

### Query Formulation

Write queries as specific hypotheses, not topic searches.

Bad queries:
- "momentum strategies" (too broad, returns textbook definitions)
- "intraday trading strategies for equities" (generic, returns everything)
- "Bollinger Band strategies" (indicator-specific, misses the underlying anomaly)

Good queries:
- "cross-sectional momentum returns after controlling for volatility in large-cap equities"
- "mean reversion half-life estimation for equity pairs using Ornstein-Uhlenbeck"
- "volume-price divergence as a predictor of short-term reversals empirical evidence"
- "transaction cost impact on high-frequency momentum strategy profitability"

### Query Iteration

Your first query reveals the landscape. Subsequent queries should drill into what matters.

Pattern:
1. **Broad signal query** — "Does this anomaly exist?" → Get the core papers
2. **Mechanism query** — "Why does this persist?" → Behavioral, structural, or risk explanation
3. **Boundary query** — "When does this fail?" → Regime conditions, capacity limits, decay
4. **Implementation query** — "How has this been traded?" → Practical details, costs, frequency
5. **Counter-evidence query** — "What challenges this thesis?" → Contradictory findings

Minimum 5 queries across strategy_research and theory_research. If your first 3 queries
all confirm your hypothesis, your 4th query MUST seek disconfirming evidence.

## Evidence Evaluation

### Scoring Research Results

Not all research findings are equal. Apply this hierarchy:

**Tier 1 — Strong evidence** (build strategy around this):
- Published empirical results with out-of-sample testing
- Multiple independent papers confirming the same anomaly
- Results that survive transaction cost analysis
- Evidence from the last 10 years (market structure changes matter)

**Tier 2 — Supporting evidence** (strengthens thesis, doesn't stand alone):
- Theoretical models with empirical calibration
- Results from related but not identical markets/timeframes
- Backtested results without out-of-sample validation
- Older papers (pre-2010) where market structure may have changed

**Tier 3 — Contextual evidence** (useful background, not thesis-bearing):
- Pure theoretical models without empirical validation
- Results from asset classes we don't trade (futures, forex, crypto)
- Methodology papers (useful for implementation, not for edge)
- Survey papers that summarize without new evidence

When citing research in your strategy output, lead with Tier 1 evidence. If you have no
Tier 1 evidence for the core signal, your thesis is speculative — acknowledge this explicitly.

### Red Flags in Research

Watch for these and call them out:

- **Survivorship bias** — Backtest on current index constituents, not point-in-time
- **Look-ahead bias** — Uses information not available at trade time
- **Data mining** — Tests 100 signals, reports the 3 that worked
- **Unrealistic transaction costs** — Assumes 0 cost or fixed small cost for HFT strategies
- **In-sample only** — No out-of-sample or walk-forward validation
- **Simulated data** — Results on synthetic data, not real markets
- **Pre-cost Sharpe** — A Sharpe > 2.0 pre-cost means nothing without cost analysis

When a paper shows pre-cost Sharpe > 2.0, immediately ask: what are realistic costs for this
strategy's turnover and universe? A HFT strategy trading 1-min bars in large-caps at 5-10bps
round-trip loses 50-100bps per trade. If the average trade captures 30bps gross, the strategy
is underwater after costs.

## Synthesis Process

### Step 1: Cluster findings by signal type

After completing your research queries, group results by the underlying signal they exploit.
Multiple papers may describe the same anomaly with different implementations.

Example: Three papers might discuss:
- "Volume-weighted momentum outperforms calendar-time momentum"
- "Order flow imbalance predicts short-term returns"
- "Volume-price divergence signals behavioral reversals"

These are all variants of "informed volume predicts direction." Recognize the common thread.

### Step 2: Identify the core edge

From your clusters, select the ONE primary signal that has:
- The strongest empirical evidence (Tier 1)
- A clear mechanism explaining persistence
- Implementability with available data
- Sufficient signal frequency for statistical significance

Everything else is supporting. A strategy with one well-understood edge beats a strategy
with four speculative edges layered together.

### Step 3: Stress-test the thesis

Before writing the spec, answer these questions:

1. **Why hasn't this been arbitraged away?**
   If you can't answer this, the edge probably doesn't exist. Valid answers: capacity
   constraints, regulatory barriers, behavioral persistence, structural market features.

2. **What's the realistic Sharpe after costs?**
   Take the best-case research Sharpe. Haircut it by: 30-50% for transaction costs
   (more for HFT), 20-30% for implementation shortfall, 10-20% for data snooping.
   If the result is below 0.5, the strategy isn't worth implementing.

3. **How many independent trades per year?**
   Fewer than 50 → the strategy can't be statistically validated in a reasonable timeframe.
   Fewer than 200 → you need a very high win rate or payoff ratio to be confident.

4. **Does this work in the CURRENT regime?**
   A strategy backed by 2005-2015 evidence may not work in 2026. What's changed?
   Market structure, fee compression, HFT proliferation, LETF growth, retail participation.

### Step 4: Write the thesis statement

Compress your synthesis into one paragraph that contains:
- The signal (what you're trading)
- The mechanism (why it works)
- The evidence (who proved it, with numbers)
- The regime fit (why now)

This paragraph becomes the Core Thesis section of your spec. If you can't write it in one
paragraph, you don't understand your own strategy well enough.

## Common Synthesis Failures

### The Kitchen Sink

Symptom: Strategy combines 4+ independent signals into a composite score.
Problem: Each signal adds a degree of freedom. A 4-signal composite with 3 parameters each
gives you 12 knobs to overfit. The probability that all 4 signals are genuinely alpha-generative
AND complementary is low.
Fix: Pick the strongest signal. Add ONE secondary signal only if it captures a genuinely
orthogonal dimension (e.g., a momentum signal + a volatility filter, not two momentum signals).

### The Narrative Bridge

Symptom: "Paper A found X. Paper B found Y. Therefore, combining X and Y should produce Z."
Problem: Combining two individually profitable strategies doesn't guarantee a better strategy.
Correlations between signals, shared factor exposures, and execution conflicts can make the
combination worse.
Fix: Only combine signals when you have evidence of complementarity — either from a paper
that tested the combination, or from orthogonal factor exposures.

### The Recency Trap

Symptom: Strategy designed around current macro regime as if it's permanent.
Problem: "VIX is at 25 and negative gamma favors continuation" is a regime observation, not
a strategy edge. When VIX normalizes to 15, the strategy breaks.
Fix: Design the core signal to work across regimes. Use regime as a SIZING adjustment, not
as the signal itself. The strategy should have positive expected value in neutral regimes
and enhanced expected value in favorable regimes.

### The Cost Blindness

Symptom: Strategy targets 30bps per trade on 1-min bars with 500% daily turnover.
Problem: At 5-10bps round-trip costs for large-caps, the strategy needs >50bps gross capture
per trade to be viable. Most intraday signals capture 10-30bps.
Fix: Always compute: (expected gross return per trade) - (estimated round-trip cost) =
net edge per trade. If net edge < 5bps, the strategy is fragile — any cost increase or
execution slippage kills it.

## Research Citation Format

When citing research in your final output, use this format:

```
[Author(s) (Year)] — [Key finding relevant to your thesis] ([metric]: [value])
```

Example:
```
Jegadeesh-Titman (1993) — 12-1 month momentum produces 1.0%/month raw returns (t=3.07)
Barroso-Santa-Clara (2014) — Volatility-scaling doubles momentum Sharpe from 0.5 to 1.0
Hong-Stein (1999) — Analyst coverage predicts momentum speed (low coverage = slow diffusion)
```

Do NOT cite papers just because they appeared in your search results. Only cite papers
whose specific findings directly support or challenge your thesis.
