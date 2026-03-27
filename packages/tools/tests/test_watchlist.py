"""Test watchlist tools (1 tool)."""

from helpers import parse_result, assert_error, run_test, print_summary
from prophitai_tools.watchlist.get_watchlist import get_watchlist


def test_get_watchlist_invalid_uuid():
    raw = get_watchlist(watchlist_id="not-a-uuid")
    result = parse_result(raw)
    assert_error(result, "get_watchlist (invalid UUID)")


def test_get_watchlist_not_found():
    raw = get_watchlist(watchlist_id="00000000-0000-0000-0000-000000000000")
    result = parse_result(raw)
    assert_error(result, "get_watchlist (not found)")


def main():
    results = []
    results.append(run_test("get_watchlist (invalid UUID)", test_get_watchlist_invalid_uuid))
    results.append(run_test("get_watchlist (not found)", test_get_watchlist_not_found))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
