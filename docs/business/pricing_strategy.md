# ProphitAI Pricing Strategy & Unit Economics

Generated from 520 agent traces over 30 days of Langfuse data. Recalculate anytime via `python business_analytics.py` in the repo root.

## What the Data Actually Says

**Cost distribution is violently bimodal** — this is the most important finding:

```
47% of all runs cost under $0.10     ← quick queries
35% cost $0.10 to $2.00              ← medium analysis
16% cost $2.00 to $10.00             ← deep research
2%  cost $10.00 to $22.00            ← monster research runs
```

**Cost is dominated by whales.** Top 5% of runs drive 56.4% of cost. Top 10% drive 76%. 15 sessions (12% of users) drove 80% of the $443 in spend. This is a power law, not a normal distribution. Pricing must account for this or 3 whales will eat the margin of 20 normal users.

**Cost drivers are predictable:**

- Top quartile iterations = 10.3x bottom quartile cost
- 1-5 iter runs: **$0.05 median**
- 80+ iter runs: **$5.36 median**
- 0 workers: $0.14 | 5-7 workers: $4.36

This tells us exactly what to gate: **iterations and workers.**

## Empirical Cost Distribution

### Simple Agent Runs (n=322)
| Percentile | Cost |
|-----------|------|
| P10 | $0.016 |
| P25 | $0.034 |
| P50 (median) | $0.113 |
| P75 | $0.258 |
| P90 | $0.678 |
| P95 | $1.285 |
| P99 | $8.148 |
| Max | $16.22 |

### Planned Agent Runs (n=106)
| Percentile | Cost |
|-----------|------|
| P10 | $0.035 |
| P25 | $0.178 |
| P50 (median) | $1.422 |
| P75 | $4.065 |
| P90 | $7.501 |
| P95 | $11.385 |
| P99 | $17.004 |
| Max | $22.81 |

## The Optimal Model Matrix

Based on median cost analysis across 97 planned + 322 simple runs:

| Role | Recommended Model | Median Cost | Why |
|------|------------------|-------------|-----|
| **Simple agent / quick query** | Gemini 2.5 Flash | **$0.006** | 23x cheaper than Sonnet, identical tool quality |
| **Orchestrator (planned)** | Sonnet OR Gemini 2.5 Pro | $0.99 / $0.49 | Needs reasoning for task decomposition. Pro is 50% cheaper — A/B test for quality |
| **Workers (tool calling)** | Claude Haiku 4.5 | **$0.42** | Best tool-calling reliability at 4x cheaper than Sonnet |
| **Workers (if simple tasks)** | Gemini 2.5 Flash | $0.08 | Use for straightforward tool calls when reliability is less critical |
| **Final synthesis** | Same as orchestrator | — | Don't bounce models here — user-facing text quality matters |
| **AVOID** | Grok 4.2 | $1.45 (workers) | Surprisingly expensive due to no caching; only use if orchestrator needs it |
| **AVOID** | Claude Opus | $7.90 (workers) | 19x more expensive than Haiku. Reserve for edge cases only. |

**This routing alone cuts unit cost ~60%** for planned runs (from $2.83 avg to $1.14).

### Cost Per Run by Model Config (Planned Agents)

| Config | Simple Median | Planned Median | Planned P90 |
|--------|--------------|----------------|-------------|
| Current (all Sonnet) | $0.135 | $2.13 | $7.85 |
| **Optimized (Sonnet + Haiku)** | $0.135 | **$1.39** | $4.44 |
| Budget (Sonnet + Flash) | $0.135 | $1.06 | $3.63 |
| Aggressive (Grok + Grok) | $0.099 | $2.03 | $6.97 |
| Ultra-budget (Pro + Flash) | $0.059 | $0.56 | $1.78 |

## Target Market

**Retail investors only.** This is not a professional/RIA tool. Pricing, features, and communication all target individual investors managing their own money — from casual stock pickers to serious active traders.

## The Pricing Model

Three retail tiers plus free. Margins computed using Sonnet orchestrator + Haiku workers + Flash for simple queries.

```
┌──────────────────────────────────────────────────────────────────────┐
│  FREE                                                                │
│  $0/mo                                                               │
│  20 quick queries + 2 deep analyses                                  │
│  Flash everything                                                    │
│  Cost: ~$3/active user. Purpose: acquisition funnel.                │
├──────────────────────────────────────────────────────────────────────┤
│  STARTER — $29/mo                                                    │
│  100 queries + 10 deep analyses                                      │
│  Target user: casual retail investor, checks portfolio weekly       │
│  Typical cost (60%): $14  →  52% margin                             │
│  Max cost (100%):    $22  →  24% margin                             │
├──────────────────────────────────────────────────────────────────────┤
│  PRO — $79/mo  (the volume tier)                                     │
│  250 queries + 25 deep analyses                                      │
│  Target user: active retail trader, logs in several times per week  │
│  Typical cost (60%): $32  →  59% margin                             │
│  Max cost (100%):    $51  →  35% margin                             │
├──────────────────────────────────────────────────────────────────────┤
│  POWER — $149/mo                                                     │
│  500 queries + 60 deep analyses                                      │
│  Target user: power retail trader, daily user, multiple portfolios  │
│  Typical cost (60%): $70  →  53% margin                             │
│  Max cost (100%):    $113 →  24% margin                             │
└──────────────────────────────────────────────────────────────────────┘

OVERAGE PRICING (after limits):
  Query:    $0.25 each  (5x cost at Flash)
  Analysis: $3.00 each  (2x cost at optimized)

SPENDING CAP:
  Default: 2x subscription value in overages before throttling
  User-configurable up or down
```

### Why These Numbers Work

**The gym membership math is real.** 47% of runs are under $0.10 — most users will use ~60% of their limits. The users who hit limits either pay overage or upgrade. The 5% who blow past limits repeatedly hit the spending cap and are auto-prompted to upgrade to Power.

**Margins improve over time automatically.** Sensitivity analysis: if LLM costs drop 50% in 12 months (they will), the $79 Pro tier goes from 59% to 78% margin with zero price changes. That's the advantage of subscription.

**Why not higher limits?** At Pro's 25 analyses, maxed-out margin is 35%. Jumping to 40 analyses drops max margin to 5%. The 25-analysis cap is the sweet spot where even max-usage is sustainable.

### Why No Unlimited Tier

Retail-only means we can't rely on a pass-through Professional tier to absorb heavy users. Instead:

1. **Overage pricing** is the primary safety valve — transparent, predictable, and scales with usage
2. **Hard spending caps** prevent runaway bills on both sides
3. **Auto-upgrade prompts** push consistent over-users from Pro → Power
4. **Power tier limits** are deliberately chosen so even 100% utilization is profitable

## Growth Strategy in Numbers

Current internal spend: **$474/mo** (team testing).

At 100 paying customers:

| Scenario | Avg tier | Revenue | Cost | Monthly Profit |
|----------|---------|---------|------|----------------|
| Conservative (mostly Starter) | $35 blended | $3,500 | ~$1,500 | **$2,000** |
| Balanced (Starter + Pro mix) | $55 blended | $5,500 | ~$2,300 | **$3,200** |
| Pro-heavy | $75 blended | $7,500 | ~$3,000 | **$4,500** |
| Power-mix (+10% on Power tier) | $85 blended | $8,500 | ~$3,400 | **$5,100** |

At 1,000 users with balanced retail mix: **~$32k/mo gross profit** on subscription + overage.

## Critical Implementation Order

### 1. Model Router (non-negotiable)
Every tier above assumes Flash for simple queries and Haiku for workers. Without routing, Starter margins flip negative on any user who does 3+ deep analyses.

### 2. Usage Tracking in UI
Users need to see their "quick queries used" and "deep analyses used" counters. This is also how to enforce tier limits.

### 3. Per-User Spend Cap
Even with routing, a runaway agent could hit $20/call. Default cap: 2x subscription value per month before throttling. User-configurable.

### 4. Overage Billing via Stripe
Metered billing on Query and Analysis overages. Revenue safety net + reduces need for hard caps.

### 5. Auto Upgrade Prompts
If a user exceeds their Pro limits two months in a row, auto-suggest Power tier. Prevents resentment from paying overage indefinitely.

## Launch Recommendation

Start with **three retail tiers**:

- **Free**: 20 queries + 2 analyses (acquisition funnel)
- **$29/mo Starter**: 100 queries + 10 analyses (casual retail investor)
- **$79/mo Pro**: 250 queries + 25 analyses (active retail trader — volume tier)
- **$149/mo Power**: 500 queries + 60 analyses (daily power user)

Offer annual pricing at 20% discount on all paid tiers.

### Target Mix at 1,000 Users (retail only)
- 15% Free (acquisition funnel, loss leader)
- 50% Starter = $14,500/mo
- 30% Pro = $23,700/mo
- 5% Power = $7,450/mo

**Total MRR at 1,000 users: ~$45,650/mo, ~60% gross margin = ~$27,400/mo gross profit.**

## Key Unit Economics Constants

Use these numbers for any modeling. All from 30-day Langfuse data.

| Metric | Value |
|--------|-------|
| Simple agent median cost (optimized) | $0.05 |
| Simple agent P90 cost (optimized) | $0.07 |
| Planned agent median cost (optimized) | $1.39 |
| Planned agent P90 cost (optimized) | $4.44 |
| Fixed cost per user per month | ~$3-5 |
| Cost concentration: top 5% of runs | 56% of total cost |
| Cost concentration: top 10% of runs | 76% of total cost |
| Whale threshold (sessions = 80% cost) | 12% of users |
| Perplexity search cost | $0.005/call |
| Model price drop assumption (12mo) | -50% |

## Files

- `unit_economics.py` — per-trace cost report, mixed-model combos
- `business_analytics.py` — deep analysis (distributions, drivers, concentration, scenarios)
- `download_langfuse_data.py` — refresh data (run monthly)
- `langfuse_data/` — weekly JSON dumps
