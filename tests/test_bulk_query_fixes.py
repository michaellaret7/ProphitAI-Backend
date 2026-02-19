"""Verify the three critical database query fixes.

1. Column name mismatches — diluted_eps, capital_expenditures, change_in_cash no longer None
2. Bulk fundamentals — single-session IN-clause vs old N-threaded approach
3. Bulk price data — single query vs old N-threaded approach
"""

import time

import pandas as pd

from app.repositories.fundamentals import get_fundamental_data, get_bulk_fundamentals
from app.repositories.price_data import (
    fetch_bulk_ohlcv_data_for_tickers,
    fetch_bulk_price_data_for_tickers,
)


# ================================
# --> Helper funcs
# ================================

def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def _timed(label: str, func, *args, **kwargs):
    """Run func, print elapsed time, return result."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    print(f"  {label}: {elapsed:.3f}s")
    return result, elapsed


# ================================
# --> Fix 1: Column name mismatches
# ================================

def test_column_name_fixes():
    """Verify diluted_eps, capital_expenditures, and change_in_cash return real data."""
    _section("Fix 1: Column Name Mismatches")

    # Income statement — diluted_eps
    income = get_fundamental_data("AAPL", "income_statement", quarters_back=1)
    if income and income.get("data"):
        diluted_eps = income["data"][0].get("diluted_eps")
        print(f"  AAPL diluted_eps:        {diluted_eps}")
        assert diluted_eps is not None, "diluted_eps is still None — fix not applied"
        print("  PASS diluted_eps returning data")
    else:
        print("  WARN No income statement data for AAPL")

    # Cash flow — capital_expenditures and change_in_cash
    cashflow = get_fundamental_data("AAPL", "cash_flow", quarters_back=1)
    if cashflow and cashflow.get("data"):
        capex = cashflow["data"][0].get("capital_expenditures")
        change_cash = cashflow["data"][0].get("change_in_cash")
        print(f"  AAPL capital_expenditures: {capex}")
        print(f"  AAPL change_in_cash:       {change_cash}")
        assert capex is not None, "capital_expenditures is still None — fix not applied"
        assert change_cash is not None, "change_in_cash is still None — fix not applied"
        print("  PASS capital_expenditures returning data")
        print("  PASS change_in_cash returning data")
    else:
        print("  WARN No cash flow data for AAPL")


# ================================
# --> Fix 2: Bulk fundamentals
# ================================

def test_bulk_fundamentals_performance():
    """Time bulk fundamentals fetch and verify correctness."""
    _section("Fix 2: Bulk Fundamentals (single session, 6 queries)")

    tickers = [
        "AAPL", "MSFT", "GOOG", "AMZN", "META",
        "NVDA", "TSLA", "JPM", "V", "JNJ",
        "WMT", "PG", "UNH", "HD", "MA",
    ]

    result, elapsed = _timed(f"get_bulk_fundamentals({len(tickers)} tickers)", get_bulk_fundamentals, tickers)

    print(f"\n  Tickers returned: {len(result)}/{len(tickers)}")
    print(f"  Tickers: {sorted(result.keys())}")

    # Spot-check structure
    if "AAPL" in result:
        aapl = result["AAPL"]
        print(f"\n  AAPL income_statements:    {len(aapl.income_statements)} rows")
        print(f"  AAPL balance_sheets:       {len(aapl.balance_sheets)} rows")
        print(f"  AAPL cash_flow_statements: {len(aapl.cash_flow_statements)} rows")
        print(f"  AAPL financial_ratios:     {len(aapl.financial_ratios)} rows")
        print(f"  AAPL analyst_estimates:    {len(aapl.analyst_estimates)} rows")

    assert len(result) > 0, "No fundamentals returned"
    print(f"\n  PASS Bulk fundamentals returned {len(result)} tickers in {elapsed:.3f}s")


# ================================
# --> Fix 3: Bulk price data
# ================================

def test_bulk_price_data_performance():
    """Time bulk price data fetch and verify correctness."""
    _section("Fix 3: Bulk Price Data (single query)")

    tickers = [
        "AAPL", "MSFT", "GOOG", "AMZN", "META",
        "NVDA", "TSLA", "JPM", "V", "JNJ",
        "WMT", "PG", "UNH", "HD", "MA",
        "BAC", "KO", "PEP", "DIS", "NFLX",
    ]
    start = "2024-01-01"
    end = "2025-12-31"

    # Test OHLCV fetch
    ohlcv_result, ohlcv_time = _timed(
        f"fetch_bulk_ohlcv_data_for_tickers({len(tickers)} tickers)",
        fetch_bulk_ohlcv_data_for_tickers,
        tickers, start, end,
    )

    print(f"\n  Tickers returned: {len(ohlcv_result)}/{len(tickers)}")

    # Verify DataFrame structure
    if "AAPL" in ohlcv_result:
        df = ohlcv_result["AAPL"]
        print(f"  AAPL shape: {df.shape}")
        print(f"  AAPL columns: {df.columns.tolist()}")
        print(f"  AAPL index type: {type(df.index).__name__}")
        expected_cols = {"open", "high", "low", "close", "adj_close", "volume"}
        assert expected_cols.issubset(set(df.columns)), f"Missing columns: {expected_cols - set(df.columns)}"
        assert isinstance(df.index, pd.DatetimeIndex), "Index is not DatetimeIndex"

    assert len(ohlcv_result) > 0, "No OHLCV data returned"
    print(f"\n  PASS OHLCV fetch returned {len(ohlcv_result)} tickers in {ohlcv_time:.3f}s")

    # Test price-only fetch
    price_result, price_time = _timed(
        f"fetch_bulk_price_data_for_tickers({len(tickers)} tickers)",
        fetch_bulk_price_data_for_tickers,
        tickers, start, end,
    )

    print(f"\n  Price DataFrame shape: {price_result.shape}")
    print(f"  Columns: {price_result.columns.tolist()[:5]}...")
    assert not price_result.empty, "Price DataFrame is empty"
    print(f"\n  PASS Price fetch returned {price_result.shape[1]} tickers in {price_time:.3f}s")


# ================================
# --> Main
# ================================

if __name__ == "__main__":
    test_column_name_fixes()
    test_bulk_fundamentals_performance()
    test_bulk_price_data_performance()

    _section("ALL TESTS PASSED")
