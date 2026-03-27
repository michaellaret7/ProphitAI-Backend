"""Test options tools (5 tools, chained)."""

from helpers import parse_result, assert_success, run_test, print_summary
from prophitai_tools.options.expirations import get_option_expirations
from prophitai_tools.options.contracts import get_option_contracts
from prophitai_tools.options.chain import get_options_chain
from prophitai_tools.options.quote import get_option_quote
from prophitai_tools.options.price_history import get_option_price_history

# Reason: state shared between chained tests
_expiration = None
_osi_symbol = None


def test_expirations():
    global _expiration
    raw = get_option_expirations(underlying="AAPL")
    result = parse_result(raw)
    data = assert_success(result, "get_option_expirations")
    exps = data.get("expirations", [])
    assert len(exps) > 0, "Expected at least one expiration date"
    _expiration = exps[0]
    print(f"  Using expiration: {_expiration}")


def test_contracts():
    global _osi_symbol
    assert _expiration is not None, "Skipped — no expiration from step 1"
    raw = get_option_contracts(
        underlying="AAPL",
        expiration=_expiration,
        contract_type="call",
        limit=5,
    )
    result = parse_result(raw)
    data = assert_success(result, "get_option_contracts")
    contracts = data.get("contracts", data if isinstance(data, list) else [])
    assert len(contracts) > 0, "Expected at least one contract"
    _osi_symbol = contracts[0] if isinstance(contracts[0], str) else contracts[0].get("symbol", contracts[0].get("osi_symbol"))
    print(f"  Using OSI symbol: {_osi_symbol}")


def test_chain():
    assert _expiration is not None, "Skipped — no expiration from step 1"
    raw = get_options_chain(
        underlying="AAPL",
        expiration=_expiration,
        contract_type="call",
        limit=5,
    )
    result = parse_result(raw)
    data = assert_success(result, "get_options_chain")
    assert data is not None, "Expected non-None chain data"


def test_quote():
    assert _osi_symbol is not None, "Skipped — no OSI symbol from step 2"
    raw = get_option_quote(osi_symbol=_osi_symbol)
    result = parse_result(raw)
    data = assert_success(result, "get_option_quote")
    assert data is not None, "Expected non-None quote data"


def test_price_history():
    assert _osi_symbol is not None, "Skipped — no OSI symbol from step 2"
    raw = get_option_price_history(osi_symbol=_osi_symbol, timeframe="1d", limit=10)
    result = parse_result(raw)
    data = assert_success(result, "get_option_price_history")
    assert data is not None, "Expected non-None price history"


def main():
    results = []
    results.append(run_test("get_option_expirations", test_expirations))
    results.append(run_test("get_option_contracts", test_contracts))
    results.append(run_test("get_options_chain", test_chain))
    results.append(run_test("get_option_quote", test_quote))
    results.append(run_test("get_option_price_history", test_price_history))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
