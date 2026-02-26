import time
from app.core.atlas.tools.ticker.utils import build_ticker_obj
from app.core.atlas.tools.portfolio.utils import build_portfolio_obj
from app.utils.cache.data_cache import get_cache
from app.redis.sync_client import sync_cache

SEP = "=" * 70


def snap() -> dict[str, int]:
    c = get_cache()
    return {
        "ohlcv": len(c.ohlcv), "fund": len(c.fundamentals),
        "class": len(c.classifications), "factors": len(c.ticker_factors),
    }


def redis_info() -> str:
    sync_cache._ensure_connected()
    if not sync_cache.client:
        return "Redis: off"
    from app.utils.time_utils import get_utc_date_str
    key = f"universe_factors:{get_utc_date_str()}"
    ttl = sync_cache.client.ttl(key)
    return f"Redis: universe={ttl > 0} ttl={ttl}s"


def run_ticker_research(tickers: list[str], fundamentals: bool = True) -> float:
    """Simulate agent calling ticker tools. Returns total time."""
    t0 = time.time()
    for tkr in tickers:
        t1 = time.time()
        obj = build_ticker_obj(tkr, years_back=5, fundamentals=fundamentals)
        elapsed = time.time() - t1
        tag = "CACHED" if elapsed < 0.5 else "NEW"
        has_val = obj.factors.value is not None
        print(f"    {tkr:<5} {elapsed:.2f}s [{tag}]  fundamentals={'yes' if has_val else 'no'}")
    return time.time() - t0


def run_portfolio(tickers: list[str], weights: list[float]) -> float:
    """Simulate agent building a portfolio. Returns total time."""
    t0 = time.time()
    p = build_portfolio_obj(tickers=tickers, weights=weights, years_back=5, with_factors=True)
    elapsed = time.time() - t0
    fe = p.factor_exposure
    print(f"    Build: {elapsed:.2f}s")
    print(f"    mom={fe.momentum:+.2f}  val={fe.value}  qual={fe.quality}")
    print(f"    grow={fe.growth}  vol={fe.volatility:+.2f}  size={fe.size}")
    return elapsed


print(SEP)
print("INITIAL STATE")
print(f"  cache: {snap()} | {redis_info()}")
print(SEP)

results: list[tuple[str, float]] = []

# ============================================================
# User A — Cold start, big tech research + portfolio
# ============================================================
print(f"\nUSER A (12:00pm) — Tech research + portfolio")
print("-" * 50)
tA = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
t0 = time.time()
print("  Ticker research:")
run_ticker_research(tA)
print("  Portfolio:")
run_portfolio(tA, [0.25, 0.25, 0.20, 0.15, 0.15])
total_a = time.time() - t0
results.append(("User A (cold tech)", total_a))
print(f"  TOTAL: {total_a:.2f}s | cache: {snap()}")

# ============================================================
# User B — Overlapping tickers, growth portfolio
# ============================================================
print(f"\nUSER B (12:07pm) — Growth portfolio (3/5 overlap with A)")
print("-" * 50)
tB = ["NVDA", "AAPL", "TSLA", "META", "MSFT"]
t0 = time.time()
print("  Ticker research:")
run_ticker_research(tB)
print("  Portfolio:")
run_portfolio(tB, [0.30, 0.20, 0.20, 0.15, 0.15])
total_b = time.time() - t0
results.append(("User B (3/5 cached)", total_b))
print(f"  TOTAL: {total_b:.2f}s | cache: {snap()}")

# ============================================================
# User C — Financials sector, no overlap
# ============================================================
print(f"\nUSER C (12:15pm) — Financials research (all new tickers)")
print("-" * 50)
tC = ["JPM", "GS", "MS", "BAC", "C"]
t0 = time.time()
print("  Ticker research:")
run_ticker_research(tC)
print("  Portfolio:")
run_portfolio(tC, [0.25, 0.20, 0.20, 0.20, 0.15])
total_c = time.time() - t0
results.append(("User C (all new)", total_c))
print(f"  TOTAL: {total_c:.2f}s | cache: {snap()}")

# ============================================================
# User D — Mixed portfolio, heavy overlap with A+B+C
# ============================================================
print(f"\nUSER D (12:22pm) — Mixed portfolio (all 8 tickers already cached)")
print("-" * 50)
tD = ["AAPL", "NVDA", "JPM", "TSLA", "GS", "MSFT", "META", "GOOGL"]
wD = [0.15, 0.15, 0.15, 0.10, 0.10, 0.15, 0.10, 0.10]
t0 = time.time()
print("  Ticker research:")
run_ticker_research(tD)
print("  Portfolio:")
run_portfolio(tD, wD)
total_d = time.time() - t0
results.append(("User D (8/8 cached)", total_d))
print(f"  TOTAL: {total_d:.2f}s | cache: {snap()}")

# ============================================================
# User E — Healthcare, all new, price-only first then fundamentals
# ============================================================
print(f"\nUSER E (12:30pm) — Healthcare (price-only scan, then deep dive)")
print("-" * 50)
tE = ["JNJ", "UNH", "PFE", "ABT", "TMO"]
t0 = time.time()
print("  Quick scan (no fundamentals):")
run_ticker_research(tE, fundamentals=False)
print(f"    cache mid-scan: {snap()}")
print("  Deep dive (with fundamentals — factors recomputed):")
run_ticker_research(tE, fundamentals=True)
print("  Portfolio:")
run_portfolio(tE, [0.25, 0.20, 0.20, 0.20, 0.15])
total_e = time.time() - t0
results.append(("User E (scan→deep)", total_e))
print(f"  TOTAL: {total_e:.2f}s | cache: {snap()}")

# ============================================================
# User F — Semiconductors, mostly overlap with A+B
# ============================================================
print(f"\nUSER F (12:38pm) — Semiconductors (3/5 cached from earlier)")
print("-" * 50)
tF = ["NVDA", "AMD", "AVGO", "QCOM", "AAPL"]
t0 = time.time()
print("  Ticker research:")
run_ticker_research(tF)
print("  Portfolio:")
run_portfolio(tF, [0.30, 0.20, 0.20, 0.15, 0.15])
total_f = time.time() - t0
results.append(("User F (3/5 cached)", total_f))
print(f"  TOTAL: {total_f:.2f}s | cache: {snap()}")

# ============================================================
# User G — Mega portfolio, ALL tickers from every prior user
# ============================================================
print(f"\nUSER G (12:45pm) — Mega portfolio (all prior tickers, fully cached)")
print("-" * 50)
all_seen = list(dict.fromkeys(tA + tB + tC + tD + tE + tF))  # dedupe, preserve order
wG = [1.0 / len(all_seen)] * len(all_seen)
t0 = time.time()
print(f"  Ticker research ({len(all_seen)} tickers):")
run_ticker_research(all_seen)
print("  Portfolio:")
run_portfolio(all_seen, wG)
total_g = time.time() - t0
results.append(("User G (all cached)", total_g))
print(f"  TOTAL: {total_g:.2f}s | cache: {snap()}")

# ============================================================
# Final Summary
# ============================================================
print(f"\n{SEP}")
print("FINAL SUMMARY")
print(SEP)
print(f"  {'User':<22} {'Total':>7}  {'Bar'}")
print(f"  {'-'*22} {'-'*7}  {'-'*30}")
for label, t in results:
    bar = "#" * int(t * 5)
    print(f"  {label:<22} {t:>5.2f}s  {bar}")
print(f"\n  Final cache: {snap()}")
print(f"  {redis_info()}")
