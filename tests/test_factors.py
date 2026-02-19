"""End-to-end test for calc_v2 factor module.

Tests:
1. Ticker with fundamentals → all 6 factor categories populated
2. Ticker without fundamentals → momentum + volatility only, rest None
3. Portfolio factor exposure from multiple tickers
4. Universe-relative z-scoring vs. intra-portfolio z-scoring
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import pandas as pd

from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.repositories.fundamentals.fetchers import get_bulk_fundamentals
from app.core.calc_v2.ticker import Ticker
from app.core.calc_v2.portfolio import Portfolio
from app.core.calc_v2.factors.universe import build_universe_factors


def main() -> None:
    tickers = ['AAPL', 'MSFT', 'TSLA', 'GOOG', 'NVDA']
    weights = [0.20, 0.35, 0.25, 0.10, 0.10]

    # Reason: broader universe to test z-scoring against market
    universe_tickers = [
        'JNJ', 'PG', 'KO', 'PEP', 'MRK', 'ABT', 'WMT', 'COST',
        'CVX', 'XOM', 'JPM', 'BAC', 'GS', 'HD', 'LOW',
        'UNH', 'LLY', 'ABBV', 'CRM', 'ADBE', 'AMD', 'INTC',
    ]
    all_tickers = list(set(tickers + universe_tickers + ['SPY']))

    # ---- Fetch data ----
    print("Fetching OHLCV data...")
    t0 = time.time()
    ohlcv = fetch_bulk_ohlcv_data_for_tickers(all_tickers, '2024-01-01', '2026-01-31')
    print(f"  OHLCV fetched in {time.time() - t0:.1f}s")

    print("Fetching fundamentals...")
    t0 = time.time()
    fundamentals = get_bulk_fundamentals(all_tickers)
    print(f"  Fundamentals fetched in {time.time() - t0:.1f}s")
    print(f"  Got fundamentals for: {list(fundamentals.keys())}")

    benchmark = ohlcv['SPY']['adj_close']

    # ---- Test 1: Ticker WITH fundamentals ----
    print("\n" + "=" * 60)
    print("TEST 1: Ticker with fundamentals")
    print("=" * 60)

    ticker_objs: dict[str, Ticker] = {}
    for t in tickers:
        t0 = time.time()
        ticker_objs[t] = Ticker(t, ohlcv[t], benchmark, fundamentals.get(t))
        elapsed = time.time() - t0
        f = ticker_objs[t].factors
        print(f"\n--- {t} (built in {elapsed:.2f}s) ---")
        print(f"  Momentum:   r12_1={f.momentum.r12_1}, r6_1={f.momentum.r6_1}, "
              f"r3_1={f.momentum.r3_1}, risk_adj={f.momentum.risk_adj_momentum}, "
              f"pct_52w={f.momentum.pct_from_52w_high}")
        print(f"  Volatility: vol_1y={f.volatility.realized_vol_1y}, vol_3m={f.volatility.realized_vol_3m}, "
              f"beta={f.volatility.beta}, ivol={f.volatility.idiosyncratic_vol}, "
              f"mdd_1y={f.volatility.max_drawdown_1y}")
        if f.value:
            print(f"  Value:      ey={f.value.earnings_yield}, b/p={f.value.book_to_price}, "
                  f"fcf_y={f.value.fcf_yield}, ebitda/ev={f.value.ebitda_to_ev}, "
                  f"div_y={f.value.dividend_yield}")
        else:
            print("  Value:      None (no fundamentals)")
        if f.quality:
            print(f"  Quality:    gp={f.quality.gross_profitability}, roe={f.quality.roe}, "
                  f"roa={f.quality.roa}, accrual={f.quality.accrual_ratio}, "
                  f"d/e={f.quality.debt_to_equity}, ic={f.quality.interest_coverage}, "
                  f"z={f.quality.altman_z_score}")
        else:
            print("  Quality:    None (no fundamentals)")
        if f.growth:
            print(f"  Growth:     rev_g={f.growth.revenue_growth_yoy}, eps_g={f.growth.earnings_growth_yoy}, "
                  f"fcf_g={f.growth.fcf_growth_yoy}, fwd_eps={f.growth.forward_eps_growth}, "
                  f"sgr={f.growth.sustainable_growth_rate}")
        else:
            print("  Growth:     None (no fundamentals)")
        if f.size:
            print(f"  Size:       mcap={f.size.market_cap}, log_mcap={f.size.log_market_cap}")
        else:
            print("  Size:       None (no fundamentals)")

    # ---- Test 2: Ticker WITHOUT fundamentals ----
    print("\n" + "=" * 60)
    print("TEST 2: Ticker without fundamentals (momentum + vol only)")
    print("=" * 60)

    no_fund = Ticker('AAPL', ohlcv['AAPL'], benchmark)
    f = no_fund.factors
    print(f"  Momentum present:   {f.momentum is not None}")
    print(f"  Volatility present: {f.volatility is not None}")
    print(f"  Value is None:      {f.value is None}")
    print(f"  Quality is None:    {f.quality is None}")
    print(f"  Growth is None:     {f.growth is None}")
    print(f"  Size is None:       {f.size is None}")
    assert f.momentum is not None
    assert f.volatility is not None
    assert f.value is None
    assert f.quality is None
    assert f.growth is None
    assert f.size is None
    print("  PASSED")

    # ---- Test 3: Portfolio factor exposure ----
    print("\n" + "=" * 60)
    print("TEST 3: Portfolio factor exposure")
    print("=" * 60)

    price_df = pd.DataFrame({t: ohlcv[t]['adj_close'] for t in tickers})
    tf = {t: ticker_objs[t].factors for t in tickers}

    portfolio = Portfolio(
        name="Test Portfolio",
        tickers=tickers,
        weights=weights,
        price_df=price_df,
        benchmark_prices=benchmark,
        ticker_factors=tf,
    )

    fe = portfolio.factor_exposure
    assert fe is not None, "factor_exposure should not be None"
    print(f"  Momentum composite:   {fe.momentum}")
    print(f"  Value composite:      {fe.value}")
    print(f"  Quality composite:    {fe.quality}")
    print(f"  Growth composite:     {fe.growth}")
    print(f"  Volatility composite: {fe.volatility}")
    print(f"  Size composite:       {fe.size}")
    print(f"\n  Detail:")
    print(f"    r12_1:              {fe.detail.r12_1}")
    print(f"    earnings_yield:     {fe.detail.earnings_yield}")
    print(f"    gross_profitability:{fe.detail.gross_profitability}")
    print(f"    revenue_growth_yoy: {fe.detail.revenue_growth_yoy}")
    print(f"    realized_vol_1y:    {fe.detail.realized_vol_1y}")
    print(f"    log_market_cap:     {fe.detail.log_market_cap}")
    print("  PASSED")

    # ---- Test 4: Universe-relative z-scoring ----
    print("\n" + "=" * 60)
    print("TEST 4: Universe-relative z-scoring")
    print("=" * 60)

    print("  Building universe factors...")
    t0 = time.time()
    univ_factors = build_universe_factors(
        tickers=universe_tickers,
        ohlcv_data=ohlcv,
        benchmark_prices=benchmark,
        fundamentals=fundamentals,
    )
    print(f"  Universe factors built in {time.time() - t0:.1f}s "
          f"({len(univ_factors)} tickers)")

    portfolio_univ = Portfolio(
        name="Test Portfolio (universe z-scored)",
        tickers=tickers,
        weights=weights,
        price_df=price_df,
        benchmark_prices=benchmark,
        ticker_factors=tf,
        universe_factors=univ_factors,
    )

    fe_univ = portfolio_univ.factor_exposure
    assert fe_univ is not None, "universe factor_exposure should not be None"

    # Reason: print side-by-side comparison so we can visually validate the shift
    print(f"\n  {'Composite':<22} {'Intra-portfolio':>16} {'vs. Universe':>16}")
    print(f"  {'-' * 54}")
    for name in ['momentum', 'value', 'quality', 'growth', 'volatility', 'size']:
        intra = getattr(fe, name)
        univ = getattr(fe_univ, name)
        intra_str = f"{intra:.4f}" if intra is not None else "None"
        univ_str = f"{univ:.4f}" if univ is not None else "None"
        print(f"  {name:<22} {intra_str:>16} {univ_str:>16}")

    print(f"\n  {'Detail Metric':<22} {'Intra-portfolio':>16} {'vs. Universe':>16}")
    print(f"  {'-' * 54}")
    detail_fields = [
        'r12_1', 'r6_1', 'risk_adj_momentum',
        'earnings_yield', 'book_to_price', 'fcf_yield', 'ebitda_to_ev',
        'gross_profitability', 'roe', 'accrual_ratio', 'altman_z_score',
        'revenue_growth_yoy', 'forward_eps_growth',
        'realized_vol_1y', 'beta', 'log_market_cap',
    ]
    for field in detail_fields:
        intra = getattr(fe.detail, field)
        univ = getattr(fe_univ.detail, field)
        intra_str = f"{intra:.4f}" if intra is not None else "None"
        univ_str = f"{univ:.4f}" if univ is not None else "None"
        print(f"  {field:<22} {intra_str:>16} {univ_str:>16}")

    print("  PASSED")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
