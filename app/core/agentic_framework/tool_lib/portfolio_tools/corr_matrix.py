from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.core.config import DEFAULT_LOOKBACK_SHORT
from app.models.portfolio_models import PortfolioInput
import pandas as pd
from app.core.calculations.core.helpers import build_returns_df_from_price_map
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.utils.tool_validator import ToolValidator
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

@log_simulation_data_range()
def correlation_matrix(portfolio_dict: PortfolioInput | dict, filter: str = "all", _simulation_date: Optional[datetime] = None) -> str:
    """
    Calculate pairwise correlations and return as records for easy LLM consumption.

    Args:
        portfolio_dict: Portfolio holdings
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Output shape:
    {
      "correlations": [
        {"ticker1": "T1", "ticker2": "T2", "correlation": 0.123}
      ]
    }
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')

    try:

        # Use utility to get portfolio data
        weights, price_data, dividend_data = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=DEFAULT_LOOKBACK_SHORT,
            include_dividends=False,
            _simulation_date=_simulation_date
        )

        if not price_data:
            return success_response({"correlations": []})

        # Calculate returns without dropping rows globally; let correlation handle pairwise NaNs
        returns_df = build_returns_df_from_price_map(price_data, drop_rows='none', include_dividends=False)

        if returns_df.empty:
            return success_response({"correlations": []})

        # Compute correlation matrix and round
        corr_df = CorrelationAnalysis.correlation_matrix(returns_df)
        if corr_df is None or corr_df.empty:
            return success_response({"correlations": []})
        corr_df = corr_df.round(3)

        # Use the correlation matrix's own column order to avoid key-order drift
        ordered_tickers = [t for t in corr_df.columns if t in corr_df.index]

        # Build records for unique pairs (upper triangle, excluding diagonal)
        records = []
        for i, t1 in enumerate(ordered_tickers):
            for j in range(i + 1, len(ordered_tickers)):
                t2 = ordered_tickers[j]
                value = corr_df.loc[t1, t2]
                try:
                    value = float(value)
                except Exception:
                    pass

                if filter == "all":
                    records.append({
                        "pair": f"{t1} | {t2}",
                        "corr": value
                    })
                elif filter == "high":
                    if abs(value) >= 0.7:
                        records.append({
                            "pair": f"{t1} | {t2}",
                            "corr": value
                        })
                elif filter == "significant":
                    if abs(value) >= 0.5:
                        records.append({
                            "pair": f"{t1} | {t2}",
                            "corr": value
                        })
                elif filter == "low":
                    if abs(value) <= 0.3:
                        records.append({
                            "pair": f"{t1} | {t2}",
                            "corr": value
                        })
                elif filter == "negative_only":
                    if value < 0:
                        records.append({
                            "pair": f"{t1} | {t2}",
                            "corr": value
                        })
                elif filter == "positive_only":
                    if value > 0:
                        records.append({
                            "pair": f"{t1} | {t2}",
                            "corr": value
                        })
                else:
                    return error_response("Invalid filter")

        if records == []:
            return error_response(f"There are no correlations in this matrix fitting the {filter} criteria")

        return success_response({"correlations": records})
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
CORRELATION_MATRIX_DESCRIPTION = (
    "Calculate pairwise correlations between portfolio tickers using 252 trading days of price returns. "
    "Correlation measures how assets move together, ranging from -1 (perfect inverse) to +1 (perfect co-movement). "
    "\n\n**TOKEN EFFICIENCY - Use Filters to Reduce Response Size:**"
    "\n  For large portfolios, the full correlation matrix can consume significant tokens. Filters reduce response size by 60-90%."
    "\n  Example: 18-stock portfolio = 153 correlation pairs. With 'high' filter = ~8-15 pairs only (90% reduction)."
    "\n\n**Filter Options (default: 'all'):**"
    "\n  • 'all' - Return all pairwise correlations (full matrix)"
    "\n  • 'high' - Only |corr| ≥ 0.7 (concentration risk & strong hedges)"
    "\n  • 'significant' - Only |corr| ≥ 0.5 (material relationships worth monitoring)"
    "\n  • 'low' - Only |corr| ≤ 0.3 (diversification & independence)"
    "\n  • 'negative_only' - Only negative correlations (hedge analysis)"
    "\n  • 'positive_only' - Only positive correlations (co-movement analysis)"
    "\n\n**When to Use Each Filter:**"
    "\n  🔴 Risk Analysis → Use 'high': Identifies clustered positions that amplify portfolio risk"
    "\n  🟡 Position Monitoring → Use 'significant': Material relationships affecting portfolio behavior"
    "\n  🟢 Diversification Check → Use 'low': Validates that positions actually diversify each other"
    "\n  🔵 Hedge Discovery → Use 'negative_only': Find positions that naturally offset losses"
    "\n  🟠 Co-Movement Analysis → Use 'positive_only': Understand directional alignment"
    "\n\n**Industry Standard Thresholds (from academic finance):**"
    "\n  • |corr| ≥ 0.7: Very strong correlation - positions move together ~70%+ of the time"
    "\n  • |corr| ≥ 0.5: Strong correlation - material relationship affecting risk/return"
    "\n  • |corr| ≤ 0.3: Weak correlation - positions act independently (good diversification)"
    "\n  • |corr| near 0: No relationship - perfect diversification"
    "\n  • |corr| < 0: Inverse relationship - positions hedge each other"
    "\n\n**Output Format:**"
    "\n  {'correlations': [{'pair': 'AAPL | MSFT', 'corr': 0.712}, ...]} (rounded to 3 decimals)"
    "\n\n**Critical Requirements:**"
    "\n  • You MUST include portfolio_dict with ALL holdings (allocation + position)"
    "\n  • Choose appropriate filter for your analysis goal to minimize token usage"
    "\n  • If no correlations match filter criteria, error is returned - try broader filter"
    "\n\n**Examples:**"
    "\n  correlation_matrix(portfolio_dict={...}, filter='high')  # Check concentration risk"
    "\n  correlation_matrix(portfolio_dict={...}, filter='low')  # Validate diversification"
    "\n  correlation_matrix(portfolio_dict={...}, filter='negative_only')  # Find hedges"
)

CORRELATION_MATRIX_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "filter": {
            "type": "string",
            "description": (
                "Filter which correlations to return based on strength and direction. "
                "Reduces token usage by 60-90% for large portfolios. "
                "\n\n**Filter Options:**"
                "\n  • 'all' (default): Return all pairwise correlations"
                "\n  • 'high': Only |corr| ≥ 0.7 → Identify concentration risk or find very strong hedges"
                "\n  • 'significant': Only |corr| ≥ 0.5 → Material relationships worth monitoring"
                "\n  • 'low': Only |corr| ≤ 0.3 → Validate diversification effectiveness"
                "\n  • 'negative_only': Only corr < 0 → Find natural hedges (positions offsetting losses)"
                "\n  • 'positive_only': Only corr > 0 → Understand co-movement patterns"
                "\n\n**Thresholds (Industry Standards):**"
                "\n  • 0.7 = 'very strong correlation' (academic finance definition)"
                "\n  • 0.5 = 'material relationship' (portfolio management threshold)"
                "\n  • 0.3 = upper bound for 'essentially independent' assets"
                "\n\n**Token Efficiency Impact:**"
                "\n  • 8-stock portfolio: 28 pairs → 'high' filter returns ~3-5 pairs (82% reduction)"
                "\n  • 18-stock portfolio: 153 pairs → 'high' filter returns ~8-15 pairs (90% reduction)"
                "\n  • 30-stock portfolio: 435 pairs → 'high' filter returns ~20-35 pairs (92% reduction)"
                "\n\n**Error Handling:**"
                "\n  If no correlations meet filter criteria, returns error: 'There are no correlations in this matrix fitting the {filter} criteria'"
                "\n  → Solution: Try broader filter (e.g., 'significant' instead of 'high' or 'all' to see full matrix)"
            ),
            "enum": ["all", "high", "significant", "low", "negative_only", "positive_only"],
            "default": "all"
        }
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CORRELATION_MATRIX_TOOL = {
    "name": "calculate_portfolio_correlation_matrix",
    "description": CORRELATION_MATRIX_DESCRIPTION,
    "parameters": CORRELATION_MATRIX_PARAMETERS,
    "function": correlation_matrix,
}

if __name__ == "__main__":
    print(correlation_matrix(portfolio_dict={'AAPL': {'allocation': 0.0556, 'position': 'long'}, 'MSFT': {'allocation': 0.0556, 'position': 'long'}, 'AMZN': {'allocation': 0.0556, 'position': 'long'}, 'TSLA': {'allocation': 0.0556, 'position': 'long'}, 'META': {'allocation': 0.0556, 'position': 'long'}, 'SPY': {'allocation': 0.0556, 'position': 'long'}, 'QQQ': {'allocation': 0.0556, 'position': 'long'}, 'IWM': {'allocation': 0.0556, 'position': 'long'}, 'GOOGL': {'allocation': 0.0556, 'position': 'long'}, 'NVDA': {'allocation': 0.0556, 'position': 'long'}, 'AMD': {'allocation': 0.0556, 'position': 'long'}, 'NFLX': {'allocation': 0.0556, 'position': 'long'}, 'DIS': {'allocation': 0.0556, 'position': 'long'}, 'V': {'allocation': 0.0556, 'position': 'long'}, 'JPM': {'allocation': 0.0556, 'position': 'long'}, 'XLF': {'allocation': 0.0556, 'position': 'long'}, 'VTI': {'allocation': 0.0556, 'position': 'long'}, 'EEM': {'allocation': 0.0552, 'position': 'long'}}, filter="all"))