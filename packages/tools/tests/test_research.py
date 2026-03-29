"""Test research tools (7 tools). May SKIP if Foundry/Pinecone not configured."""

from helpers import parse_result, assert_success, run_test, print_summary
from prophitai_tools.research.macro_research import macro_research
from prophitai_tools.research.earnings_calls import earnings_call_search
from prophitai_tools.research.credit_research import credit_research_search
from prophitai_tools.research.economics_research import economics_research_search
from prophitai_tools.research.tax_research import tax_research_search
from prophitai_tools.research.theory_research import theory_research
from prophitai_tools.research.user_uploads import user_upload_search


def test_macro_research():
    raw = macro_research(query="Federal Reserve interest rate outlook 2026", top_k=3)
    result = parse_result(raw)
    data = assert_success(result, "macro_research")
    assert data is not None


def test_earnings_call_search():
    raw = earnings_call_search(query="Apple iPhone revenue guidance", ticker="AAPL", top_k=3)
    result = parse_result(raw)
    data = assert_success(result, "earnings_call_search")
    assert data is not None


def test_credit_research_search():
    raw = credit_research_search(query="High yield credit spread outlook", top_k=3)
    result = parse_result(raw)
    data = assert_success(result, "credit_research_search")
    assert data is not None


def test_economics_research_search():
    raw = economics_research_search(query="ISM Manufacturing PMI latest reading", top_k=3)
    result = parse_result(raw)
    data = assert_success(result, "economics_research_search")
    assert data is not None


def test_tax_research_search():
    raw = tax_research_search(query="Capital gains tax rates 2025", top_k=3)
    result = parse_result(raw)
    data = assert_success(result, "tax_research_search")
    assert data is not None


def test_theory_research():
    raw = theory_research(query="Modern portfolio theory mean-variance optimization", top_k=3)
    result = parse_result(raw)
    data = assert_success(result, "theory_research")
    assert data is not None


def test_user_upload_search():
    raw = user_upload_search(query="test query", clerk_id="test_clerk_id", top_k=3)
    result = parse_result(raw)
    # Reason: likely returns error since test_clerk_id doesn't exist, but tool should not crash
    assert result is not None, "Expected a valid YAML response"
    print(f"  Result success={result.get('success')}")


def main():
    results = []
    results.append(run_test("macro_research", test_macro_research))
    results.append(run_test("earnings_call_search", test_earnings_call_search))
    results.append(run_test("credit_research_search", test_credit_research_search))
    results.append(run_test("economics_research_search", test_economics_research_search))
    results.append(run_test("tax_research_search", test_tax_research_search))
    results.append(run_test("theory_research", test_theory_research))
    results.append(run_test("user_upload_search", test_user_upload_search))
    print_summary(results)
    return results


if __name__ == "__main__":
    main()
