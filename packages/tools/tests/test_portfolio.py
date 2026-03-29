"""Test portfolio tools (9 tools)."""

from helpers import parse_result, assert_success, assert_error, run_test, print_summary

from prophitai_tools.portfolio.performance import portfolio_performance
from prophitai_tools.portfolio.risk import portfolio_risk
from prophitai_tools.portfolio.stress_test import portfolio_stress_test
from prophitai_tools.portfolio.factor_exposure import portfolio_factor_exposure
from prophitai_tools.portfolio.classification import portfolio_classification
from prophitai_tools.portfolio.covariance import portfolio_covariance
from prophitai_tools.portfolio.correlation import portfolio_correlation
from prophitai_tools.portfolio.allocator import portfolio_allocator
from prophitai_tools.portfolio.user_portfolio import get_user_simulated_portfolio

TICKERS = ["AAPL", "MSFT", "JNJ", "KO"]
WEIGHTS = [0.30, 0.30, 0.20, 0.20]


def test_portfolio_performance():
    raw = portfolio_performance(tickers=TICKERS, weights=WEIGHTS, years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "portfolio_performance")
    assert data is not None, "Expected non-None data"


def test_portfolio_risk():
    raw = portfolio_risk(tickers=TICKERS, weights=WEIGHTS, years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "portfolio_risk")
    assert data is not None, "Expected non-None data"


def test_portfolio_stress_test():
    raw = portfolio_stress_test(
        tickers=TICKERS, weights=WEIGHTS,
        shocks={"SPY": -0.05, "TLT": 0.10},
        years_back=2,
    )
    result = parse_result(raw)
    data = assert_success(result, "portfolio_stress_test")
    assert data is not None, "Expected non-None data"


def test_portfolio_factor_exposure():
    raw = portfolio_factor_exposure(tickers=TICKERS, weights=WEIGHTS, years_back=2)
    result = parse_result(raw)
    data = assert_success(result, "portfolio_factor_exposure")
    assert data is not None, "Expected non-None data"


def test_portfolio_classification():
    raw = portfolio_classification(tickers=TICKERS, weights=WEIGHTS, years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "portfolio_classification")
    assert data is not None, "Expected non-None data"


def test_portfolio_covariance():
    raw = portfolio_covariance(tickers=TICKERS, weights=WEIGHTS, years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "portfolio_covariance")
    assert data is not None, "Expected non-None data"


def test_portfolio_correlation():
    raw = portfolio_correlation(tickers=TICKERS, weights=WEIGHTS, years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "portfolio_correlation")
    assert data is not None, "Expected non-None data"


def test_portfolio_allocator():
    raw = portfolio_allocator(
        tickers=["AAPL", "MSFT", "JNJ", "KO", "TLT"],
        strategy="max_sharpe",
    )
    result = parse_result(raw)
    data = assert_success(result, "portfolio_allocator")
    assert data is not None, "Expected non-None data"


def test_get_user_simulated_portfolio_error():
    """Test error path with fake UUID."""
    raw = get_user_simulated_portfolio(portfolio_id="00000000-0000-0000-0000-000000000000")
    result = parse_result(raw)
    assert_error(result, "get_user_simulated_portfolio (fake UUID)")


def main():
    results = []
    results.append(run_test("portfolio_performance", test_portfolio_performance))
    results.append(run_test("portfolio_risk", test_portfolio_risk))
    results.append(run_test("portfolio_stress_test", test_portfolio_stress_test))
    results.append(run_test("portfolio_factor_exposure", test_portfolio_factor_exposure))
    results.append(run_test("portfolio_classification", test_portfolio_classification))
    results.append(run_test("portfolio_covariance", test_portfolio_covariance))
    results.append(run_test("portfolio_correlation", test_portfolio_correlation))
    results.append(run_test("portfolio_allocator", test_portfolio_allocator))
    results.append(run_test("get_user_simulated_portfolio", test_get_user_simulated_portfolio_error))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
