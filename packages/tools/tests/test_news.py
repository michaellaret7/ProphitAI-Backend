"""Test news tools: general_news, get_ticker_news, get_press_releases."""

from helpers import parse_result, assert_success, run_test, print_summary
from prophitai_tools.news.general_news import general_news
from prophitai_tools.news.ticker_news import get_ticker_news
from prophitai_tools.news.press_releases import get_press_releases


def test_general_news():
    raw = general_news(days_back=7, limit=5, max_text_length=300)
    result = parse_result(raw)
    data = assert_success(result, "general_news")
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) > 0, "Expected non-empty data"
    assert "title" in data[0], f"Missing 'title' key in {data[0].keys()}"


def test_get_ticker_news():
    raw = get_ticker_news(ticker="AAPL", news_type="stock_news", limit=5, days_back=30)
    result = parse_result(raw)
    data = assert_success(result, "get_ticker_news")
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) > 0, "Expected non-empty data"


def test_get_press_releases():
    raw = get_press_releases(ticker="AAPL", days_back=90, row_limit=5)
    result = parse_result(raw)
    data = assert_success(result, "get_press_releases")
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) > 0, "Expected non-empty data"


def main():
    results = []
    results.append(run_test("general_news", test_general_news))
    results.append(run_test("get_ticker_news", test_get_ticker_news))
    results.append(run_test("get_press_releases", test_get_press_releases))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
