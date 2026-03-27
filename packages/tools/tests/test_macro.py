"""Test macro tools: commodity_prices, us_treasury_rates, macro_indicators."""

from helpers import parse_result, assert_success, run_test, print_summary
from prophitai_tools.macro.commodity_prices import commodity_prices
from prophitai_tools.macro.us_rates import us_treasury_rates
from prophitai_tools.macro.indicators import macro_indicators


def test_commodity_prices():
    raw = commodity_prices(symbols=["GCUSD", "CLUSD"], days_back=14)
    result = parse_result(raw)
    data = assert_success(result, "commodity_prices")
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) > 0, "Expected non-empty data"
    assert "GCUSD_close" in data[0], f"Missing GCUSD_close key in {data[0].keys()}"


def test_us_treasury_rates():
    raw = us_treasury_rates(maturities=["y2", "y10"], days_back=14)
    result = parse_result(raw)
    data = assert_success(result, "us_treasury_rates")
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) > 0, "Expected non-empty data"
    assert "y2" in data[0], f"Missing y2 key in {data[0].keys()}"
    assert "y10" in data[0], f"Missing y10 key in {data[0].keys()}"


def test_macro_indicators():
    raw = macro_indicators(indicators=["CPI", "federalFunds"], years_back=1)
    result = parse_result(raw)
    data = assert_success(result, "macro_indicators")
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    assert "CPI" in data, f"Missing CPI key in {data.keys()}"
    assert "federalFunds" in data, f"Missing federalFunds key in {data.keys()}"


def main():
    results = []
    results.append(run_test("commodity_prices", test_commodity_prices))
    results.append(run_test("us_treasury_rates", test_us_treasury_rates))
    results.append(run_test("macro_indicators", test_macro_indicators))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
