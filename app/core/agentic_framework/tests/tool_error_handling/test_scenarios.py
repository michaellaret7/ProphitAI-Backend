"""
Reusable test scenario library for tool error testing.

This module provides pre-defined error scenarios that can be reused across
different tools to test common error patterns.
"""

from typing import List, Dict


# ============================================================================
# WRONG TYPE SCENARIOS
# ============================================================================

WRONG_TYPE_SCENARIOS = {
    "ticker_string_to_int": "Pass 'ticker' as integer 12345 instead of string",
    "ticker_string_to_list": "Pass 'ticker' as list ['AAPL'] instead of string",
    "ticker_string_to_dict": "Pass 'ticker' as dict {'ticker': 'AAPL'} instead of string",

    "portfolio_dict_to_string": "Pass 'portfolio_dict' as string 'invalid' instead of dictionary",
    "portfolio_dict_to_int": "Pass 'portfolio_dict' as integer 12345 instead of dictionary",
    "portfolio_dict_to_list": "Pass 'portfolio_dict' as list ['AAPL'] instead of dictionary",

    "tickers_list_to_string": "Pass 'tickers' as string 'AAPL,MSFT' instead of list",
    "tickers_list_to_dict": "Pass 'tickers' as dict instead of list",

    "lookback_days_to_string": "Pass 'lookback_days' as string '252' instead of integer",
    "lookback_days_to_float": "Pass 'lookback_days' as float 252.5 instead of integer",
}


# ============================================================================
# MISSING ARGUMENT SCENARIOS
# ============================================================================

MISSING_ARG_SCENARIOS = {
    "missing_ticker": "Call the function without the required 'ticker' parameter",
    "missing_portfolio_dict": "Call the function without the required 'portfolio_dict' parameter",
    "missing_factor": "Call the function without the required 'factor' parameter",
    "missing_data_type": "Call the function without the required 'data_type' parameter",
    "missing_tickers": "Call the function without the required 'tickers' parameter",
    "missing_group_by": "Call the function without the required 'group_by' parameter",
    "missing_statement_type": "Call the function without the required 'statement_type' parameter",
    "missing_industry": "Call the function without the required 'industry' parameter",
    "missing_sub_industry": "Call the function without the required 'sub_industry' parameter",
}


# ============================================================================
# INVALID VALUE SCENARIOS
# ============================================================================

INVALID_VALUE_SCENARIOS = {
    "empty_ticker": "Pass empty string '' for 'ticker' parameter",
    "numeric_only_ticker": "Pass numeric-only string '12345' for 'ticker' parameter",
    "multiple_tickers_in_string": "Pass multiple tickers 'AAPL,MSFT' in single ticker parameter",

    "empty_portfolio": "Pass empty dictionary {} for 'portfolio_dict'",
    "portfolio_missing_allocation": "Pass portfolio_dict with ticker missing 'allocation' key: {'AAPL': {'position': 'long'}}",
    "portfolio_missing_position": "Pass portfolio_dict with ticker missing 'position' key: {'AAPL': {'allocation': 0.5}}",
    "portfolio_invalid_allocation": "Pass portfolio_dict with allocation outside 0-1 range: {'AAPL': {'allocation': 1.5, 'position': 'long'}}",
    "portfolio_invalid_position": "Pass portfolio_dict with invalid position value: {'AAPL': {'allocation': 0.5, 'position': 'invalid'}}",
    "portfolio_negative_allocation": "Pass portfolio_dict with negative allocation: {'AAPL': {'allocation': -0.5, 'position': 'long'}}",

    "negative_lookback": "Pass negative number -252 for 'lookback_days' parameter",
    "zero_lookback": "Pass zero 0 for 'lookback_days' parameter",

    "empty_tickers_list": "Pass empty list [] for 'tickers' parameter",
    "tickers_with_empty_string": "Pass list with empty string ['AAPL', '', 'MSFT'] for 'tickers' parameter",

    "invalid_factor_enum": "Pass invalid factor 'invalid_factor' (not in allowed values)",
    "invalid_data_type_enum": "Pass invalid data_type 'invalid_type' (not in allowed values)",
    "invalid_statement_type_enum": "Pass invalid statement_type 'invalid_statement' (not in allowed values)",
}


# ============================================================================
# SUCCESS SCENARIOS
# ============================================================================

SUCCESS_SCENARIOS = {
    "portfolio_performance": "Call correctly with portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'MSFT': {'allocation': 0.5, 'position': 'long'}}",

    "portfolio_beta": "Call correctly with portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'MSFT': {'allocation': 0.5, 'position': 'long'}}, index_ticker='SPY'",

    "ticker_factors_growth": "Call correctly with ticker='AAPL', factor='growth'",
    "ticker_factors_value": "Call correctly with ticker='AAPL', factor='value'",
    "ticker_factors_momentum": "Call correctly with ticker='AAPL', factor='momentum'",

    "ticker_performance": "Call correctly with ticker='AAPL', lookback_days=252",

    "repository_data": "Call correctly with ticker='AAPL', data_type='stock_news'",

    "group_performance_industry": "Call correctly with portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}}, group_by='industry'",

    "ticker_fundamentals_income": "Call correctly with ticker='AAPL', statement_type='income_statement', quarters_back=4",
    "ticker_fundamentals_ratios": "Call correctly with ticker='AAPL', statement_type='financial_ratios', quarters_back=4",

    "industry_benchmark_growth": "Call correctly with industry='food_products', factor='growth'",
    "subindustry_benchmark_quality": "Call correctly with sub_industry='packaged_foods_and_meats', factor='quality'",
}


# ============================================================================
# TOOL-SPECIFIC TEST SUITES
# ============================================================================

def get_portfolio_tool_scenarios() -> List[str]:
    """Get standard test scenarios for portfolio tools (requires portfolio_dict)."""
    return [
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_string"],
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_int"],
        MISSING_ARG_SCENARIOS["missing_portfolio_dict"],
        INVALID_VALUE_SCENARIOS["empty_portfolio"],
        INVALID_VALUE_SCENARIOS["portfolio_missing_allocation"],
        INVALID_VALUE_SCENARIOS["portfolio_invalid_position"],
        SUCCESS_SCENARIOS["portfolio_performance"],
    ]


def get_ticker_tool_scenarios(success_key: str = "ticker_performance") -> List[str]:
    """Get standard test scenarios for ticker tools (requires single ticker)."""
    return [
        WRONG_TYPE_SCENARIOS["ticker_string_to_int"],
        WRONG_TYPE_SCENARIOS["ticker_string_to_list"],
        MISSING_ARG_SCENARIOS["missing_ticker"],
        INVALID_VALUE_SCENARIOS["empty_ticker"],
        INVALID_VALUE_SCENARIOS["numeric_only_ticker"],
        SUCCESS_SCENARIOS.get(success_key, "Call correctly with ticker='AAPL'"),
    ]


def get_ticker_factor_scenarios() -> List[str]:
    """Get test scenarios for ticker factor tools."""
    return [
        WRONG_TYPE_SCENARIOS["ticker_string_to_int"],
        MISSING_ARG_SCENARIOS["missing_ticker"],
        MISSING_ARG_SCENARIOS["missing_factor"],
        INVALID_VALUE_SCENARIOS["invalid_factor_enum"],
        SUCCESS_SCENARIOS["ticker_factors_growth"],
    ]


def get_custom_scenarios(scenario_keys: List[str]) -> List[str]:
    """
    Get custom list of scenarios by their keys.

    Args:
        scenario_keys: List of scenario keys from any of the scenario dicts

    Returns:
        List of scenario descriptions

    Example:
        scenarios = get_custom_scenarios([
            "portfolio_dict_to_string",
            "missing_portfolio_dict",
            "portfolio_performance"
        ])
    """
    all_scenarios = {
        **WRONG_TYPE_SCENARIOS,
        **MISSING_ARG_SCENARIOS,
        **INVALID_VALUE_SCENARIOS,
        **SUCCESS_SCENARIOS,
    }

    return [all_scenarios.get(key, f"Unknown scenario: {key}") for key in scenario_keys]


# ============================================================================
# QUICK ACCESS BY TOOL NAME
# ============================================================================

TOOL_SCENARIOS: Dict[str, List[str]] = {
    "calculate_portfolio_performance": [
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_string"],
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_int"],
        MISSING_ARG_SCENARIOS["missing_portfolio_dict"],
        INVALID_VALUE_SCENARIOS["portfolio_missing_allocation"],
        INVALID_VALUE_SCENARIOS["portfolio_invalid_position"],
        SUCCESS_SCENARIOS["portfolio_performance"],
    ],

    "calculate_portfolio_beta_vs_index": [
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_string"],
        MISSING_ARG_SCENARIOS["missing_portfolio_dict"],
        INVALID_VALUE_SCENARIOS["empty_portfolio"],
        WRONG_TYPE_SCENARIOS["ticker_string_to_int"],  # for index_ticker
        SUCCESS_SCENARIOS["portfolio_beta"],
    ],

    "calculate_portfolio_returns_metrics": [
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_string"],
        MISSING_ARG_SCENARIOS["missing_portfolio_dict"],
        INVALID_VALUE_SCENARIOS["portfolio_missing_position"],
        INVALID_VALUE_SCENARIOS["portfolio_negative_allocation"],
        SUCCESS_SCENARIOS["portfolio_performance"],
    ],

    "calculate_ticker_factors": [
        WRONG_TYPE_SCENARIOS["ticker_string_to_int"],
        MISSING_ARG_SCENARIOS["missing_ticker"],
        MISSING_ARG_SCENARIOS["missing_factor"],
        INVALID_VALUE_SCENARIOS["invalid_factor_enum"],
        INVALID_VALUE_SCENARIOS["empty_ticker"],
        SUCCESS_SCENARIOS["ticker_factors_growth"],
    ],

    "calculate_ticker_performance": [
        WRONG_TYPE_SCENARIOS["ticker_string_to_int"],
        MISSING_ARG_SCENARIOS["missing_ticker"],
        INVALID_VALUE_SCENARIOS["empty_ticker"],
        INVALID_VALUE_SCENARIOS["numeric_only_ticker"],
        SUCCESS_SCENARIOS["ticker_performance"],
    ],

    "calculate_ticker_performances": [
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_string"],
        MISSING_ARG_SCENARIOS["missing_portfolio_dict"],
        INVALID_VALUE_SCENARIOS["empty_portfolio"],
        SUCCESS_SCENARIOS["portfolio_performance"],
    ],

    "calculate_group_performances": [
        WRONG_TYPE_SCENARIOS["portfolio_dict_to_int"],
        MISSING_ARG_SCENARIOS["missing_portfolio_dict"],
        MISSING_ARG_SCENARIOS["missing_group_by"],
        INVALID_VALUE_SCENARIOS["empty_portfolio"],
        SUCCESS_SCENARIOS["group_performance_industry"],
    ],

    "get_ticker_fundamental_data": [
        WRONG_TYPE_SCENARIOS["ticker_string_to_int"],
        MISSING_ARG_SCENARIOS["missing_ticker"],
        MISSING_ARG_SCENARIOS["missing_statement_type"],
        INVALID_VALUE_SCENARIOS["empty_ticker"],
        INVALID_VALUE_SCENARIOS["invalid_statement_type_enum"],
        SUCCESS_SCENARIOS["ticker_fundamentals_income"],
        SUCCESS_SCENARIOS["ticker_fundamentals_ratios"],
    ],

    "get_industry_benchmark_calculations": [
        MISSING_ARG_SCENARIOS["missing_industry"],
        MISSING_ARG_SCENARIOS["missing_factor"],
        INVALID_VALUE_SCENARIOS["invalid_factor_enum"],
        SUCCESS_SCENARIOS["industry_benchmark_growth"],
    ],

    "get_sub_industry_benchmark_calculations": [
        MISSING_ARG_SCENARIOS["missing_sub_industry"],
        MISSING_ARG_SCENARIOS["missing_factor"],
        INVALID_VALUE_SCENARIOS["invalid_factor_enum"],
        SUCCESS_SCENARIOS["subindustry_benchmark_quality"],
    ],
}


def get_scenarios_for_tool(tool_name: str) -> List[str]:
    """
    Get pre-configured test scenarios for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        List of test scenario descriptions

    Example:
        scenarios = get_scenarios_for_tool("calculate_portfolio_performance")
    """
    if tool_name not in TOOL_SCENARIOS:
        # Return generic scenarios if tool not configured
        return [
            "Pass wrong type for first parameter",
            "Omit required parameter",
            "Call correctly with valid parameters",
        ]

    return TOOL_SCENARIOS[tool_name]


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    """Example usage of the test scenario library."""

    print("="*80)
    print("EXAMPLE 1: Get portfolio tool scenarios")
    print("="*80)
    scenarios = get_portfolio_tool_scenarios()
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario}")

    print("\n" + "="*80)
    print("EXAMPLE 2: Get ticker factor scenarios")
    print("="*80)
    scenarios = get_ticker_factor_scenarios()
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario}")

    print("\n" + "="*80)
    print("EXAMPLE 3: Get scenarios for specific tool")
    print("="*80)
    scenarios = get_scenarios_for_tool("calculate_portfolio_performance")
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario}")

    print("\n" + "="*80)
    print("EXAMPLE 4: Custom scenario selection")
    print("="*80)
    scenarios = get_custom_scenarios([
        "portfolio_dict_to_string",
        "missing_portfolio_dict",
        "portfolio_performance"
    ])
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario}")