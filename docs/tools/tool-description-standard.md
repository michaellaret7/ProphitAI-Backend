# Tool Description Standard

Every agent tool description (docstring or schema constant) MUST follow this structured pattern. Tool descriptions are serialized into JSON schemas and sent to the LLM on **every iteration** of the agent loop — concise, structured descriptions reduce token cost and improve tool selection accuracy.

## Required Sections

Sections must appear in this order. Omit a section only if it genuinely does not apply.

```
1. Summary          — 1-3 sentences: what the tool does
2. WHEN TO USE      — Bullet list of scenarios (optional for simple tools)
3. IMPORTANT        — Critical constraints or gotchas (optional)
4. Args             — Parameter descriptions with types and examples
5. Returns          — Shape of the response
6. Interpretation   — How to read the output (optional, for numeric/financial tools)
7. Examples         — 1-2 concrete invocations
8. Raises           — Error conditions (optional)
```

## Rules

1. **Be concise.** Descriptions are sent on every LLM call across all iterations. Every extra line costs tokens multiplied by iteration count. A 10-iteration run with 100 extra tokens per tool × 20 tools = 20,000 wasted tokens.

2. **No redundant parameter docs.** The `Args` section is the single source of truth for parameters. Do not duplicate parameter descriptions in the body text, "PARAMETERS" blocks, or separate bullet lists.

3. **Max 2 examples.** One simple, one with optional params. No need for 3+ examples.

4. **No anti-pattern lists.** "DO NOT" sections and "Bad vs Good" comparisons bloat the schema. State the correct approach once instead.

5. **No verbose section explanations.** State what each section is — don't explain why it matters or give coaching on how to write it well.

6. **Keep the summary actionable.** Lead with what the tool does, not what it "helps with" or "enables".

## Template

```python
@agent_tool(name="tool_name", category="category_name")
def tool_name(
    param_a: list[str],
    param_b: list[float],
    param_c: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """One-line summary of what this tool does.

Optional 1-2 sentence elaboration on behavior or output format.

**WHEN TO USE:**
- Scenario A
- Scenario B
- Scenario C

**IMPORTANT:**
- Critical constraint or gotcha
- Another constraint

    Args:
        param_a: Description with example (e.g., ['AAPL', 'MSFT'])
        param_b: Description with format note.
            0.30 = 30%. Negative = short. (e.g., [0.40, 0.35, 0.25])
        param_c: Description with default note (default 1)

    Returns:
        YAML-formatted result:
        - field_a: description
        - field_b: {sub_field: description}

    Interpretation Guide:
        field_a: What this number means. 1.0 = fully invested.
        field_b: What this number means. -0.02 = 2% loss.

    Examples:
        tool_name(
            param_a=["AAPL", "MSFT", "JPM"],
            param_b=[0.40, 0.35, 0.25]
        )

        tool_name(
            param_a=["AAPL", "TSLA"],
            param_b=[0.60, -0.20],
            param_c=2
        )

    Raises:
        ValueError: If param_a and param_b have different lengths
    """
```

## Real Example

From `packages/tools/src/prophitai_tools/portfolio/classification.py`:

```python
@agent_tool(name="portfolio_classification", category="portfolio")
def portfolio_classification(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """Analyze portfolio exposure breakdown by sector, industry, and sub-industry.

Returns concentration (weight allocation), group-level 99% VaR, and constituent
tickers for each classification group, plus portfolio-level exposure metrics.

**WHEN TO USE:**
- Understanding sector/industry diversification of a portfolio
- Identifying concentration risk in specific sectors or industries
- Checking long/short/net/gross exposure metrics
- Reviewing which tickers belong to which classification groups

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Concentration is the sum of weights in that group (can be negative for short-heavy groups).
- VaR 99% is the daily 1% worst-case loss contribution from that group at portfolio weights.
- Groups are sorted by absolute concentration (largest exposure first).

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        years_back: Number of years of historical data for VaR calculation (default 1)

    Returns:
        YAML-formatted classification breakdown:
        - exposures: net_exposure, gross_exposure, long_exposure, short_exposure
        - sector: {group_name: {concentration, var_99, tickers}}
        - industry: {group_name: {concentration, var_99, tickers}}
        - sub_industry: {group_name: {concentration, var_99, tickers}}

    Interpretation Guide:
        net_exposure: Sum of all weights. 1.0 = fully invested long. 0.0 = market-neutral.
        gross_exposure: Sum of absolute weights. Measures total capital deployed. 130/30 = 1.6.
        long_exposure: Sum of positive weights.
        short_exposure: Sum of absolute negative weights.
        concentration: Weight allocated to that group. 0.40 = 40% of portfolio.
        var_99: Daily 99% VaR for that group's contribution to portfolio risk.
            -0.02 means a 1% chance of losing 2%+ from that group on any given day.

    Examples:
        portfolio_classification(
            tickers=["AAPL", "MSFT", "JPM", "XOM", "PG"],
            weights=[0.25, 0.25, 0.20, 0.15, 0.15]
        )

        portfolio_classification(
            tickers=["AAPL", "TSLA", "JPM", "XOM"],
            weights=[0.40, -0.15, 0.35, 0.40],
            years_back=2
        )

    Raises:
        ValueError: If tickers and weights have different lengths or no price data found
    """
```

## Schema Constants (Non-Decorator Tools)

For tools that use manual schema dicts (e.g., `deploy_worker_agent`), apply the same structure in the `DESCRIPTION` constant. Keep the `description` fields in `PARAMETERS` dict short — one line each — since the main description already covers usage.
