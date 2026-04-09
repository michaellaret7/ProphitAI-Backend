"""Test 1 — LLM tool selection for worker agent delegation.

Sends a task and a list of available tools in the prompt, and asks
the model to choose which tools a worker agent should be equipped with.
The model responds with structured JSON — no function-calling API used.
"""

import json

from prophitai_shared import get_backend


# ================================
# --> Fake tool catalogue
# ================================

FAKE_TOOL_CATALOGUE = [
    {
        "name": "get_portfolio_holdings",
        "category": "portfolio",
        "description": "Retrieve all current holdings in a user's portfolio including ticker, weight, and sector.",
    },
    {
        "name": "calculate_risk_metrics",
        "category": "portfolio",
        "description": "Calculate risk metrics (volatility, VaR, max drawdown, Sharpe ratio) for a list of tickers over a time period.",
    },
    {
        "name": "get_stock_news",
        "category": "news",
        "description": "Fetch recent news articles and press releases for a given stock ticker.",
    },
    {
        "name": "screen_equities",
        "category": "screener",
        "description": "Screen equities by market cap, sector, P/E ratio, dividend yield, and other fundamental filters.",
    },
    {
        "name": "get_macro_indicators",
        "category": "macro",
        "description": "Fetch macroeconomic indicators like GDP growth, CPI, unemployment rate, and fed funds rate.",
    },
    {
        "name": "optimize_portfolio",
        "category": "portfolio",
        "description": "Run mean-variance optimization to find optimal weights for a set of tickers given a target return or risk level.",
    },
    {
        "name": "get_stock_quote",
        "category": "market_data",
        "description": "Get the current price quote for a stock ticker.",
    },
    {
        "name": "get_earnings_transcript",
        "category": "research",
        "description": "Retrieve the full earnings call transcript for a company's most recent quarter.",
    },
    {
        "name": "get_factor_exposures",
        "category": "portfolio",
        "description": "Calculate factor exposures (value, momentum, quality, size, volatility) for a portfolio.",
    },
    {
        "name": "get_technical_indicators",
        "category": "technicals",
        "description": "Compute technical indicators (RSI, MACD, Bollinger Bands) for a ticker.",
    },
]

FAKE_TASK = (
    "Analyze my portfolio 'port_abc123' — get the current holdings, calculate the "
    "risk metrics, check factor exposures, and then optimize for max Sharpe ratio."
)

EXPECTED_TOOLS = {
    "get_portfolio_holdings",
    "calculate_risk_metrics",
    "get_factor_exposures",
    "optimize_portfolio",
}


def _build_tool_list_text() -> str:
    """Format the tool catalogue as a readable list for the prompt."""
    lines = []

    for tool in FAKE_TOOL_CATALOGUE:
        lines.append(f"- **{tool['name']}** [{tool['category']}]: {tool['description']}")

    return "\n".join(lines)


def test_tool_selection():
    """Ask Groq GPT-OSS-120b to choose tools for a worker agent given a task."""
    backend = get_backend(provider="groq", model="openai-gpt-oss-120b")

    print(f"Provider: groq")
    print(f"Model: {backend.model}")
    print(f"Task: {FAKE_TASK}\n")

    tool_list_text = _build_tool_list_text()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a planner agent. Your job is to select which tools a worker agent "
                "needs to complete a given task. You will be given a task description and a "
                "catalogue of available tools.\n\n"
                "Respond with ONLY a JSON object in this exact format:\n"
                "{\n"
                '  "selected_tools": ["tool_name_1", "tool_name_2"],\n'
                '  "reasoning": "Brief explanation of why each tool is needed."\n'
                "}\n\n"
                "Rules:\n"
                "- Only select tools the worker actually needs for the task.\n"
                "- Do not select tools that are irrelevant to the task.\n"
                "- Order the tools in the sequence the worker should use them.\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"## Available Tools\n\n{tool_list_text}\n\n"
                f"## Task\n\n{FAKE_TASK}\n\n"
                "Select the tools this worker agent needs."
            ),
        },
    ]

    import time
    start_time = time.time()
    response = backend.call_llm_json(
        messages=messages,
        temperature=0.7,
    )
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    # --- Parse response ---

    print(f"Raw response:\n{response}\n")

    parsed = json.loads(response)
    selected = parsed["selected_tools"]
    reasoning = parsed.get("reasoning", "")

    print(f"Selected tools: {selected}")
    print(f"Reasoning: {reasoning}\n")


if __name__ == "__main__":
    test_tool_selection()
