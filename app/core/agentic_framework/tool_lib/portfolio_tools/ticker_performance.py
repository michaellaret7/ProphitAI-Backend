from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_benchmark_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_MEDIUM
import pandas as pd
import numpy as np
from app.models.portfolio_models import PortfolioInput
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

# Metric group definitions for per-ticker filtering
TICKER_METRIC_GROUPS = {
    "core": ["ann_total_return", "ann_volatility", "max_drawdown"],
    "risk_adjusted": ["sharpe", "sortino", "treynor", "info", "alpha"],
    "advanced": ["omega", "sterling", "burke", "martin"],
    "capture_ratios": ["up_cap_daily", "down_cap_daily", "up_cap_ann", "down_cap_ann"],
    "win_loss": ["win_rate", "pf_ret", "pf_eq", "pain", "tail_ratio", "gain_loss"],
    "risk_metrics": ["ulcer", "ulcer_252pct"],
}

@log_simulation_data_range()
def calculate_ticker_performances(
    portfolio_dict: PortfolioInput | dict, 
    lookback_days: int = DEFAULT_LOOKBACK_MEDIUM, 
    use_total_returns: bool = True, 
    benchmark: str = "SPY", 
    filters: list[str] = ["all"],
    _simulation_date: Optional[datetime] = None
    ) -> str:

    """Return a DataFrame of performance metrics for each ticker in the portfolio.

    Reuses shared utilities and calculators to fetch data and compute metrics.

    Args:
        portfolio_dict: Dict of holdings with position and allocation
        lookback_days: Number of days to look back
        use_total_returns: If True, include dividends; if False, price-only returns
        benchmark: Benchmark ticker symbol used for relative metrics

    Returns:
        pd.DataFrame where each row corresponds to a ticker and columns are metrics.
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.optional_numeric('lookback_days', lookback_days, default=DEFAULT_LOOKBACK_MEDIUM, min_val=1, positive_only=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    lookback_days = v.get('lookback_days')

    try:

        # Fetch inputs via shared utilities
        weights, price_data, dividend_data = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=lookback_days,
            include_dividends=use_total_returns,
            include_benchmark=None,
            _simulation_date=_simulation_date
        )

        # Build per-ticker daily returns
        ticker_returns: dict[str, pd.Series] = {}
        for ticker in weights:
            series = price_data.get(ticker)
            if series is None or series.empty:
                continue
            if use_total_returns:
                divs = dividend_data.get(ticker)
                ticker_returns[ticker] = ReturnsCalculator.total_returns(series, divs)
            else:
                ticker_returns[ticker] = ReturnsCalculator.daily_price_returns(series)

        # Benchmark returns
        benchmark_returns = get_benchmark_returns(
            benchmark=benchmark,
            lookback_days=lookback_days,
            use_total_returns=use_total_returns,
            _simulation_date=_simulation_date
        )

        rows: list[dict] = []
        for ticker, r in ticker_returns.items():
            try:
                # Core risk-adjusted metrics
                sharpe = PerformanceCalculator.sharpe_ratio(r)
                sortino = PerformanceCalculator.sortino_ratio(r)
                treynor = PerformanceCalculator.treynor_ratio(r, benchmark_returns)
                info = PerformanceCalculator.information_ratio(r, benchmark_returns)
                alpha = PerformanceCalculator.alpha_jensen(r, benchmark_returns)

                # Advanced risk-adjusted metrics
                omega = PerformanceCalculator.omega_ratio_from_annual(r)
                sterling = PerformanceCalculator.sterling_ratio_from_returns(r)
                burke = PerformanceCalculator.burke_ratio(r)
                martin = PerformanceCalculator.martin_ratio(r)

                # Capture ratios
                up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(r, benchmark_returns, periods_per_year=None)
                up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(r, benchmark_returns, periods_per_year=252)

                # Win/loss and other diagnostics
                win_rate = PerformanceCalculator.win_rate(r)
                pf_ret = PerformanceCalculator.profit_factor_from_returns(r)
                pf_eq = PerformanceCalculator.profit_factor(r, start_equity=1.0)
                pain = PerformanceCalculator.pain_index(r)
                tail_ratio = PerformanceCalculator.tail_ratio(r, q=5.0)
                gain_loss = PerformanceCalculator.gain_loss_ratio(r, threshold=0.0, method="mean")
                ulcer = PerformanceCalculator.ulcer_index(r, window=None, as_percent=False)
                ulcer_252pct = PerformanceCalculator.ulcer_index(r, window=252, as_percent=True)

                # Additional requested metrics
                equity = (1.0 + r).cumprod()
                max_drawdown = RiskCalculator.max_drawdown(equity)
                ann_total_return = ReturnsCalculator.annualized_return(r, 252)
                ann_volatility = RiskCalculator.annualized_volatility(r, 252)

                row = {
                    "ticker": ticker,
                    "sharpe": sharpe,
                    "sortino": sortino,
                    "treynor": treynor,
                    "info": info,
                    "alpha": alpha,
                    "omega": omega,
                    "sterling": sterling,
                    "burke": burke,
                    "martin": martin,
                    "up_cap_daily": up_cap_daily,
                    "down_cap_daily": down_cap_daily,
                    "up_cap_ann": up_cap_ann,
                    "down_cap_ann": down_cap_ann,
                    "win_rate": win_rate,
                    "pf_ret": pf_ret,
                    "pf_eq": pf_eq,
                    "pain": pain,
                    "tail_ratio": tail_ratio,
                    "gain_loss": gain_loss,
                    "ulcer": ulcer,
                    "ulcer_252pct": ulcer_252pct,
                    "max_drawdown": max_drawdown,
                    "ann_total_return": ann_total_return,
                    "ann_volatility": ann_volatility,
                }

                # Round numeric metrics to 4 decimals
                for k, v in list(row.items()):
                    if k == "ticker":
                        continue
                    if isinstance(v, (float, int, np.floating)) and np.isfinite(v):
                        row[k] = round(float(v), 4)
                rows.append(row)
            except Exception:
                rows.append({"ticker": ticker})

        df = pd.DataFrame(rows)

        # Apply filters
        if "all" in filters or not filters:
            # Return all columns (backward compatible)
            cols = [
                "ticker",
                "sharpe", "sortino", "treynor", "info", "alpha",
                "omega", "sterling", "burke", "martin",
                "up_cap_daily", "down_cap_daily", "up_cap_ann", "down_cap_ann",
                "win_rate", "pf_ret", "pf_eq", "pain", "tail_ratio", "gain_loss",
                "ulcer", "ulcer_252pct",
                "max_drawdown", "ann_total_return", "ann_volatility",
            ]
        else:
            # Build filtered column list based on requested groups
            requested_metrics = set()

            for filter_name in filters:
                if filter_name in TICKER_METRIC_GROUPS:
                    requested_metrics.update(TICKER_METRIC_GROUPS[filter_name])
                else:
                    # Invalid filter name - return error
                    valid_filters = list(TICKER_METRIC_GROUPS.keys()) + ["all"]
                    return error_response(f"Invalid filter '{filter_name}'. Valid filters: {valid_filters}")

            # Always include ticker column, then requested metrics
            cols = ["ticker"] + sorted(requested_metrics)

        # Select only existing columns in the specified order
        if not df.empty:
            existing = [c for c in cols if c in df.columns]
            df = df[existing]

        return success_response(df.to_dict('records'))
    except Exception as e:
        return error_response(e)

# Tool Schema Constants
CALCULATE_TICKER_PERFORMANCES_DESCRIPTION = (
    "Calculate performance metrics for each ticker in the portfolio with optional filtering for token efficiency. "
    "Returns 25 metrics per ticker across 6 groups (core, risk_adjusted, advanced, capture_ratios, win_loss, risk_metrics). "
    "\n\n**TOKEN EFFICIENCY - Use Filters to Reduce Response Size:**"
    "\n  Full response (filters=['all']): ~300 tokens per ticker (25 metrics)"
    "\n  Filtered response (filters=['core', 'risk_adjusted']): ~100 tokens per ticker (8 metrics, 67% reduction)"
    "\n  Minimal response (filters=['core']): ~40 tokens per ticker (3 metrics, 87% reduction)"
    "\n\n**Common Filter Patterns:**"
    "\n  • Quick check: ['core', 'risk_adjusted']"
    "\n  • Compare tickers: ['core', 'risk_adjusted', 'capture_ratios']"
    "\n  • Full analysis: ['all'] (default)"
    "\n\n**Critical Requirements:**"
    "\n  • You MUST include portfolio_dict with ALL holdings"
    "\n  • Use filters to request only needed metrics per ticker"
    "\n  • Default lookback: 2 years (504 days), benchmark: SPY"
    "\n\n**Examples:**"
    "\n  calculate_ticker_performances(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...}, filters=['core', 'risk_adjusted'])"
    "\n  calculate_ticker_performances(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...}, filters=['all'])"
)

CALCULATE_TICKER_PERFORMANCES_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "filters": {
            "type": "array",
            "description": (
                "Filter which metric groups to return per ticker. Reduces token usage by 60-90%. "
                "\n\n**Available Metric Groups:**"
                "\n  • 'core' (3 metrics): ann_total_return, ann_volatility, max_drawdown"
                "\n  • 'risk_adjusted' (5 metrics): sharpe, sortino, treynor, info, alpha"
                "\n  • 'advanced' (4 metrics): omega, sterling, burke, martin"
                "\n  • 'capture_ratios' (4 metrics): up_cap_daily, down_cap_daily, up_cap_ann, down_cap_ann"
                "\n  • 'win_loss' (6 metrics): win_rate, pf_ret, pf_eq, pain, tail_ratio, gain_loss"
                "\n  • 'risk_metrics' (2 metrics): ulcer, ulcer_252pct"
                "\n  • 'all': Return all 25 metrics per ticker (default)"
                "\n\n**Examples:**"
                "\n  filters=['core', 'risk_adjusted']  # Compare tickers on key metrics"
                "\n  filters=['all']  # Full analysis"
            ),
            "items": {
                "type": "string",
                "enum": ["all", "core", "risk_adjusted", "advanced", "capture_ratios", "win_loss", "risk_metrics"]
            },
            "default": ["all"]
        }
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CALCULATE_TICKER_PERFORMANCES_TOOL = {
    "name": "calculate_ticker_performances",
    "description": CALCULATE_TICKER_PERFORMANCES_DESCRIPTION,
    "parameters": CALCULATE_TICKER_PERFORMANCES_PARAMETERS,
    "function": calculate_ticker_performances,
}

if __name__ == "__main__":
    print(calculate_ticker_performances(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, 'MSFT': {'allocation': 0.125, 'position': 'long'}, 'AMZN': {'allocation': 0.125, 'position': 'long'}, 'TSLA': {'allocation': 0.125, 'position': 'long'}, 'META': {'allocation': 0.125, 'position': 'long'}, 'SPY': {'allocation': 0.125, 'position': 'long'}, 'QQQ': {'allocation': 0.125, 'position': 'long'}, 'IWM': {'allocation': 0.125, 'position': 'long'}}, filters=["core"]))