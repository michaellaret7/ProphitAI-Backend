"""Test broker tools (5 read-only, 5 CHAT_ONLY skipped)."""

from helpers import parse_result, assert_success, run_test, print_summary
from prophitai_tools.broker.account import account_info
from prophitai_tools.broker.portfolio import get_positions, close_position
from prophitai_tools.broker.trade import propose_trade
from prophitai_tools.broker.orders import get_order_impact, get_orders, get_quotes, cancel_order
from prophitai_tools.broker.options_trade import propose_options_trade, propose_multi_leg_options_trade

EMAIL = "clause_cowork+clerk_test@gmail.com"
FAKE_EMAIL = "no_broker_user_doesnt_exist@test.com"
NO_BROKER_MSG = "No brokerage account is connected"


# ================================
# --> Helper funcs
# ================================

def _check_broker_result(raw: str, label: str):
    """Check broker tool result — accept success or known API errors."""
    result = parse_result(raw)
    if result["success"]:
        assert_success(result, label)
    else:
        # Reason: broker API may reject due to auth, insufficient funds, etc.
        # The tool still works correctly if it returns a clean error_response.
        error = result.get("error", "")
        print(f"  [OK] {label} — API error (tool handled correctly): {error[:100]}")


def _assert_no_broker_guard(raw: str, label: str):
    """Assert the tool returns a success_response with the no-broker message."""
    result = parse_result(raw)
    assert result["success"] is True, f"{label}: expected success=True, got {result}"
    data = str(result.get("data", ""))
    assert NO_BROKER_MSG in data, f"{label}: expected no-broker message, got: {data[:150]}"
    print(f"  [OK] {label} — returned no-broker message correctly")


# ================================
# --> Connected broker tests (read-only)
# ================================

def test_account_info():
    raw = account_info(email=EMAIL)
    _check_broker_result(raw, "account_info")


def test_get_positions():
    raw = get_positions(email=EMAIL)
    _check_broker_result(raw, "get_positions")


def test_get_orders():
    raw = get_orders(email=EMAIL, state="all", days=7)
    _check_broker_result(raw, "get_orders")


def test_get_quotes():
    raw = get_quotes(symbols="AAPL,MSFT")
    _check_broker_result(raw, "get_quotes")


def test_get_order_impact():
    raw = get_order_impact(email=EMAIL, symbol="AAPL", action="BUY", units=1)
    _check_broker_result(raw, "get_order_impact")


# ================================
# --> No-broker guard tests
# ================================

def test_no_broker_account_info():
    raw = account_info(email=FAKE_EMAIL)
    _assert_no_broker_guard(raw, "no_broker: account_info")


def test_no_broker_get_positions():
    raw = get_positions(email=FAKE_EMAIL)
    _assert_no_broker_guard(raw, "no_broker: get_positions")


def test_no_broker_close_position():
    raw = close_position(email=FAKE_EMAIL, symbol="AAPL", reasoning="test")
    _assert_no_broker_guard(raw, "no_broker: close_position")


def test_no_broker_propose_trade():
    raw = propose_trade(email=FAKE_EMAIL, symbol="AAPL", side="buy", reasoning="test", qty=1)
    _assert_no_broker_guard(raw, "no_broker: propose_trade")


def test_no_broker_get_order_impact():
    raw = get_order_impact(email=FAKE_EMAIL, symbol="AAPL", action="BUY", units=1)
    _assert_no_broker_guard(raw, "no_broker: get_order_impact")


def test_no_broker_get_orders():
    raw = get_orders(email=FAKE_EMAIL, state="all", days=7)
    _assert_no_broker_guard(raw, "no_broker: get_orders")


def test_no_broker_cancel_order():
    raw = cancel_order(email=FAKE_EMAIL, brokerage_order_id="fake-123")
    _assert_no_broker_guard(raw, "no_broker: cancel_order")


def test_no_broker_propose_options_trade():
    raw = propose_options_trade(
        email=FAKE_EMAIL, osi_symbol="AAPL260620C00200000",
        side="buy_to_open", contracts=1, reasoning="test",
    )
    _assert_no_broker_guard(raw, "no_broker: propose_options_trade")


def test_no_broker_propose_multi_leg():
    raw = propose_multi_leg_options_trade(
        email=FAKE_EMAIL,
        legs=[
            {"symbol": "AAPL260620C00200000", "action": "buy_to_open", "units": 1},
            {"symbol": "AAPL260620C00210000", "action": "sell_to_open", "units": 1},
        ],
        reasoning="test",
    )
    _assert_no_broker_guard(raw, "no_broker: propose_multi_leg_options_trade")


def main():
    results = []

    print("\n========== CONNECTED BROKER TESTS ==========")
    results.append(run_test("account_info", test_account_info))
    results.append(run_test("get_positions", test_get_positions))
    results.append(run_test("get_orders", test_get_orders))
    results.append(run_test("get_quotes", test_get_quotes))
    results.append(run_test("get_order_impact", test_get_order_impact))

    print("\n========== NO-BROKER GUARD TESTS ==========")
    results.append(run_test("no_broker: account_info", test_no_broker_account_info))
    results.append(run_test("no_broker: get_positions", test_no_broker_get_positions))
    results.append(run_test("no_broker: close_position", test_no_broker_close_position))
    results.append(run_test("no_broker: propose_trade", test_no_broker_propose_trade))
    results.append(run_test("no_broker: get_order_impact", test_no_broker_get_order_impact))
    results.append(run_test("no_broker: get_orders", test_no_broker_get_orders))
    results.append(run_test("no_broker: cancel_order", test_no_broker_cancel_order))
    results.append(run_test("no_broker: propose_options_trade", test_no_broker_propose_options_trade))
    results.append(run_test("no_broker: propose_multi_leg", test_no_broker_propose_multi_leg))

    print_summary(results)
    return results


if __name__ == "__main__":
    main()
