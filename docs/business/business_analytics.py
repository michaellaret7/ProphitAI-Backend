"""
Deep analytics on Langfuse data for business model decisions.

Runs 7 analyses:
1. Cost distribution (percentiles)
2. Cost driver correlation (what makes runs expensive)
3. Usage patterns over time
4. Whale analysis (cost concentration)
5. Optimal model-per-role matrix
6. Pricing scenario margin analysis
7. Break-even & sensitivity analysis
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev

sys.stdout.reconfigure(encoding="utf-8")


# ================================
# --> Pricing config (same as unit_economics.py)
# ================================

PRICING = {
    "claude-sonnet-4-6":  {"input": 3.00,  "output": 15.00, "cache_create": 3.75, "cache_read": 0.30},
    "claude-opus-4-6":    {"input": 15.00, "output": 75.00, "cache_create": 18.75, "cache_read": 1.50},
    "claude-haiku-4-5":   {"input": 0.80,  "output": 4.00,  "cache_create": 1.00, "cache_read": 0.08},
    "gpt-4o":             {"input": 2.50,  "output": 10.00, "cache_create": 0,    "cache_read": 1.25},
    "gpt-4o-mini":        {"input": 0.15,  "output": 0.60,  "cache_create": 0,    "cache_read": 0.075},
    "gpt-4.1":            {"input": 2.00,  "output": 8.00,  "cache_create": 0,    "cache_read": 0.50},
    "gpt-4.1-mini":       {"input": 0.40,  "output": 1.60,  "cache_create": 0,    "cache_read": 0.10},
    "gemini-2.5-pro":     {"input": 1.25,  "output": 10.00, "cache_create": 0,    "cache_read": 0.315},
    "gemini-2.5-flash":   {"input": 0.15,  "output": 0.60,  "cache_create": 0,    "cache_read": 0.0375},
    "gemini-2.0-flash":   {"input": 0.10,  "output": 0.40,  "cache_create": 0,    "cache_read": 0.025},
    "grok-4.2":           {"input": 2.00,  "output": 6.00,  "cache_create": 0,    "cache_read": 0},
    "grok-3-mini":        {"input": 0.30,  "output": 0.50,  "cache_create": 0,    "cache_read": 0},
}

PERPLEXITY_COST = 0.005


# ================================
# --> Helper funcs
# ================================

def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def load_all_traces() -> list[dict]:
    data_dir = Path(__file__).parent / "langfuse_data"
    traces = []

    for f in sorted(data_dir.glob("*.json")):
        with open(f) as fh:
            traces.extend(json.load(fh))

    return traces


def classify_trace(t: dict) -> str:
    """Classify trace as simple or planned."""

    name = (t.get("name") or "").lower()

    if "planned" in name or "planner" in name or "orchestrator" in name:
        return "planned"

    return "simple"


def get_worker_obs_ids(observations: list) -> set[str]:
    """Find observation IDs inside a worker_agent.run subtree."""

    obs_by_id = {o["id"]: o for o in observations}
    worker_roots = {o["id"] for o in observations if "worker_agent" in (o.get("name") or "").lower()}
    worker_ids = set()

    for o in observations:
        current = o

        while current:
            if current["id"] in worker_roots:
                worker_ids.add(o["id"])
                break

            pid = current.get("parent_observation_id")

            if not pid or pid == current["id"]:
                break

            current = obs_by_id.get(pid)

    return worker_ids


def aggregate_tokens(observations: list, filter_ids: set[str] | None = None) -> dict:
    """Sum token counts across observations (optionally filtered to a set of IDs)."""

    agg = {"input": 0, "output": 0, "cc": 0, "cr": 0, "gens": 0}

    for o in observations:
        if o.get("type") != "GENERATION":
            continue

        if filter_ids is not None and o["id"] not in filter_ids:
            continue

        ud = o.get("usage_details") or {}
        agg["input"] += ud.get("input", 0) or 0
        agg["output"] += ud.get("output", 0) or 0
        agg["cc"] += ud.get("input_cache_creation", 0) or 0
        agg["cr"] += ud.get("input_cached_tokens", 0) or 0
        agg["gens"] += 1

    return agg


def cost_for_tokens(tokens: dict, model: str) -> float:
    p = PRICING[model]
    has_cache = p["cache_create"] > 0 or p["cache_read"] > 0

    if has_cache:
        return (
            (tokens["input"] / 1e6) * p["input"]
            + (tokens["output"] / 1e6) * p["output"]
            + (tokens["cc"] / 1e6) * p["cache_create"]
            + (tokens["cr"] / 1e6) * p["cache_read"]
        )

    total_in = tokens["input"] + tokens["cc"] + tokens["cr"]
    return (total_in / 1e6) * p["input"] + (tokens["output"] / 1e6) * p["output"]


def iter_count(t: dict) -> int:
    return sum(1 for o in t["observations"] if o.get("type") == "SPAN" and "iteration" in (o.get("name") or "").lower())


def worker_count(t: dict) -> int:
    return sum(1 for o in t["observations"] if "worker_agent" in (o.get("name") or "").lower())


def tool_count(t: dict) -> int:
    return sum(1 for o in t["observations"] if o.get("type") == "TOOL")


def web_search_count(t: dict) -> int:
    return sum(1 for o in t["observations"] if o.get("type") == "TOOL" and "web_search" in (o.get("name") or "").lower())


# ================================
# --> Analysis 1: Cost distribution
# ================================

def analyze_cost_distribution(traces: list[dict]) -> None:
    print("\n" + "=" * 75)
    print("  ANALYSIS 1: COST DISTRIBUTION (actual Langfuse costs)")
    print("=" * 75)

    simple = [t.get("total_cost", 0) for t in traces if classify_trace(t) == "simple" and t.get("total_cost", 0) > 0]
    planned = [t.get("total_cost", 0) for t in traces if classify_trace(t) == "planned" and t.get("total_cost", 0) > 0]
    all_costs = simple + planned

    def stats(name, data):
        if not data:
            return
        print(f"\n  {name} (n={len(data)})")
        print(f"    Mean:      ${mean(data):.4f}")
        print(f"    Stdev:     ${stdev(data):.4f}" if len(data) > 1 else "")
        print(f"    P5:        ${percentile(data, 5):.4f}")
        print(f"    P10:       ${percentile(data, 10):.4f}")
        print(f"    P25:       ${percentile(data, 25):.4f}")
        print(f"    P50 (med): ${percentile(data, 50):.4f}")
        print(f"    P75:       ${percentile(data, 75):.4f}")
        print(f"    P90:       ${percentile(data, 90):.4f}")
        print(f"    P95:       ${percentile(data, 95):.4f}")
        print(f"    P99:       ${percentile(data, 99):.4f}")
        print(f"    Max:       ${max(data):.4f}")

    stats("Simple Agent", simple)
    stats("Planned Agent", planned)
    stats("All Runs", all_costs)

    # Histogram
    buckets = [(0, 0.01), (0.01, 0.05), (0.05, 0.10), (0.10, 0.25), (0.25, 0.50),
               (0.50, 1.00), (1.00, 2.00), (2.00, 5.00), (5.00, 10.00), (10.00, 100.00)]

    print("\n  Distribution histogram (all runs):")
    print(f"  {'Range':<18} {'Count':>7} {'%':>6} Bar")

    for lo, hi in buckets:
        count = sum(1 for c in all_costs if lo <= c < hi)
        pct = count / len(all_costs) * 100 if all_costs else 0
        bar = "#" * int(pct / 2)
        print(f"  ${lo:>5.2f} - ${hi:>6.2f}  {count:>7} {pct:>5.1f}% {bar}")


# ================================
# --> Analysis 2: Cost drivers
# ================================

def analyze_cost_drivers(traces: list[dict]) -> None:
    print("\n\n" + "=" * 75)
    print("  ANALYSIS 2: COST DRIVERS (what makes a run expensive?)")
    print("=" * 75)

    planned = [t for t in traces if classify_trace(t) == "planned" and t.get("total_cost", 0) > 0]

    if not planned:
        print("  No planned traces with cost data")
        return

    # Bucket by iteration count
    iter_buckets = defaultdict(list)

    for t in planned:
        ic = iter_count(t)
        cost = t.get("total_cost", 0)

        if ic <= 5:
            iter_buckets["1-5 iters"].append(cost)
        elif ic <= 10:
            iter_buckets["6-10 iters"].append(cost)
        elif ic <= 20:
            iter_buckets["11-20 iters"].append(cost)
        elif ic <= 40:
            iter_buckets["21-40 iters"].append(cost)
        elif ic <= 80:
            iter_buckets["41-80 iters"].append(cost)
        else:
            iter_buckets["80+ iters"].append(cost)

    print("\n  Cost by iteration count (planned agents):")
    print(f"  {'Iterations':<15} {'Count':>7} {'Median':>10} {'Mean':>10} {'P90':>10}")

    for label in ["1-5 iters", "6-10 iters", "11-20 iters", "21-40 iters", "41-80 iters", "80+ iters"]:
        data = iter_buckets.get(label, [])

        if not data:
            continue

        print(f"  {label:<15} {len(data):>7} ${median(data):>9.3f} ${mean(data):>9.3f} ${percentile(data, 90):>9.3f}")

    # Bucket by worker count
    worker_buckets = defaultdict(list)

    for t in planned:
        wc = worker_count(t)
        cost = t.get("total_cost", 0)

        if wc == 0:
            worker_buckets["0 workers"].append(cost)
        elif wc <= 2:
            worker_buckets["1-2 workers"].append(cost)
        elif wc <= 4:
            worker_buckets["3-4 workers"].append(cost)
        elif wc <= 7:
            worker_buckets["5-7 workers"].append(cost)
        else:
            worker_buckets["8+ workers"].append(cost)

    print("\n  Cost by worker count (planned agents):")
    print(f"  {'Workers':<15} {'Count':>7} {'Median':>10} {'Mean':>10} {'P90':>10}")

    for label in ["0 workers", "1-2 workers", "3-4 workers", "5-7 workers", "8+ workers"]:
        data = worker_buckets.get(label, [])

        if not data:
            continue

        print(f"  {label:<15} {len(data):>7} ${median(data):>9.3f} ${mean(data):>9.3f} ${percentile(data, 90):>9.3f}")

    # Correlation: cost vs various features
    print("\n  Correlation of features with cost (Spearman-ish ranking):")

    features = {
        "iterations":    [(iter_count(t), t.get("total_cost", 0)) for t in planned],
        "workers":       [(worker_count(t), t.get("total_cost", 0)) for t in planned],
        "tool_calls":    [(tool_count(t), t.get("total_cost", 0)) for t in planned],
        "web_searches":  [(web_search_count(t), t.get("total_cost", 0)) for t in planned],
    }

    for fname, pairs in features.items():
        if not pairs:
            continue

        # Compute how cost scales with feature: compare avg cost at top
        # quartile vs bottom quartile of feature
        n = len(pairs)
        q = n // 4

        if q == 0:
            continue

        bottom_q_cost = mean([pairs[i][1] for i in range(q)])
        top_q_pairs = sorted(pairs, key=lambda x: x[0], reverse=True)[:q]
        top_q_cost = mean([p[1] for p in top_q_pairs])

        mult = top_q_cost / bottom_q_cost if bottom_q_cost > 0 else 0
        print(f"    {fname:<15} top quartile cost is {mult:.1f}x bottom quartile")


# ================================
# --> Analysis 3: Usage patterns over time
# ================================

def analyze_usage_patterns(traces: list[dict]) -> None:
    print("\n\n" + "=" * 75)
    print("  ANALYSIS 3: USAGE PATTERNS OVER TIME")
    print("=" * 75)

    daily = defaultdict(lambda: {"count": 0, "cost": 0.0, "simple": 0, "planned": 0})

    for t in traces:
        ts = t.get("timestamp", "")

        if not ts:
            continue

        try:
            day = ts[:10]
        except Exception:
            continue

        cost = t.get("total_cost", 0) or 0
        daily[day]["count"] += 1
        daily[day]["cost"] += cost

        if classify_trace(t) == "planned":
            daily[day]["planned"] += 1
        else:
            daily[day]["simple"] += 1

    sorted_days = sorted(daily.keys())

    print(f"\n  Daily traffic over {len(sorted_days)} days:")
    print(f"  {'Date':<12} {'Runs':>6} {'Simple':>7} {'Planned':>8} {'Total $':>10} {'Avg $':>9}")

    total_runs = 0
    total_cost = 0.0

    for day in sorted_days:
        d = daily[day]
        avg = d["cost"] / d["count"] if d["count"] > 0 else 0
        total_runs += d["count"]
        total_cost += d["cost"]
        print(f"  {day:<12} {d['count']:>6} {d['simple']:>7} {d['planned']:>8} ${d['cost']:>9.2f} ${avg:>8.3f}")

    print(f"\n  Totals:  {total_runs} runs, ${total_cost:.2f} total spend")
    print(f"  Avg per day:  {total_runs / max(len(sorted_days), 1):.1f} runs, ${total_cost / max(len(sorted_days), 1):.2f}")
    print(f"  Projected monthly (if current pace): ${total_cost / max(len(sorted_days), 1) * 30:.2f}")


# ================================
# --> Analysis 4: Whale / cost concentration
# ================================

def analyze_concentration(traces: list[dict]) -> None:
    print("\n\n" + "=" * 75)
    print("  ANALYSIS 4: COST CONCENTRATION (who drives the bill?)")
    print("=" * 75)

    costs = sorted([t.get("total_cost", 0) or 0 for t in traces], reverse=True)
    total = sum(costs)

    if total == 0:
        return

    print(f"\n  Total traces:     {len(costs)}")
    print(f"  Total cost:       ${total:.2f}")
    print()

    milestones = [1, 5, 10, 20, 50]

    print(f"  Cost concentration (top X% of runs):")
    print(f"  {'Top %':<10} {'# Runs':>8} {'Cost':>10} {'% of total':>12}")

    for pct in milestones:
        n = max(1, int(len(costs) * pct / 100))
        sub = costs[:n]
        sub_total = sum(sub)
        share = sub_total / total * 100
        print(f"  Top {pct}%{'':4} {n:>8} ${sub_total:>9.2f} {share:>11.1f}%")

    # Sessions by user
    print("\n  By session_id (user proxy):")

    by_session = defaultdict(lambda: {"runs": 0, "cost": 0.0})

    for t in traces:
        sid = t.get("session_id") or "no_session"
        by_session[sid]["runs"] += 1
        by_session[sid]["cost"] += t.get("total_cost", 0) or 0

    sorted_sessions = sorted(by_session.items(), key=lambda x: -x[1]["cost"])

    print(f"  {'Top 10 sessions':<40} {'Runs':>6} {'Cost':>10}")

    for sid, data in sorted_sessions[:10]:
        print(f"    {sid[:38]:<40} {data['runs']:>6} ${data['cost']:>9.2f}")

    # Power law: what % of sessions account for 80% of cost?
    cumulative = 0
    sessions_sorted = sorted(by_session.values(), key=lambda x: -x["cost"])

    for i, s in enumerate(sessions_sorted):
        cumulative += s["cost"]

        if cumulative >= total * 0.8:
            pct = (i + 1) / len(sessions_sorted) * 100
            print(f"\n  Pareto: {i + 1} sessions ({pct:.1f}% of total) drive 80% of cost")
            break


# ================================
# --> Analysis 5: Optimal model matrix
# ================================

def analyze_optimal_models(traces: list[dict]) -> None:
    print("\n\n" + "=" * 75)
    print("  ANALYSIS 5: OPTIMAL MODEL PER ROLE (cost comparison)")
    print("=" * 75)

    simple_traces = [t for t in traces if classify_trace(t) == "simple" and t.get("total_cost", 0) > 0]
    planned_traces = [t for t in traces if classify_trace(t) == "planned" and t.get("total_cost", 0) > 0]

    def model_costs_for_role(traces_list, worker_only=False, orch_only=False):
        """Compute avg/median cost if ALL generations in role ran on each model."""

        results = {}

        for model in PRICING.keys():
            costs = []

            for t in traces_list:
                worker_ids = get_worker_obs_ids(t["observations"])

                if worker_only:
                    tokens = aggregate_tokens(t["observations"], worker_ids)
                elif orch_only:
                    all_gen_ids = {o["id"] for o in t["observations"] if o.get("type") == "GENERATION"}
                    tokens = aggregate_tokens(t["observations"], all_gen_ids - worker_ids)
                else:
                    tokens = aggregate_tokens(t["observations"])

                if tokens["gens"] == 0:
                    continue

                costs.append(cost_for_tokens(tokens, model))

            if costs:
                results[model] = {
                    "median": median(costs),
                    "mean": mean(costs),
                    "p90": percentile(costs, 90),
                    "count": len(costs),
                }

        return results

    # Simple agents
    print("\n  SIMPLE AGENT — estimated cost if run on each model:")
    print(f"  {'Model':<25} {'Median':>10} {'Mean':>10} {'P90':>10}")

    simple_results = model_costs_for_role(simple_traces)

    for model, r in sorted(simple_results.items(), key=lambda x: x[1]["median"]):
        print(f"  {model:<25} ${r['median']:>9.4f} ${r['mean']:>9.4f} ${r['p90']:>9.4f}")

    # Orchestrator only
    print("\n  PLANNED AGENT ORCHESTRATOR — estimated cost if orchestrator ran on each model:")
    print(f"  {'Model':<25} {'Median':>10} {'Mean':>10} {'P90':>10}")

    orch_results = model_costs_for_role(planned_traces, orch_only=True)

    for model, r in sorted(orch_results.items(), key=lambda x: x[1]["median"]):
        print(f"  {model:<25} ${r['median']:>9.4f} ${r['mean']:>9.4f} ${r['p90']:>9.4f}")

    # Workers only
    print("\n  PLANNED AGENT WORKERS — estimated cost if workers ran on each model:")
    print(f"  {'Model':<25} {'Median':>10} {'Mean':>10} {'P90':>10}")

    worker_results = model_costs_for_role(planned_traces, worker_only=True)

    for model, r in sorted(worker_results.items(), key=lambda x: x[1]["median"]):
        print(f"  {model:<25} ${r['median']:>9.4f} ${r['mean']:>9.4f} ${r['p90']:>9.4f}")


# ================================
# --> Analysis 6: Pricing scenarios
# ================================

def analyze_pricing_scenarios(traces: list[dict]) -> None:
    print("\n\n" + "=" * 75)
    print("  ANALYSIS 6: PRICING SCENARIO MARGIN ANALYSIS")
    print("=" * 75)

    # Use the empirical median costs for realistic scenarios
    simple_traces = [t for t in traces if classify_trace(t) == "simple" and t.get("total_cost", 0) > 0]
    planned_traces = [t for t in traces if classify_trace(t) == "planned" and t.get("total_cost", 0) > 0]

    # Compute optimal-mix costs: Sonnet for simple, Sonnet orchestrator + Haiku workers for planned
    def mixed_cost(t, orch_model, worker_model):
        worker_ids = get_worker_obs_ids(t["observations"])
        all_gen_ids = {o["id"] for o in t["observations"] if o.get("type") == "GENERATION"}
        orch_tokens = aggregate_tokens(t["observations"], all_gen_ids - worker_ids)
        worker_tokens = aggregate_tokens(t["observations"], worker_ids)

        orch_cost = cost_for_tokens(orch_tokens, orch_model) if orch_tokens["gens"] > 0 else 0
        worker_cost = cost_for_tokens(worker_tokens, worker_model) if worker_tokens["gens"] > 0 else 0

        return orch_cost + worker_cost

    # Scenarios to test
    configs = {
        "current (all Sonnet)":      ("claude-sonnet-4-6", "claude-sonnet-4-6"),
        "optimized (Sonnet+Haiku)":  ("claude-sonnet-4-6", "claude-haiku-4-5"),
        "budget (Sonnet+Flash)":     ("claude-sonnet-4-6", "gemini-2.5-flash"),
        "aggressive (Grok+Grok)":    ("grok-4.2", "grok-4.2"),
        "ultra-budget (Pro+Flash)":  ("gemini-2.5-pro", "gemini-2.5-flash"),
    }

    print("\n  Cost per agent run under different model configs:")
    print(f"  {'Config':<30} {'Simple med':>12} {'Planned med':>13} {'Planned P90':>13}")

    config_costs = {}

    for name, (orch, worker) in configs.items():
        simple_costs = [cost_for_tokens(aggregate_tokens(t["observations"]), orch) for t in simple_traces]
        planned_costs = [mixed_cost(t, orch, worker) for t in planned_traces]
        simple_costs = [c for c in simple_costs if c > 0]
        planned_costs = [c for c in planned_costs if c > 0]

        if simple_costs and planned_costs:
            config_costs[name] = {
                "simple_med": median(simple_costs),
                "planned_med": median(planned_costs),
                "planned_p90": percentile(planned_costs, 90),
            }
            print(f"  {name:<30} ${config_costs[name]['simple_med']:>11.4f} ${config_costs[name]['planned_med']:>12.4f} ${config_costs[name]['planned_p90']:>12.4f}")

    # Pricing tier analysis
    print("\n\n  Tier margin analysis (using 'optimized' Sonnet+Haiku config):")

    opt = config_costs.get("optimized (Sonnet+Haiku)")

    if not opt:
        return

    s_med = opt["simple_med"]
    p_med = opt["planned_med"]
    p_p90 = opt["planned_p90"]

    tiers = [
        ("$29/mo Starter",  29,  100, 10,  3),
        ("$49/mo Plus",     49,  200, 15,  4),
        ("$79/mo Pro",      79,  400, 30,  5),
        ("$129/mo Prem",   129,  750, 60,  6),
        ("$199/mo Elite",  199, 1500, 100, 8),
    ]

    print(f"\n  {'Tier':<18} {'Q-lim':>6} {'A-lim':>6} {'Fixed':>6} {'Typ $':>8} {'Max $':>8} {'Typ margin':>12} {'Max margin':>12}")

    for name, price, q_lim, a_lim, fixed in tiers:
        # Typical usage = 60% of limits
        typ_cost = 0.6 * q_lim * s_med + 0.6 * a_lim * p_med + fixed
        # Max usage = 100% of limits (with p90 for analyses to be conservative)
        max_cost = q_lim * s_med + a_lim * p_p90 + fixed

        typ_margin = (price - typ_cost) / price * 100 if price > 0 else 0
        max_margin = (price - max_cost) / price * 100 if price > 0 else 0

        print(f"  {name:<18} {q_lim:>6} {a_lim:>6} ${fixed:>5} ${typ_cost:>7.2f} ${max_cost:>7.2f} {typ_margin:>10.0f}% {max_margin:>10.0f}%")


# ================================
# --> Analysis 7: Break-even & sensitivity
# ================================

def analyze_breakeven(traces: list[dict]) -> None:
    print("\n\n" + "=" * 75)
    print("  ANALYSIS 7: BREAK-EVEN AND FUTURE-PROOFING")
    print("=" * 75)

    planned_traces = [t for t in traces if classify_trace(t) == "planned" and t.get("total_cost", 0) > 0]

    if not planned_traces:
        return

    # How many deep analyses can you do per subscription tier before breaking even?
    # Using Sonnet+Haiku optimized config
    def opt_cost(t):
        worker_ids = get_worker_obs_ids(t["observations"])
        all_gen_ids = {o["id"] for o in t["observations"] if o.get("type") == "GENERATION"}
        orch = aggregate_tokens(t["observations"], all_gen_ids - worker_ids)
        work = aggregate_tokens(t["observations"], worker_ids)
        return cost_for_tokens(orch, "claude-sonnet-4-6") + cost_for_tokens(work, "claude-haiku-4-5")

    planned_costs = [opt_cost(t) for t in planned_traces if opt_cost(t) > 0]
    planned_med = median(planned_costs)

    print(f"\n  Median deep-analysis cost (optimized): ${planned_med:.3f}")
    print(f"\n  Break-even deep-analyses per subscription tier:")
    print(f"  {'Subscription':<15} {'Break-even # analyses':>22}")

    for price in [29, 49, 79, 129, 199, 299]:
        breakeven = price / planned_med
        print(f"  ${price}/mo{'':<8} {breakeven:>22.0f}")

    # Model price drop sensitivity
    print(f"\n  Sensitivity: what if LLM prices drop 50% in 12 months?")
    print(f"  (fixed subscription price, variable cost halves)")
    print(f"  {'Tier':<15} {'Today margin':>14} {'Future margin':>15}")

    for price in [29, 79, 129, 199]:
        # Estimate today vs future margin at "typical" usage (30 analyses on $79 plan scale)
        analyses = int(price / 4)  # rough: user does analyses worth 1/4 of price
        today_cost = analyses * planned_med + 4
        future_cost = analyses * planned_med * 0.5 + 4
        today_margin = (price - today_cost) / price * 100
        future_margin = (price - future_cost) / price * 100
        print(f"  ${price}/mo{'':<8} {today_margin:>13.0f}% {future_margin:>14.0f}%")


# ================================
# --> Main
# ================================

def main():
    traces = load_all_traces()

    print(f"Loaded {len(traces)} traces for analysis")

    analyze_cost_distribution(traces)
    analyze_cost_drivers(traces)
    analyze_usage_patterns(traces)
    analyze_concentration(traces)
    analyze_optimal_models(traces)
    analyze_pricing_scenarios(traces)
    analyze_breakeven(traces)


if __name__ == "__main__":
    main()
