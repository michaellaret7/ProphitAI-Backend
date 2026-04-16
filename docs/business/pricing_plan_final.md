# ProphitAI Pricing Plan (Final)

**Target market:** Retail investors only. Quality-first — only top-tier models (Sonnet 4.6, GPT-5.4, Grok 4.2, Gemini 3.1 Pro).

**Model stack:** Sonnet 4.6 orchestrator + GPT-5.4 workers + GPT-5.4 for simple queries.

## The Model Decision (Why This Won)

Tested 9 combinations across 10,000 simulated users per persona. All configs restricted to premium models — no Haiku, Flash, or mini models because financial analysis quality must be trusted when real money is at stake.

| Rank | Config | Gross Margin | Profit @ 1K users |
|------|--------|-------------|-------------------|
| 1 | GPT-5.4 everything | 72.6% | $40,664/mo |
| 2 | GPT-5.4 orch + Grok workers | 68.8% | $38,522/mo |
| 3 | **Sonnet orch + GPT-5.4 workers** | **66.1%** | **$37,000/mo** |
| 4 | Gemini 3.1 everything | 53.7% | $30,060/mo |
| 9 | Sonnet everything (baseline) | 27.0% | $15,125/mo |

**Selected: Sonnet orch + GPT-5.4 workers + GPT-5.4 simple.** Pure GPT-5.4 had the highest margin, but Sonnet 4.6 is Anthropic's purpose-built agentic reasoning model — the planning role benefits from its task decomposition quality. The ~$3.6k/mo margin delta buys orchestration quality where it matters most.

## What You're Billing On

**Chat messages** = one user turn in the Atlas interface. User sends a message, gets an answer. Everything happening under the hood (tool calls, iterations, worker spawning) is part of that single message. Simple and easy to count.

**Watchlists** = AI-generated thematic watchlists. Fixed $3 COGS each.

**Builders** = strategy / indicator / signal / execution builders. Fixed $4 COGS each.

## Chat Message Economics

Under the hood, a chat message can trigger two different paths:
- **Simple path** (~95% of messages): direct agent call with tools → mean $0.066/message
- **Planned path** (~5% of messages): spawns workers for deep research → mean $2.54/message

User doesn't see this split. They just see "messages used: X of Y."

**Empirical persona usage (10,000-user Monte Carlo):**

| Persona | Chat messages/mo (median) | Monthly chat cost (median) | Monthly chat cost (mean) |
|---------|--------------------------|---------------------------|-------------------------|
| **Casual retail** | 25 | $6.77 | $8.10 |
| **Active trader** | 105 | $23.70 | $25.83 |
| **Power user** | 333 | $60.67 | $62.99 |

(Costs include $4/mo fixed infrastructure.)

## The Pricing Plan

```
┌──────────────────────────────────────────────────────────────────────┐
│  FREE                                                                │
│  $0/mo                                                               │
│                                                                      │
│  • 25 chat messages                                                  │
│  • 1 watchlist                                                       │
│  • 0 builders                                                        │
│                                                                      │
│  COGS if maxed:  ~$12 (loss leader, acquisition)                    │
├──────────────────────────────────────────────────────────────────────┤
│  STARTER — $29/mo                                                    │
│  Target: casual retail, checks portfolio weekly                      │
│                                                                      │
│  • 100 chat messages                                                 │
│  • 2 watchlists                                                      │
│  • 0 builders                                                        │
│                                                                      │
│  TYPICAL COGS (casual persona, 60% util):                            │
│    Chat:        $8.10  (mean chat cost incl fixed)                  │
│    Watchlists:  $3.00  (1 × $3)                                      │
│    ─────────────────                                                 │
│    TOTAL:       $11.10  →  Margin: 62%                              │
│                                                                      │
│  MAX COGS (100% utilization):                                        │
│    Chat max:    $23.00 (100 msg × $0.19 blended mean + $4 fixed)    │
│    Watchlists:  $6.00  (2 × $3)                                      │
│    ─────────────────                                                 │
│    TOTAL:       $29.00  →  Margin: 0% (break-even, overage kicks in) │
├──────────────────────────────────────────────────────────────────────┤
│  PRO — $79/mo                                                        │
│  Target: active retail trader, several sessions per week             │
│                                                                      │
│  • 300 chat messages                                                 │
│  • 5 watchlists                                                      │
│  • 2 builders                                                        │
│                                                                      │
│  TYPICAL COGS (active persona, 60% util):                            │
│    Chat:        $25.83                                               │
│    Watchlists:  $9.00   (3 × $3)                                     │
│    Builders:    $4.00   (1 × $4)                                     │
│    ─────────────────                                                 │
│    TOTAL:       $38.83  →  Margin: 51%                              │
│                                                                      │
│  MAX COGS (100% utilization):                                        │
│    Chat max:    $61.00  (300 msg × $0.19 + $4 fixed)                │
│    Watchlists:  $15.00  (5 × $3)                                     │
│    Builders:    $8.00   (2 × $4)                                     │
│    ─────────────────                                                 │
│    TOTAL:       $84.00  →  Margin: -6% (overage covers excess)      │
├──────────────────────────────────────────────────────────────────────┤
│  POWER — $179/mo                                                     │
│  Target: daily retail power user, multiple portfolios                │
│                                                                      │
│  • 800 chat messages                                                 │
│  • 12 watchlists                                                     │
│  • 5 builders                                                        │
│                                                                      │
│  TYPICAL COGS (power persona, 60% util):                             │
│    Chat:        $62.99                                               │
│    Watchlists:  $21.00  (7 × $3)                                     │
│    Builders:    $12.00  (3 × $4)                                     │
│    ─────────────────                                                 │
│    TOTAL:       $95.99  →  Margin: 46%                              │
│                                                                      │
│  MAX COGS (100% utilization):                                        │
│    Chat max:    $156.00 (800 msg × $0.19 + $4 fixed)                 │
│    Watchlists:  $36.00  (12 × $3)                                    │
│    Builders:    $20.00  (5 × $4)                                     │
│    ─────────────────                                                 │
│    TOTAL:       $212.00 →  Margin: -18% (overage covers excess)     │
└──────────────────────────────────────────────────────────────────────┘

OVERAGE PRICING (after limits exceeded):
  Chat message:  $0.50 each  (2.6x blended cost)
  Watchlist:     $5.00 each  (1.7x cost)
  Builder:       $6.00 each  (1.5x cost)

MONTHLY SPEND CAP (per user):
  Default: 2x subscription price (user-configurable)
  Prevents runaway bills on both sides
```

## Blended Revenue Model @ 1,000 Users

Assumed user mix: 60% Starter / 30% Pro / 10% Power

| Segment | # Users | Tier | Typical Cost/user | Revenue/mo | COGS/mo |
|---------|---------|------|------------------|-----------|---------|
| Casual retail | 600 | Starter ($29) | $11.10 | $17,400 | $6,660 |
| Active trader | 300 | Pro ($79) | $38.83 | $23,700 | $11,649 |
| Power user | 100 | Power ($179) | $95.99 | $17,900 | $9,599 |
| **Totals** | **1,000** | — | — | **$59,000** | **$27,908** |

**Gross profit: $31,092/mo | Gross margin: 53% | Annual run-rate: $708,000**

## Why Max-Usage Margins Look Bad (And Why It's Fine)

At 100% utilization, margins drop to break-even or negative. That's by design:

1. **Simulation shows users typically use 25-40% of limits** — power users hitting 60-80% is rare
2. **Overage pricing restores margin on excess usage** — the $0.50/message overage is 2.6x blended cost, so every overage message is a ~60% margin sale
3. **Spend caps bound worst case** at 2x subscription
4. **Simulation shows >95% of each persona is profitable at their recommended tier** even accounting for variance

## Critical Implementation Requirements

1. **Model router** — routes orchestrator to Sonnet 4.6, workers to GPT-5.4, simple queries to GPT-5.4
2. **Message counter in UI** — "X of Y messages used this month"
3. **Watchlist & builder counters** — separate meters
4. **Overage billing via Stripe** metered pricing
5. **Hard spend cap** (user-configurable)
6. **Auto-upgrade suggestion** after 2 months of consistent tier overage

## Launch Strategy

Ship with four tiers (Free, Starter, Pro, Power). Annual pricing at 20% discount. Monitor first 90 days for actual vs simulated usage — adjust limits if margins are too fat, increase overage rates if margins are too thin.

Starting prices: $0 / $29 / $79 / $179.

## Files (all in this directory: `docs/business/`)

- `user_simulator.py` — Monte Carlo simulator (run with `python user_simulator.py`)
- `compare_configs.py` — model config comparison harness
- `simulator_results.json` — latest run results
- `unit_economics.py` — per-trace cost report, mixed-model combos (historical)
- `business_analytics.py` — deep analysis: distributions, drivers, concentration
- `download_langfuse_data.py` — refresh Langfuse data (run to update `langfuse_data/`)
- `langfuse_data/` — weekly JSON dumps of Langfuse traces
