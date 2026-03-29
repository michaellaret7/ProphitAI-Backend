"""Real integration tests for equity and ETF screeners after refactor to data layer."""

from prophitai_data.repositories.screener import (
    screen_equities,
    screen_etfs,
    EquityScreenerResult,
    ETFScreenerResult,
)


def test_equity_screener_basic():
    """Screen for large-cap tech stocks with low P/E."""
    print("\n=== Test: Equity Screener — large-cap tech, low P/E ===")
    results, error = screen_equities(
        sectors=["equity_sector_information_technology"],
        market_cap=(50_000_000_000, None),
        pe_ratio_ttm=(None, 30),
    )

    if error:
        print(f"ERROR: {error}")
        return

    print(f"Found {len(results)} stocks")
    for r in results[:5]:
        assert isinstance(r, EquityScreenerResult), f"Expected EquityScreenerResult, got {type(r)}"
        print(f"  {r.ticker} | sector={r.sector} | price={r.price} | mkt_cap={r.market_cap:,.0f}")

    assert len(results) > 0, "Should find at least one large-cap tech stock with P/E < 30"
    print("PASSED")


def test_equity_screener_multi_industry():
    """Screen across multiple industries with OR logic."""
    print("\n=== Test: Equity Screener — software OR biotech ===")
    results, error = screen_equities(
        industries=["software", "biotechnology"],
        market_cap=(1_000_000_000, None),
    )

    if error:
        print(f"ERROR: {error}")
        return

    print(f"Found {len(results)} stocks")
    industries_found = {r.industry for r in results}
    print(f"Industries in results: {industries_found}")

    assert len(results) > 0, "Should find software or biotech stocks"
    assert industries_found.issubset({"software", "biotechnology"}), f"Unexpected industries: {industries_found}"
    print("PASSED")


def test_equity_screener_invalid_sector():
    """Verify fuzzy matching error for invalid sector."""
    print("\n=== Test: Equity Screener — invalid sector fuzzy match ===")
    results, error = screen_equities(
        sectors=["financialz"],
    )

    assert results is None, "Should return None for invalid sector"
    assert error is not None, "Should return error message"
    assert "Invalid" in error or "Did you mean" in error, f"Expected fuzzy match error, got: {error}"
    print(f"Got expected error: {error[:100]}...")
    print("PASSED")


def test_etf_screener_basic():
    """Screen for low-cost equity ETFs."""
    print("\n=== Test: ETF Screener — low-cost equity ETFs ===")
    results, error = screen_etfs(
        industries=["equity_etfs"],
        expense_ratio=(None, 0.50),
    )

    if error:
        print(f"ERROR: {error}")
        return

    print(f"Found {len(results)} ETFs")
    for r in results[:5]:
        assert isinstance(r, ETFScreenerResult), f"Expected ETFScreenerResult, got {type(r)}"
        print(f"  {r.ticker} | industry={r.industry} | expense_ratio={r.expense_ratio}")

    assert len(results) > 0, "Should find low-cost equity ETFs"
    print("PASSED")


def test_etf_screener_high_dividend():
    """Screen for high dividend yield ETFs."""
    print("\n=== Test: ETF Screener — high dividend yield ===")
    results, error = screen_etfs(
        dividend_yield_ttm=(0.03, None),
    )

    if error:
        print(f"ERROR: {error}")
        return

    print(f"Found {len(results)} ETFs with dividend yield >= 3%")
    for r in results[:5]:
        print(f"  {r.ticker} | div_yield={r.dividend_yield_ttm} | industry={r.industry}")

    assert len(results) > 0, "Should find ETFs with 3%+ dividend yield"
    print("PASSED")


def test_etf_screener_invalid_industry():
    """Verify fuzzy matching error for invalid ETF industry."""
    print("\n=== Test: ETF Screener — invalid industry fuzzy match ===")
    results, error = screen_etfs(
        industries=["equity_etfz"],
    )

    assert results is None, "Should return None for invalid industry"
    assert error is not None, "Should return error message"
    assert "Invalid" in error or "Did you mean" in error, f"Expected fuzzy match error, got: {error}"
    print(f"Got expected error: {error[:100]}...")
    print("PASSED")


if __name__ == "__main__":
    test_equity_screener_basic()
    test_equity_screener_multi_industry()
    test_equity_screener_invalid_sector()
    test_etf_screener_basic()
    test_etf_screener_high_dividend()
    test_etf_screener_invalid_industry()
    print("\n=== ALL TESTS PASSED ===")
