"""Test screener tools: equity_screener, etf_screener."""

from helpers import parse_result, assert_success, run_test, print_summary
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.screener.etf_screener import etf_screener


def test_equity_screener():
    raw = equity_screener(sectors=["equity_sector_financials"], pe_ratio_ttm=[None, 15])
    result = parse_result(raw)
    data = assert_success(result, "equity_screener")
    assert data is not None, "Expected non-None data"


def test_etf_screener():
    raw = etf_screener(industries=["equity_etfs"])
    result = parse_result(raw)
    data = assert_success(result, "etf_screener")
    assert data is not None, "Expected non-None data"


def main():
    results = []
    results.append(run_test("equity_screener", test_equity_screener))
    results.append(run_test("etf_screener", test_etf_screener))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
