"""
Layer 1 Statistical User Simulator for ProphitAI Unit Economics.

Monte Carlo simulation of retail user behavior to validate pricing tiers.

Uses:
- EMPIRICAL cost distributions from real Langfuse traces (accurate)
- ASSUMED usage patterns based on industry benchmarks (best guess)

Output:
- Monthly cost distribution per persona
- % of users profitable at each tier
- Recommended overage pricing based on P95 costs

Usage:
    python user_simulator.py                    # default 10,000 users per persona
    python user_simulator.py --users 5000       # custom sample size
    python user_simulator.py --model optimized  # pricing config
"""

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")


# ================================
# --> Persona definitions
# ================================

@dataclass
class Persona:
    """Retail user archetype with behavioral parameters."""

    name: str
    description: str
    sessions_per_month_mean: float
    queries_per_session_mean: float
    queries_per_session_stdev: float
    analyses_per_month_mean: float


PERSONAS = [
    Persona(
        name="casual_retail",
        description="Checks portfolio weekly, reads news, asks basic questions",
        sessions_per_month_mean=8,
        queries_per_session_mean=3,
        queries_per_session_stdev=1,
        analyses_per_month_mean=1,
    ),
    Persona(
        name="active_trader",
        description="Logs in several times per week, trades actively, uses research tools",
        sessions_per_month_mean=20,
        queries_per_session_mean=5,
        queries_per_session_stdev=1.5,
        analyses_per_month_mean=6,
    ),
    Persona(
        name="power_user",
        description="Daily user, multiple portfolios, heavy research and construction",
        sessions_per_month_mean=40,
        queries_per_session_mean=8,
        queries_per_session_stdev=2,
        analyses_per_month_mean=15,
    ),
]


# ================================
# --> Pricing config
# ================================

# Cost model assumptions (these can change via --model flag)
MODEL_CONFIGS = {
    # TOP-TIER ONLY — Sonnet 4.6, Grok 4.2, GPT-5.4, Gemini 3.1 Pro
    # Financial analysis requires reasoning quality users trust with real money.
    # Cost values: empirical from Langfuse where available, else estimated from
    # token profile × model pricing.
    "sonnet_only": {
        "description": "Sonnet 4.6 everything (premium baseline)",
        "simple_median": 0.113,
        "simple_p90": 0.678,
        "planned_median": 2.13,
        "planned_p90": 7.85,
    },
    "sonnet_grok": {
        "description": "Sonnet 4.6 orch + Grok 4.2 workers (EMPIRICAL)",
        "simple_median": 0.113,
        "simple_p90": 0.678,
        "planned_median": 1.98,
        "planned_p90": 6.30,
    },
    "sonnet_gpt54": {
        "description": "Sonnet 4.6 orch + GPT-5.4 workers",
        "simple_median": 0.113,
        "simple_p90": 0.678,
        "planned_median": 1.51,
        "planned_p90": 5.57,
    },
    "sonnet_gemini31": {
        "description": "Sonnet 4.6 orch + Gemini 3.1 Pro workers",
        "simple_median": 0.113,
        "simple_p90": 0.678,
        "planned_median": 1.81,
        "planned_p90": 6.67,
    },
    "gpt54_only": {
        "description": "GPT-5.4 everything",
        "simple_median": 0.03,
        "simple_p90": 0.15,
        "planned_median": 0.98,
        "planned_p90": 3.61,
    },
    "gemini31_only": {
        "description": "Gemini 3.1 Pro everything",
        "simple_median": 0.06,
        "simple_p90": 0.35,
        "planned_median": 1.56,
        "planned_p90": 5.73,
    },
    "gemini31_grok": {
        "description": "Gemini 3.1 Pro orch + Grok 4.2 workers",
        "simple_median": 0.06,
        "simple_p90": 0.35,
        "planned_median": 1.64,
        "planned_p90": 6.05,
    },
    "hybrid_sonnet_orch_gpt54_worker_gpt54_simple": {
        "description": "Sonnet orch + GPT-5.4 workers + GPT-5.4 simple (best hybrid)",
        "simple_median": 0.03,
        "simple_p90": 0.15,
        "planned_median": 1.51,
        "planned_p90": 5.57,
    },
    "gpt54_orch_grok_worker": {
        "description": "GPT-5.4 orch + Grok 4.2 workers + GPT-5.4 simple",
        "simple_median": 0.03,
        "simple_p90": 0.15,
        "planned_median": 1.24,
        "planned_p90": 4.60,
    },
}

# Fixed infrastructure cost per user per month
FIXED_COST_PER_USER = 4.0

# Pricing tiers (retail only, single chat-message counter)
PRICING_TIERS = [
    {"name": "Free",    "price":   0, "message_limit":  25, "watchlist_limit":  1, "builder_limit": 0},
    {"name": "Starter", "price":  29, "message_limit": 100, "watchlist_limit":  2, "builder_limit": 0},
    {"name": "Pro",     "price":  79, "message_limit": 300, "watchlist_limit":  5, "builder_limit": 2},
    {"name": "Power",   "price": 179, "message_limit": 800, "watchlist_limit": 12, "builder_limit": 5},
]

# Overage rates
OVERAGE_MESSAGE = 0.50   # per chat message over limit (~2.5x blended mean cost)
OVERAGE_WATCHLIST = 5.00  # per watchlist over limit (~1.67x cost)
OVERAGE_BUILDER = 6.00    # per builder over limit (~1.5x cost)

# Feature COGS (fixed per unit)
WATCHLIST_COGS = 3.00
BUILDER_COGS = 4.00


# ================================
# --> Helper funcs
# ================================

def poisson(mean_val: float) -> int:
    """Simple Poisson random draw using Knuth's algorithm."""

    import math

    l = math.exp(-mean_val)
    k = 0
    p = 1.0

    while p > l:
        k += 1
        p *= random.random()

    return k - 1


def sample_cost_lognormal(median_cost: float, p90_cost: float) -> float:
    """Sample a single run cost from a log-normal distribution.

    Uses median and P90 to fit the distribution's shape — matches the
    long-tail pattern observed in real Langfuse data.
    """

    import math

    # Reason: for log-normal, median = exp(mu), so mu = ln(median)
    # P90 = exp(mu + 1.2816 * sigma), so sigma = (ln(P90) - mu) / 1.2816
    if median_cost <= 0:
        return 0.0

    mu = math.log(median_cost)

    if p90_cost <= median_cost:
        return median_cost

    sigma = (math.log(p90_cost) - mu) / 1.2816

    # Sample from N(mu, sigma), then exp
    normal_sample = random.gauss(mu, sigma)
    return math.exp(normal_sample)


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0

    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)

    return s[f] + (s[c] - s[f]) * (k - f)


# ================================
# --> Core simulation
# ================================

@dataclass
class UserMonthResult:
    """Outcome of simulating one user for one month.

    Chat messages are counted as a single user-facing metric.
    Internally some messages trigger the simple agent (cheap),
    others trigger the planned agent with workers (expensive),
    but the user just sees 'chat messages'.
    """

    persona: str
    total_messages: int
    simple_messages: int
    planned_messages: int
    total_sessions: int
    chat_cost: float
    fixed_cost: float
    total_cost: float

    # Compat aliases
    @property
    def total_queries(self) -> int:
        return self.simple_messages

    @property
    def total_analyses(self) -> int:
        return self.planned_messages

    @property
    def query_cost(self) -> float:
        return self.chat_cost  # not split anymore

    @property
    def analysis_cost(self) -> float:
        return 0.0


def simulate_user_month(persona: Persona, config: dict) -> UserMonthResult:
    """Run a single Monte Carlo iteration for one user over one month.

    Models total chat messages (user turns). Each message is classified
    internally as simple (single agent) or planned (spawns workers) based
    on complexity, but the user-facing counter is just 'messages'.
    """

    sessions = max(1, poisson(persona.sessions_per_month_mean))
    simple_messages = 0
    planned_messages = 0
    chat_cost = 0.0

    for _ in range(sessions):
        q_count = max(1, round(random.gauss(persona.queries_per_session_mean, persona.queries_per_session_stdev)))

        for _ in range(q_count):
            simple_messages += 1
            chat_cost += sample_cost_lognormal(config["simple_median"], config["simple_p90"])

    # Planned-type messages (complex research requests) spread across the month
    planned_count = poisson(persona.analyses_per_month_mean)

    for _ in range(planned_count):
        planned_messages += 1
        chat_cost += sample_cost_lognormal(config["planned_median"], config["planned_p90"])

    total_messages = simple_messages + planned_messages
    total_cost = chat_cost + FIXED_COST_PER_USER

    return UserMonthResult(
        persona=persona.name,
        total_messages=total_messages,
        simple_messages=simple_messages,
        planned_messages=planned_messages,
        total_sessions=sessions,
        chat_cost=chat_cost,
        fixed_cost=FIXED_COST_PER_USER,
        total_cost=total_cost,
    )


def simulate_persona(persona: Persona, config: dict, n_users: int) -> list[UserMonthResult]:
    """Simulate N users over one month for a persona."""

    return [simulate_user_month(persona, config) for _ in range(n_users)]


# ================================
# --> Analysis & reporting
# ================================

def print_persona_summary(persona: Persona, results: list[UserMonthResult]) -> None:
    """Print distribution summary for one persona."""

    print(f"\n{'=' * 75}")
    print(f"  PERSONA: {persona.name.upper()}")
    print(f"  {persona.description}")
    print(f"  Expected usage: {persona.sessions_per_month_mean:.0f} sessions/mo, "
          f"{persona.queries_per_session_mean:.0f} queries/session, "
          f"{persona.analyses_per_month_mean:.0f} analyses/mo")
    print(f"{'=' * 75}")

    total_costs = [r.total_cost for r in results]
    total_messages = [r.total_messages for r in results]
    simple_messages = [r.simple_messages for r in results]
    planned_messages = [r.planned_messages for r in results]

    print(f"\n  USAGE DISTRIBUTION (n={len(results)} simulated users)")
    print(f"  {'Metric':<25} {'P25':>10} {'P50':>10} {'P75':>10} {'P90':>10} {'P95':>10}")
    print(f"  {'-' * 78}")

    def row(label, data):
        p25 = percentile(data, 25)
        p50 = percentile(data, 50)
        p75 = percentile(data, 75)
        p90 = percentile(data, 90)
        p95 = percentile(data, 95)
        print(f"  {label:<25} {p25:>10.1f} {p50:>10.1f} {p75:>10.1f} {p90:>10.1f} {p95:>10.1f}")

    row("Chat messages/month", total_messages)
    row("  (simple under hood)", simple_messages)
    row("  (planned under hood)", planned_messages)

    print()
    print(f"  MONTHLY COST DISTRIBUTION")
    print(f"  {'Percentile':<12} {'Cost':>10}")
    print(f"  {'-' * 24}")

    for p in [10, 25, 50, 75, 90, 95, 99]:
        print(f"  P{p:<11} ${percentile(total_costs, p):>9.2f}")

    print(f"  {'Mean':<12} ${mean(total_costs):>9.2f}")
    print(f"  {'Max':<12} ${max(total_costs):>9.2f}")


def print_tier_analysis(persona: Persona, results: list[UserMonthResult]) -> None:
    """Analyze margin at each tier for this persona.

    Uses single chat-message counter. Assumes persona-typical watchlist/builder use
    included within tier limits (no overage on those features in this analysis).
    """

    print(f"\n  TIER ANALYSIS for {persona.name}")
    print(f"  {'Tier':<14} {'Price':>7} {'Cost P50':>10} {'Cost P95':>10} {'Margin P50':>12} {'Margin P95':>12} {'% Profitable':>14}")
    print(f"  {'-' * 85}")

    for tier in PRICING_TIERS:
        if tier["price"] == 0:
            continue

        effective_costs = []

        for r in results:
            # Message overage
            msg_overage_count = max(0, r.total_messages - tier["message_limit"])
            msg_overage_charge = msg_overage_count * OVERAGE_MESSAGE

            effective_revenue = tier["price"] + msg_overage_charge
            actual_cost = r.total_cost

            margin = (effective_revenue - actual_cost) / effective_revenue * 100 if effective_revenue > 0 else 0

            effective_costs.append({
                "revenue": effective_revenue,
                "cost": actual_cost,
                "margin": margin,
                "profitable": effective_revenue > actual_cost,
            })

        margins = [ec["margin"] for ec in effective_costs]
        costs = [ec["cost"] for ec in effective_costs]
        profitable_pct = sum(1 for ec in effective_costs if ec["profitable"]) / len(effective_costs) * 100

        print(
            f"  {tier['name']:<14} ${tier['price']:>6} "
            f"${percentile(costs, 50):>9.2f} ${percentile(costs, 95):>9.2f} "
            f"{percentile(margins, 50):>11.0f}% {percentile(margins, 5):>11.0f}% "
            f"{profitable_pct:>13.1f}%"
        )


def recommend_tier(persona: Persona, results: list[UserMonthResult]) -> dict:
    """Recommend the best tier for this persona based on simulation."""

    scores = {}

    for tier in PRICING_TIERS:
        if tier["price"] == 0:
            continue

        profitable = 0

        for r in results:
            msg_overage = max(0, r.total_messages - tier["message_limit"]) * OVERAGE_MESSAGE
            revenue = tier["price"] + msg_overage

            if revenue > r.total_cost:
                profitable += 1

        pct = profitable / len(results)
        scores[tier["name"]] = {"tier": tier, "profitable_pct": pct}

    return scores


def print_launch_recommendation(persona_results: dict, config_name: str) -> None:
    """Synthesize pricing recommendation across all personas."""

    print(f"\n\n{'=' * 75}")
    print(f"  LAUNCH RECOMMENDATION ({config_name} model config)")
    print(f"{'=' * 75}")

    for persona_name, results in persona_results.items():
        scores = recommend_tier(None, results)

        print(f"\n  {persona_name}:")

        for tier_name, s in scores.items():
            emoji = "✓" if s["profitable_pct"] > 0.9 else ("~" if s["profitable_pct"] > 0.7 else "✗")
            print(f"    {emoji} {tier_name:<10} (${s['tier']['price']}): {s['profitable_pct']*100:.0f}% profitable")

    print()
    print("  INTERPRETATION:")
    print("    ✓ = >90% profitable (safe to sell this tier to this persona)")
    print("    ~ = 70-90% profitable (marginal — depends on retention)")
    print("    ✗ = <70% profitable (losing money on this segment)")


def print_blended_economics(persona_results: dict, config_name: str) -> None:
    """Project business economics with a realistic persona mix."""

    print(f"\n\n{'=' * 75}")
    print(f"  BUSINESS MODEL PROJECTION (1,000 paid users)")
    print(f"{'=' * 75}")

    # Assumed user mix
    mix = {
        "casual_retail": {"tier": "Starter", "pct": 60, "assigned_price": 29},
        "active_trader": {"tier": "Pro",     "pct": 30, "assigned_price": 79},
        "power_user":    {"tier": "Power",   "pct": 10, "assigned_price": 149},
    }

    total_revenue = 0.0
    total_cost = 0.0

    print(f"\n  Assumed mix: 60% Starter, 30% Pro, 10% Power")
    print(f"  {'Segment':<20} {'Users':>7} {'Tier':<10} {'Price':>7} {'Avg cost':>10} {'Revenue':>10} {'Cost':>10}")

    for persona_name, segment in mix.items():
        if persona_name not in persona_results:
            continue

        results = persona_results[persona_name]
        n_users = int(1000 * segment["pct"] / 100)

        # Find the tier
        tier = next(t for t in PRICING_TIERS if t["name"] == segment["tier"])

        # Compute avg cost per user including overages
        segment_revenue = 0
        segment_cost = 0

        for r in results[:n_users] if len(results) >= n_users else results:
            msg_overage = max(0, r.total_messages - tier["message_limit"]) * OVERAGE_MESSAGE
            revenue = tier["price"] + msg_overage
            segment_revenue += revenue
            segment_cost += r.total_cost

        # Scale to full n_users
        sample_size = min(n_users, len(results))
        avg_rev = segment_revenue / sample_size
        avg_cost = segment_cost / sample_size

        segment_revenue_total = avg_rev * n_users
        segment_cost_total = avg_cost * n_users

        total_revenue += segment_revenue_total
        total_cost += segment_cost_total

        print(
            f"  {persona_name:<20} {n_users:>7} {segment['tier']:<10} "
            f"${segment['assigned_price']:>6} ${avg_cost:>9.2f} "
            f"${segment_revenue_total:>9.0f} ${segment_cost_total:>9.0f}"
        )

    profit = total_revenue - total_cost
    margin = profit / total_revenue * 100 if total_revenue > 0 else 0

    print(f"\n  TOTAL MRR:        ${total_revenue:>10,.0f}")
    print(f"  TOTAL COGS:       ${total_cost:>10,.0f}")
    print(f"  GROSS PROFIT:     ${profit:>10,.0f}")
    print(f"  GROSS MARGIN:     {margin:>10.1f}%")
    print(f"  ANNUAL RUN-RATE:  ${total_revenue * 12:>10,.0f}")


# ================================
# --> Main
# ================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=10000, help="Simulated users per persona")
    parser.add_argument("--model", choices=list(MODEL_CONFIGS.keys()), default="optimized",
                        help="Model routing config")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    config = MODEL_CONFIGS[args.model]

    print(f"\n{'#' * 75}")
    print(f"#  PROPHITAI USER SIMULATOR — LAYER 1 (statistical)")
    print(f"#  Model config: {args.model} — {config['description']}")
    print(f"#  Simulating {args.users:,} users per persona ({len(PERSONAS)} personas)")
    print(f"#  Fixed cost per user: ${FIXED_COST_PER_USER}/mo")
    print(f"{'#' * 75}")

    persona_results = {}

    for persona in PERSONAS:
        results = simulate_persona(persona, config, args.users)
        persona_results[persona.name] = results

        print_persona_summary(persona, results)
        print_tier_analysis(persona, results)

    print_launch_recommendation(persona_results, args.model)
    print_blended_economics(persona_results, args.model)

    # Save raw results for further analysis
    output = {
        "config": args.model,
        "config_details": config,
        "users_per_persona": args.users,
        "fixed_cost_per_user": FIXED_COST_PER_USER,
        "personas": {
            persona.name: {
                "description": persona.description,
                "params": {
                    "sessions_per_month_mean": persona.sessions_per_month_mean,
                    "queries_per_session_mean": persona.queries_per_session_mean,
                    "analyses_per_month_mean": persona.analyses_per_month_mean,
                },
                "cost_percentiles": {
                    f"P{p}": percentile([r.total_cost for r in persona_results[persona.name]], p)
                    for p in [10, 25, 50, 75, 90, 95, 99]
                },
                "avg_queries": mean([r.total_queries for r in persona_results[persona.name]]),
                "avg_analyses": mean([r.total_analyses for r in persona_results[persona.name]]),
            }
            for persona in PERSONAS
        },
    }

    output_path = Path(__file__).parent / "simulator_results.json"

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n\nRaw results saved to {output_path.name}")


if __name__ == "__main__":
    main()
