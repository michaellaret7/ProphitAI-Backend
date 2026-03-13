"""
Prompt Caching Benchmark: Cached vs Uncached Latency
=====================================================
Demonstrates the speed difference when using Anthropic's prompt caching.

Usage:
    export ANTHROPIC_API_KEY=your_key_here
    pip install anthropic
    python prompt_cache_benchmark.py
"""

import anthropic
import time
import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-6"          # swap to any cache-supported model
MAX_TOKENS = 256
NUM_CACHED_RUNS = 5                  # how many follow-up calls to measure

# ---------------------------------------------------------------------------
# Build a long system prompt that exceeds the minimum cache threshold
# (2048 tokens for Sonnet 4.6). We pad it with detailed instructions
# so it comfortably clears the minimum.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are DeepAgent, an advanced AI-powered investment research assistant built 
for retail investors and registered investment advisors (RIAs). Your core 
capabilities include portfolio optimization, factor exposure analysis, 
multi-agent research workflows, and real-time market analysis.

INSTRUCTIONS:
1. Always ground your analysis in quantitative data when available.
2. Provide risk-adjusted return metrics (Sharpe, Sortino, max drawdown).
3. Consider macro factors: yield curve dynamics, credit spreads, volatility 
   regime, and cross-asset correlations.
4. When analyzing equities, evaluate both fundamental (earnings, FCF, margins) 
   and technical (momentum, mean-reversion, relative strength) signals.
5. For fixed income, consider duration, convexity, OAS, and roll-down return.
6. Always disclose limitations and uncertainty in your analysis.
7. Present multiple scenarios (bull, base, bear) with probability weights.
8. Use proper financial terminology but explain complex concepts clearly.
""" + "\n".join(
    [
        f"- Additional guideline #{i}: When analyzing sector {i}, consider the "
        f"specific regulatory environment, competitive dynamics, capital intensity, "
        f"and cyclical sensitivity that characterize this sector. Evaluate both "
        f"top-down macro drivers and bottom-up company-specific catalysts. Consider "
        f"the impact of technological disruption and ESG factors on long-term "
        f"valuations and sustainable growth rates for sector {i} companies."
        for i in range(1, 80)
    ]
)

USER_QUESTION = "Give me a brief overview of how to evaluate a tech stock."


def run_benchmark():
    client = anthropic.Anthropic()

    print("=" * 65)
    print("  PROMPT CACHING BENCHMARK")
    print("=" * 65)
    print(f"  Model         : {MODEL}")
    print(f"  System prompt : ~{len(SYSTEM_PROMPT.split())} words")
    print(f"  Cached runs   : {NUM_CACHED_RUNS}")
    print("=" * 65)

    # ------------------------------------------------------------------
    # 1) UNCACHED baseline — no cache_control at all
    # ------------------------------------------------------------------
    print("\n[1/3] Uncached baseline call (no prompt caching)...")
    t0 = time.perf_counter()
    uncached_resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_QUESTION}],
    )
    uncached_time = time.perf_counter() - t0

    print(f"      Time           : {uncached_time:.3f}s")
    print(f"      Input tokens   : {uncached_resp.usage.input_tokens}")
    print(f"      Output tokens  : {uncached_resp.usage.output_tokens}")
    cache_read = getattr(uncached_resp.usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(uncached_resp.usage, "cache_creation_input_tokens", 0) or 0
    print(f"      Cache read     : {cache_read}")
    print(f"      Cache write    : {cache_write}")

    # ------------------------------------------------------------------
    # 2) First CACHED call — this writes the cache (cold start)
    # ------------------------------------------------------------------
    print("\n[2/3] First cached call (cache WRITE — cold start)...")
    t0 = time.perf_counter()
    cache_write_resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        cache_control={"type": "ephemeral"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_QUESTION}],
    )
    cache_write_time = time.perf_counter() - t0

    cw_read = getattr(cache_write_resp.usage, "cache_read_input_tokens", 0) or 0
    cw_write = getattr(cache_write_resp.usage, "cache_creation_input_tokens", 0) or 0
    print(f"      Time           : {cache_write_time:.3f}s")
    print(f"      Input tokens   : {cache_write_resp.usage.input_tokens}")
    print(f"      Output tokens  : {cache_write_resp.usage.output_tokens}")
    print(f"      Cache read     : {cw_read}")
    print(f"      Cache write    : {cw_write}")

    # ------------------------------------------------------------------
    # 3) Subsequent CACHED calls — these should read from cache
    # ------------------------------------------------------------------
    print(f"\n[3/3] {NUM_CACHED_RUNS} cached calls (cache READ — warm)...")
    cached_times = []

    for i in range(NUM_CACHED_RUNS):
        t0 = time.perf_counter()
        cached_resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            cache_control={"type": "ephemeral"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_QUESTION}],
        )
        elapsed = time.perf_counter() - t0
        cached_times.append(elapsed)

        cr_read = getattr(cached_resp.usage, "cache_read_input_tokens", 0) or 0
        cr_write = getattr(cached_resp.usage, "cache_creation_input_tokens", 0) or 0
        print(f"      Run {i+1}: {elapsed:.3f}s  "
              f"(read={cr_read}, write={cr_write})")

    avg_cached = sum(cached_times) / len(cached_times)

    # ------------------------------------------------------------------
    # Results summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  RESULTS")
    print("=" * 65)
    print(f"  Uncached (no caching)     : {uncached_time:.3f}s")
    print(f"  Cache write (cold start)  : {cache_write_time:.3f}s")
    print(f"  Cache read avg ({NUM_CACHED_RUNS} runs)  : {avg_cached:.3f}s")

    if uncached_time > 0 and avg_cached > 0:
        speedup = uncached_time / avg_cached
        reduction = (1 - avg_cached / uncached_time) * 100
        print(f"\n  Speedup (cached vs uncached) : {speedup:.2f}x")
        print(f"  Latency reduction            : {reduction:.1f}%")
    print("=" * 65)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable first.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        exit(1)

    run_benchmark()