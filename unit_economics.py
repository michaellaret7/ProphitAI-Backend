"""
Unit Economics Calculator for ProphitAI Agent Runs.

Pulls real usage data from Langfuse, computes average token consumption
per agent type, and estimates costs under pluggable model pricing.

Usage:
    python unit_economics.py
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.api.core.request_options import RequestOptions

load_dotenv()

REQUEST_OPTS = RequestOptions(timeout_in_seconds=120)


# ================================
# --> Pricing config
# ================================

# All prices are per 1M tokens
PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cache_create": 3.75,
        "cache_read": 0.30,
    },
    "claude-opus-4-6": {
        "input": 15.00,
        "output": 75.00,
        "cache_create": 18.75,
        "cache_read": 1.50,
    },
    "claude-haiku-4-5": {
        "input": 0.80,
        "output": 4.00,
        "cache_create": 1.00,
        "cache_read": 0.08,
    },
    # OpenAI
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
        "cache_create": 0.0,
        "cache_read": 1.25,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
        "cache_create": 0.0,
        "cache_read": 0.075,
    },
    "gpt-4.1": {
        "input": 2.00,
        "output": 8.00,
        "cache_create": 0.0,
        "cache_read": 0.50,
    },
    "gpt-4.1-mini": {
        "input": 0.40,
        "output": 1.60,
        "cache_create": 0.0,
        "cache_read": 0.10,
    },
    "gpt-4.1-nano": {
        "input": 0.10,
        "output": 0.40,
        "cache_create": 0.0,
        "cache_read": 0.025,
    },
    # Google
    "gemini-2.5-pro": {
        "input": 1.25,
        "output": 10.00,
        "cache_create": 0.0,
        "cache_read": 0.315,
    },
    "gemini-2.5-flash": {
        "input": 0.15,
        "output": 0.60,
        "cache_create": 0.0,
        "cache_read": 0.0375,
    },
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
        "cache_create": 0.0,
        "cache_read": 0.025,
    },
    # xAI
    "grok-3": {
        "input": 3.00,
        "output": 15.00,
        "cache_create": 0.0,
        "cache_read": 0.0,
    },
    "grok-3-mini": {
        "input": 0.30,
        "output": 0.50,
        "cache_create": 0.0,
        "cache_read": 0.0,
    },
}

# Perplexity cost per web search call (sonar pro)
PERPLEXITY_COST_PER_CALL = 0.005


# ================================
# --> Data models
# ================================

@dataclass
class GenerationStats:
    """Token usage for a single LLM generation."""

    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_create_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0
    actual_cost: float = 0.0


@dataclass
class TraceStats:
    """Aggregated stats for a single agent trace."""

    trace_id: str = ""
    trace_name: str = ""
    tags: list[str] = field(default_factory=list)
    latency: float = 0.0
    actual_cost: float = 0.0
    generation_count: int = 0
    tool_call_count: int = 0
    iteration_count: int = 0
    web_search_count: int = 0

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_create_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_tokens: int = 0

    models_used: set[str] = field(default_factory=set)
    generations: list[GenerationStats] = field(default_factory=list)


@dataclass
class UsageProfile:
    """Average usage profile for a category of agent runs."""

    category: str = ""
    sample_size: int = 0

    avg_generations: float = 0.0
    avg_iterations: float = 0.0
    avg_tool_calls: float = 0.0
    avg_web_searches: float = 0.0
    avg_latency_seconds: float = 0.0

    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    avg_cache_create_tokens: float = 0.0
    avg_cache_read_tokens: float = 0.0
    avg_total_tokens: float = 0.0

    avg_actual_cost: float = 0.0
    min_actual_cost: float = 0.0
    max_actual_cost: float = 0.0
    median_actual_cost: float = 0.0


# ================================
# --> Helper funcs
# ================================

def _extract_generation_stats(obs) -> Optional[GenerationStats]:
    """Extract generation stats from a Langfuse ObservationsView object.

    Uses usage_details (dict) for token counts including cache breakdown,
    and cost_details (dict) for actual dollar costs.
    """

    # Reason: usage_details is a dict with cache token fields,
    # usage is a Pydantic Usage model without them
    usage = getattr(obs, "usage_details", None) or {}
    cost_details = getattr(obs, "cost_details", None) or {}
    model = getattr(obs, "model", None) or "unknown"

    if not usage:
        return None

    return GenerationStats(
        model=model,
        input_tokens=int(usage.get("input", 0) or 0),
        output_tokens=int(usage.get("output", 0) or 0),
        cache_create_tokens=int(usage.get("input_cache_creation", 0) or 0),
        cache_read_tokens=int(usage.get("input_cached_tokens", 0) or 0),
        total_tokens=int(usage.get("total", 0) or 0),
        actual_cost=float(cost_details.get("total", 0) or 0),
    )


def _build_trace_stats(trace, observations: list) -> TraceStats:
    """Build aggregated stats for a single trace from its ObservationsView list."""

    stats = TraceStats(
        trace_id=trace.id,
        trace_name=trace.name or "unknown",
        tags=trace.tags or [],
        latency=trace.latency or 0.0,
        actual_cost=trace.total_cost or 0.0,
    )

    for obs in observations:
        obs_type = getattr(obs, "type", "") or ""
        obs_name = getattr(obs, "name", "") or ""

        if obs_type == "GENERATION":
            stats.generation_count += 1

            gen = _extract_generation_stats(obs)

            if gen:
                stats.generations.append(gen)
                stats.total_input_tokens += gen.input_tokens
                stats.total_output_tokens += gen.output_tokens
                stats.total_cache_create_tokens += gen.cache_create_tokens
                stats.total_cache_read_tokens += gen.cache_read_tokens
                stats.total_tokens += gen.total_tokens
                stats.models_used.add(gen.model)

        elif obs_type == "TOOL":
            stats.tool_call_count += 1

            if "web_search" in obs_name.lower():
                stats.web_search_count += 1

        elif obs_type == "SPAN" and "iteration" in obs_name.lower():
            stats.iteration_count += 1

    return stats


def _compute_profile(category: str, traces: list[TraceStats]) -> UsageProfile:
    """Compute average usage profile from a list of trace stats."""

    n = len(traces)

    if n == 0:
        return UsageProfile(category=category, sample_size=0)

    costs = sorted(t.actual_cost for t in traces)

    return UsageProfile(
        category=category,
        sample_size=n,
        avg_generations=sum(t.generation_count for t in traces) / n,
        avg_iterations=sum(t.iteration_count for t in traces) / n,
        avg_tool_calls=sum(t.tool_call_count for t in traces) / n,
        avg_web_searches=sum(t.web_search_count for t in traces) / n,
        avg_latency_seconds=sum(t.latency for t in traces) / n,
        avg_input_tokens=sum(t.total_input_tokens for t in traces) / n,
        avg_output_tokens=sum(t.total_output_tokens for t in traces) / n,
        avg_cache_create_tokens=sum(t.total_cache_create_tokens for t in traces) / n,
        avg_cache_read_tokens=sum(t.total_cache_read_tokens for t in traces) / n,
        avg_total_tokens=sum(t.total_tokens for t in traces) / n,
        avg_actual_cost=sum(costs) / n,
        min_actual_cost=costs[0],
        max_actual_cost=costs[-1],
        median_actual_cost=costs[n // 2],
    )


def _estimate_cost(profile: UsageProfile, model_key: str) -> dict[str, float]:
    """Estimate cost for a usage profile under a different model's pricing."""

    pricing = PRICING.get(model_key)

    if not pricing:
        return {"error": -1}

    input_cost = (profile.avg_input_tokens / 1_000_000) * pricing["input"]
    output_cost = (profile.avg_output_tokens / 1_000_000) * pricing["output"]
    cache_create_cost = (profile.avg_cache_create_tokens / 1_000_000) * pricing["cache_create"]
    cache_read_cost = (profile.avg_cache_read_tokens / 1_000_000) * pricing["cache_read"]
    search_cost = profile.avg_web_searches * PERPLEXITY_COST_PER_CALL

    total = input_cost + output_cost + cache_create_cost + cache_read_cost + search_cost

    return {
        "model": model_key,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_create_cost": cache_create_cost,
        "cache_read_cost": cache_read_cost,
        "search_cost": search_cost,
        "total_llm_cost": total - search_cost,
        "total_with_search": total,
    }


# ================================
# --> Data fetching
# ================================

def fetch_trace_data(lookback_days: int = 7) -> list[TraceStats]:
    """Fetch all traces and their observations from Langfuse.

    Uses trace.get() per trace to get full ObservationsView objects
    with model, usage, and cost data populated.
    """

    client = Langfuse()
    all_trace_stats: list[TraceStats] = []
    page = 1

    from_ts = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    print(f"Fetching traces from last {lookback_days} days...")

    while True:
        traces_response = client.api.trace.list(
            limit=50,
            page=page,
            from_timestamp=from_ts,
            request_options=REQUEST_OPTS,
        )

        traces = traces_response.data

        if not traces:
            break

        for trace in traces:
            # Reason: trace.get() returns full detail with ObservationsView objects
            # that include model, usage, and cost_details — list() doesn't
            detail = client.api.trace.get(trace.id, request_options=REQUEST_OPTS)
            observations = detail.observations or []
            stats = _build_trace_stats(trace, observations)
            all_trace_stats.append(stats)

        print(f"  Page {page}: {len(traces)} traces fetched ({len(all_trace_stats)} total)")

        if len(traces) < 50:
            break

        page += 1

    print(f"Total traces: {len(all_trace_stats)}")

    return all_trace_stats


# ================================
# --> Report generation
# ================================

def print_profile(profile: UsageProfile) -> None:
    """Print a single usage profile."""

    print(f"\n{'=' * 60}")
    print(f"  {profile.category} (n={profile.sample_size})")
    print(f"{'=' * 60}")
    print(f"  Avg LLM calls/run:    {profile.avg_generations:.1f}")
    print(f"  Avg iterations/run:   {profile.avg_iterations:.1f}")
    print(f"  Avg tool calls/run:   {profile.avg_tool_calls:.1f}")
    print(f"  Avg web searches/run: {profile.avg_web_searches:.1f}")
    print(f"  Avg latency:          {profile.avg_latency_seconds:.1f}s")
    print()
    print(f"  Token Usage (avg per run):")
    print(f"    Input tokens:         {profile.avg_input_tokens:>10,.0f}")
    print(f"    Output tokens:        {profile.avg_output_tokens:>10,.0f}")
    print(f"    Cache create tokens:  {profile.avg_cache_create_tokens:>10,.0f}")
    print(f"    Cache read tokens:    {profile.avg_cache_read_tokens:>10,.0f}")
    print(f"    Total tokens:         {profile.avg_total_tokens:>10,.0f}")
    print()
    print(f"  Actual Cost (from Langfuse):")
    print(f"    Average:  ${profile.avg_actual_cost:.4f}")
    print(f"    Median:   ${profile.median_actual_cost:.4f}")
    print(f"    Min:      ${profile.min_actual_cost:.4f}")
    print(f"    Max:      ${profile.max_actual_cost:.4f}")


def print_model_comparison(profile: UsageProfile) -> None:
    """Print cost estimates across all configured models."""

    print(f"\n  {'Model':<25} {'Input':>8} {'Output':>8} {'Cache$':>8} {'Search':>8} {'TOTAL':>10}")
    print(f"  {'-' * 67}")

    estimates = []

    for model_key in PRICING:
        est = _estimate_cost(profile, model_key)

        if "error" in est:
            continue

        estimates.append(est)

    estimates.sort(key=lambda e: e["total_with_search"])

    for est in estimates:
        cache_cost = est["cache_create_cost"] + est["cache_read_cost"]

        print(
            f"  {est['model']:<25} "
            f"${est['input_cost']:>7.4f} "
            f"${est['output_cost']:>7.4f} "
            f"${cache_cost:>7.4f} "
            f"${est['search_cost']:>7.4f} "
            f"${est['total_with_search']:>9.4f}"
        )


def print_monthly_projection(profiles: list[UsageProfile]) -> None:
    """Project monthly costs for different user activity levels."""

    print(f"\n{'=' * 70}")
    print(f"  MONTHLY COST PROJECTION")
    print(f"{'=' * 70}")

    # Reason: model the mix of simple vs planned runs per user
    usage_tiers = {
        "Light (20 calls/mo)": {"simple": 15, "planned": 5},
        "Medium (50 calls/mo)": {"simple": 30, "planned": 20},
        "Heavy (100 calls/mo)": {"simple": 50, "planned": 50},
        "Power (200 calls/mo)": {"simple": 80, "planned": 120},
    }

    simple_profile = next((p for p in profiles if "Simple" in p.category), None)
    planned_profile = next((p for p in profiles if "Planned" in p.category), None)

    if not simple_profile or not planned_profile:
        print("  Insufficient data for projection (need both simple and planned traces)")
        return

    print(f"\n  Using actual avg costs: Simple=${simple_profile.avg_actual_cost:.4f}, Planned=${planned_profile.avg_actual_cost:.4f}")
    print()

    header = f"  {'Tier':<25}"

    for model_key in ["claude-sonnet-4-6", "claude-haiku-4-5", "gpt-4.1-mini", "gemini-2.5-flash"]:
        header += f" {model_key:>20}"

    print(header)
    print(f"  {'-' * (25 + 4 * 21)}")

    for tier_name, counts in usage_tiers.items():
        row = f"  {tier_name:<25}"

        for model_key in ["claude-sonnet-4-6", "claude-haiku-4-5", "gpt-4.1-mini", "gemini-2.5-flash"]:
            simple_est = _estimate_cost(simple_profile, model_key)
            planned_est = _estimate_cost(planned_profile, model_key)

            monthly = (
                counts["simple"] * simple_est["total_with_search"]
                + counts["planned"] * planned_est["total_with_search"]
            )

            row += f" ${monthly:>18.2f}"

        print(row)


def generate_report(all_traces: list[TraceStats]) -> None:
    """Generate the full unit economics report."""

    # Reason: separate simple agent runs from planned runs with workers
    simple_traces = [t for t in all_traces if "Planner" not in t.trace_name and "planned" not in t.trace_name.lower()]
    planned_traces = [t for t in all_traces if "Planner" in t.trace_name or "planned" in t.trace_name.lower()]

    # Reason: filter out traces with zero cost (incomplete/errored runs)
    simple_with_cost = [t for t in simple_traces if t.actual_cost > 0]
    planned_with_cost = [t for t in planned_traces if t.actual_cost > 0]

    simple_profile = _compute_profile("Simple Agent (no workers)", simple_with_cost)
    planned_profile = _compute_profile("Planned Agent (with workers)", planned_with_cost)
    all_profile = _compute_profile("All Agent Runs", simple_with_cost + planned_with_cost)

    print("\n" + "=" * 70)
    print("  PROPHITAI UNIT ECONOMICS REPORT")
    print("=" * 70)
    print(f"  Data source: Langfuse")
    print(f"  Total traces analyzed: {len(all_traces)}")
    print(f"    Simple agent runs:  {len(simple_traces)} ({len(simple_with_cost)} with cost data)")
    print(f"    Planned agent runs: {len(planned_traces)} ({len(planned_with_cost)} with cost data)")

    # Print profiles
    for profile in [simple_profile, planned_profile, all_profile]:
        if profile.sample_size > 0:
            print_profile(profile)

    # Model comparison
    print(f"\n\n{'=' * 70}")
    print(f"  MODEL COST COMPARISON (estimated from avg token usage)")
    print(f"{'=' * 70}")

    for profile in [simple_profile, planned_profile]:
        if profile.sample_size > 0:
            print(f"\n  --- {profile.category} ---")
            print_model_comparison(profile)

    # Monthly projections
    print_monthly_projection([simple_profile, planned_profile])

    # Per-trace detail table
    print(f"\n\n{'=' * 70}")
    print(f"  INDIVIDUAL TRACE DETAIL")
    print(f"{'=' * 70}")
    print(f"  {'Type':<20} {'Gens':>5} {'Iters':>5} {'Tools':>6} {'Searches':>8} {'Tokens':>10} {'Cost':>10} {'Latency':>8}")
    print(f"  {'-' * 73}")

    for t in sorted(all_traces, key=lambda x: x.actual_cost, reverse=True):
        if t.actual_cost <= 0 and t.generation_count == 0:
            continue

        print(
            f"  {t.trace_name:<20} "
            f"{t.generation_count:>5} "
            f"{t.iteration_count:>5} "
            f"{t.tool_call_count:>6} "
            f"{t.web_search_count:>8} "
            f"{t.total_tokens:>10,} "
            f"${t.actual_cost:>9.4f} "
            f"{t.latency:>7.0f}s"
        )


# ================================
# --> Main
# ================================

if __name__ == "__main__":
    traces = fetch_trace_data(lookback_days=7)
    generate_report(traces)
