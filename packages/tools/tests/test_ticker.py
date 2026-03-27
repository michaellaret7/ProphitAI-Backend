"""Test ticker tools: analytics, info, sectors, fundamentals (16 tools)."""

from helpers import parse_result, assert_success, run_test, print_summary

# ================================
# --> Imports: analytics
# ================================
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.risk import ticker_risk
from prophitai_tools.ticker.factors import ticker_factors
from prophitai_tools.ticker.technicals import ticker_technicals

# ================================
# --> Imports: info
# ================================
from prophitai_tools.ticker.info.description import get_ticker_info, get_etf_info
from prophitai_tools.ticker.info.peers import get_ticker_peers
from prophitai_tools.ticker.info.ratings import get_stock_ratings
from prophitai_tools.ticker.info.institutional_holders import get_institutional_holders
from prophitai_tools.ticker.info.product_segmentation import get_product_segmentation
from prophitai_tools.ticker.info.etf_holdings import get_etf_holdings

# ================================
# --> Imports: sectors
# ================================
from prophitai_tools.ticker.info.sectors import get_sector_industries, get_group_tickers

# ================================
# --> Imports: fundamentals
# ================================
from prophitai_tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from prophitai_tools.ticker.fundamentals.estimates import get_analyst_estimates
from prophitai_tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from prophitai_tools.ticker.fundamentals.price_target import get_price_target_data


# ================================
# --> Tests: analytics
# ================================

def test_ticker_performance():
    raw = ticker_performance(tickers=["AAPL", "MSFT"], years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "ticker_performance")
    assert "results" in data, f"Missing 'results' key in {data.keys()}"


def test_ticker_risk():
    raw = ticker_risk(tickers=["AAPL", "MSFT"], years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "ticker_risk")
    assert "results" in data, f"Missing 'results' key in {data.keys()}"


def test_ticker_factors():
    raw = ticker_factors(tickers=["AAPL"], category="all", years_back=2)
    result = parse_result(raw)
    data = assert_success(result, "ticker_factors")
    assert "results" in data, f"Missing 'results' key in {data.keys()}"


def test_ticker_technicals():
    raw = ticker_technicals(tickers=["AAPL"], category="trend", days=20)
    result = parse_result(raw)
    data = assert_success(result, "ticker_technicals")
    assert "results" in data, f"Missing 'results' key in {data.keys()}"


# ================================
# --> Tests: info
# ================================

def test_get_ticker_info():
    raw = get_ticker_info(tickers=["AAPL"])
    result = parse_result(raw)
    data = assert_success(result, "get_ticker_info")
    assert "AAPL" in data.get("results", data), f"Missing 'AAPL' in results"


def test_get_etf_info():
    raw = get_etf_info(tickers=["SPY"])
    result = parse_result(raw)
    data = assert_success(result, "get_etf_info")
    assert "SPY" in data.get("results", data), f"Missing 'SPY' in results"


def test_get_ticker_peers():
    raw = get_ticker_peers(ticker="AAPL")
    result = parse_result(raw)
    data = assert_success(result, "get_ticker_peers")
    assert isinstance(data, (list, dict)), f"Expected list or dict, got {type(data)}"


def test_get_stock_ratings():
    raw = get_stock_ratings(tickers=["AAPL"], data_type="summary")
    result = parse_result(raw)
    data = assert_success(result, "get_stock_ratings")
    # Reason: summary mode returns a flat dict with 'symbol' key, not nested by ticker
    assert data is not None, "Expected non-None data"


def test_get_institutional_holders():
    raw = get_institutional_holders(ticker="AAPL", year=2025, quarter=4, row_limit=10)
    result = parse_result(raw)
    data = assert_success(result, "get_institutional_holders")
    assert isinstance(data, (list, dict)), f"Expected list or dict, got {type(data)}"


def test_get_product_segmentation():
    raw = get_product_segmentation(ticker="AAPL")
    result = parse_result(raw)
    data = assert_success(result, "get_product_segmentation")
    assert data is not None, "Expected non-None data"


def test_get_etf_holdings():
    raw = get_etf_holdings(ticker="SPY", limit=10)
    result = parse_result(raw)
    data = assert_success(result, "get_etf_holdings")
    assert isinstance(data, (list, dict)), f"Expected list or dict, got {type(data)}"


# ================================
# --> Tests: sectors
# ================================

def test_get_sector_industries():
    raw = get_sector_industries(sector="equity_sector_information_technology")
    result = parse_result(raw)
    data = assert_success(result, "get_sector_industries")
    assert isinstance(data, (list, dict)), f"Expected list or dict, got {type(data)}"


def test_get_group_tickers():
    raw = get_group_tickers(group="equity_sector_information_technology", group_type="sector")
    result = parse_result(raw)
    data = assert_success(result, "get_group_tickers")
    assert isinstance(data, (list, dict)), f"Expected list or dict, got {type(data)}"


# ================================
# --> Tests: fundamentals
# ================================

def test_get_ticker_fundamental_data():
    raw = get_ticker_fundamental_data(ticker="AAPL", statement_type="income_statement", quarters_back=2)
    result = parse_result(raw)
    data = assert_success(result, "get_ticker_fundamental_data")
    assert data is not None, "Expected non-None data"


def test_get_analyst_estimates():
    raw = get_analyst_estimates(tickers=["AAPL"], periods_back=4, period="quarter", outlook="all")
    result = parse_result(raw)
    data = assert_success(result, "get_analyst_estimates")
    assert "AAPL" in data.get("results", data), f"Missing 'AAPL' in results"


def test_get_ratios_ttm():
    raw = get_ratios_ttm(tickers=["AAPL"])
    result = parse_result(raw)
    data = assert_success(result, "get_ratios_ttm")
    assert "AAPL" in data.get("results", data), f"Missing 'AAPL' in results"


def test_get_price_target_data():
    raw = get_price_target_data(tickers=["AAPL"], data_type="consensus")
    result = parse_result(raw)
    data = assert_success(result, "get_price_target_data")
    assert "AAPL" in data.get("results", data), f"Missing 'AAPL' in results"


def main():
    results = []

    print("\n=== ANALYTICS ===")
    results.append(run_test("ticker_performance", test_ticker_performance))
    results.append(run_test("ticker_risk", test_ticker_risk))
    results.append(run_test("ticker_factors", test_ticker_factors))
    results.append(run_test("ticker_technicals", test_ticker_technicals))

    print("\n=== INFO ===")
    results.append(run_test("get_ticker_info", test_get_ticker_info))
    results.append(run_test("get_etf_info", test_get_etf_info))
    results.append(run_test("get_ticker_peers", test_get_ticker_peers))
    results.append(run_test("get_stock_ratings", test_get_stock_ratings))
    results.append(run_test("get_institutional_holders", test_get_institutional_holders))
    results.append(run_test("get_product_segmentation", test_get_product_segmentation))
    results.append(run_test("get_etf_holdings", test_get_etf_holdings))

    print("\n=== SECTORS ===")
    results.append(run_test("get_sector_industries", test_get_sector_industries))
    results.append(run_test("get_group_tickers", test_get_group_tickers))

    print("\n=== FUNDAMENTALS ===")
    results.append(run_test("get_ticker_fundamental_data", test_get_ticker_fundamental_data))
    results.append(run_test("get_analyst_estimates", test_get_analyst_estimates))
    results.append(run_test("get_ratios_ttm", test_get_ratios_ttm))
    results.append(run_test("get_price_target_data", test_get_price_target_data))

    print_summary(results)
    return results


if __name__ == "__main__":
    main()
