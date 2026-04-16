"""
Run the user simulator across all model configs and rank them.

Outputs a single comparison table showing:
- Chat cost per persona for each config
- Business economics at 1,000 users
- Profitability at each tier
"""

import random
import sys
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")

from user_simulator import (
    MODEL_CONFIGS,
    PERSONAS,
    PRICING_TIERS,
    FIXED_COST_PER_USER,
    OVERAGE_QUERY,
    OVERAGE_ANALYSIS,
    simulate_persona,
    percentile,
)


def run_config(config_name: str, config: dict, n_users: int = 10000) -> dict:
    """Run all personas for one config and return aggregated results."""

    results = {}

    for persona in PERSONAS:
        sims = simulate_persona(persona, config, n_users)
        results[persona.name] = {
            "cost_p50": percentile([r.total_cost for r in sims], 50),
            "cost_p90": percentile([r.total_cost for r in sims], 90),
            "cost_mean": mean([r.total_cost for r in sims]),
            "sims": sims,
        }

    # Business model projection: 60/30/10 mix
    mix = {
        "casual_retail": {"tier_name": "Starter", "pct": 60},
        "active_trader": {"tier_name": "Pro", "pct": 30},
        "power_user":    {"tier_name": "Power", "pct": 10},
    }

    total_rev = 0.0
    total_cogs = 0.0

    for persona_name, segment in mix.items():
        if persona_name not in results:
            continue

        sims = results[persona_name]["sims"]
        tier = next(t for t in PRICING_TIERS if t["name"] == segment["tier_name"])
        n_users_seg = int(1000 * segment["pct"] / 100)

        seg_rev = 0.0
        seg_cost = 0.0

        for r in sims[:n_users_seg] if len(sims) >= n_users_seg else sims:
            q_over = max(0, r.total_queries - tier["query_limit"]) * OVERAGE_QUERY
            a_over = max(0, r.total_analyses - tier["analysis_limit"]) * OVERAGE_ANALYSIS
            seg_rev += tier["price"] + q_over + a_over
            seg_cost += r.total_cost

        sample = min(n_users_seg, len(sims))
        avg_rev = seg_rev / sample
        avg_cost = seg_cost / sample

        total_rev += avg_rev * n_users_seg
        total_cogs += avg_cost * n_users_seg

    gross_profit = total_rev - total_cogs
    margin = gross_profit / total_rev * 100 if total_rev > 0 else 0

    return {
        "config_name": config_name,
        "description": config["description"],
        "casual_p50": results["casual_retail"]["cost_p50"],
        "casual_mean": results["casual_retail"]["cost_mean"],
        "active_p50": results["active_trader"]["cost_p50"],
        "active_mean": results["active_trader"]["cost_mean"],
        "power_p50": results["power_user"]["cost_p50"],
        "power_mean": results["power_user"]["cost_mean"],
        "total_mrr": total_rev,
        "total_cogs": total_cogs,
        "gross_profit": gross_profit,
        "margin": margin,
    }


def main():
    random.seed(42)

    print("\n" + "#" * 85)
    print("#  MODEL CONFIG COMPARISON — Top-tier models only (Sonnet/Grok/GPT-5.4/Gemini 3.1)")
    print("#  Simulating 10,000 users per persona per config")
    print("#  Retail-only business model (Starter 60% / Pro 30% / Power 10%)")
    print("#" * 85)

    all_results = []

    for config_name, config in MODEL_CONFIGS.items():
        result = run_config(config_name, config, n_users=10000)
        all_results.append(result)

    # Sort by gross profit
    all_results.sort(key=lambda r: r["gross_profit"], reverse=True)

    print(f"\n{'CHAT COST PER USER (median/mo)':<80}")
    print(f"{'-' * 85}")
    print(f"  {'Config':<25} {'Casual':>10} {'Active':>10} {'Power':>10}")
    print(f"  {'-' * 55}")

    for r in all_results:
        print(f"  {r['config_name']:<25} ${r['casual_p50']:>9.2f} ${r['active_p50']:>9.2f} ${r['power_p50']:>9.2f}")

    print(f"\n{'BUSINESS ECONOMICS AT 1,000 USERS':<80}")
    print(f"{'-' * 85}")
    print(f"  {'Config':<25} {'MRR':>10} {'COGS':>10} {'Profit':>10} {'Margin':>8}")
    print(f"  {'-' * 67}")

    for r in all_results:
        print(f"  {r['config_name']:<25} ${r['total_mrr']:>9,.0f} ${r['total_cogs']:>9,.0f} ${r['gross_profit']:>9,.0f} {r['margin']:>7.1f}%")

    # Winner
    winner = all_results[0]
    print(f"\n\n{'=' * 85}")
    print(f"  🏆 WINNER: {winner['config_name']}")
    print(f"  {winner['description']}")
    print(f"{'=' * 85}")
    print(f"  Gross profit at 1,000 users:  ${winner['gross_profit']:,.0f}/mo")
    print(f"  Gross margin:                  {winner['margin']:.1f}%")
    print(f"  Annual run-rate:               ${winner['total_mrr'] * 12:,.0f}")
    print()
    print(f"  Cost per user (median):")
    print(f"    Casual retail:   ${winner['casual_p50']:.2f}/mo (mean ${winner['casual_mean']:.2f})")
    print(f"    Active trader:   ${winner['active_p50']:.2f}/mo (mean ${winner['active_mean']:.2f})")
    print(f"    Power user:      ${winner['power_p50']:.2f}/mo (mean ${winner['power_mean']:.2f})")


if __name__ == "__main__":
    main()
