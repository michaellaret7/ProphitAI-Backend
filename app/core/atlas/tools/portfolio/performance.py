from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
import pandas as pd
from app.core.calculations.core.config import DEFAULT_RF_ANNUAL, DEFAULT_TRADING_DAYS, DEFAULT_LOOKBACK_3Y
from app.models.portfolio_models import PortfolioInput
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response

# Metric group definitions for filtering
METRIC_GROUPS = {
    "core": ["cagr", "annualized_return", "annualized_volatility"],
    "risk_adjusted": ["sharpe", "sortino", "calmar_1y"],
    "benchmark_relative": ["beta", "alpha", "information_ratio", "treynor", "tracking_error"],
    "capture_ratios": ["up_capture_daily", "down_capture_daily", "up_capture_annual", "down_capture_annual"],
    "advanced": ["omega", "burke", "sterling", "martin"],
    "win_loss": ["win_rate", "profit_factor"],
    "drawdown": ["max_drawdown", "pain_index", "tail_ratio", "ulcer_index"],
}


@log_simulation_data_range()
def calculate_portfolio_performance(
    portfolio_dict: PortfolioInput | dict,
    lookback_days=DEFAULT_LOOKBACK_3Y,
    use_total_returns=True,
    rf_annual=0.04,
    benchmark="SPY",
    filters: list[str] = ["all"],
    _simulation_date: Optional[datetime] = None
    ) -> str:

    """Unified portfolio performance calculation combining all metrics.

    Args:
        portfolio: Dict of holdings with position and allocation
        lookback_days: Number of days to look back
        use_total_returns: If True, include dividends; if False, price-only returns
        rf_annual: Annual risk-free rate for Sharpe/Sortino calculations
        benchmark: Benchmark ticker symbol (default: SPY)

    Returns:
        dict: All performance metrics rounded to 4 decimals
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.optional_numeric('lookback_days', lookback_days, default=DEFAULT_LOOKBACK_3Y, min_val=1, positive_only=True)
    v.optional_numeric('rf_annual', rf_annual, default=0.04, min_val=0, max_val=1)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    lookback_days = v.get('lookback_days')
    rf_annual = v.get('rf_annual')

    try:

        # Get portfolio returns
        portfolio_returns, weights = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days,
            use_total_returns=use_total_returns,
            dropna=False,
            normalization="gross",
            _simulation_date=_simulation_date
        )


        if portfolio_returns is None or portfolio_returns.empty:
            return success_response({})

        # Get benchmark returns
        benchmark_returns = get_benchmark_returns(
            benchmark=benchmark,
            lookback_days=lookback_days,
            use_total_returns=use_total_returns,
            _simulation_date=_simulation_date
        )

        # Calculate RF series for metrics that need it
        rf_daily = (1.0 + float(rf_annual)) ** (1.0 / 252.0) - 1.0
        rf_series = pd.Series(rf_daily, index=portfolio_returns.index)

        # Core returns metrics
        cagr = PerformanceCalculator.cagr_from_returns(portfolio_returns)
        ann_return = ReturnsCalculator.annualized_return(portfolio_returns, 252)
        ann_volatility = RiskCalculator.annualized_volatility(portfolio_returns, 252)

        # Risk-adjusted metrics with RF
        sharpe = PerformanceCalculator.sharpe_ratio(portfolio_returns, rf_annual=rf_annual, periods_per_year=252, rf_series=rf_series)
        sortino = PerformanceCalculator.sortino_ratio(portfolio_returns, mar_annual=rf_annual, periods_per_year=252, mar_daily=rf_daily)
        calmar = PerformanceCalculator.calmar_from_returns(portfolio_returns, periods_per_year=252, years=3)
        calmar_1y = PerformanceCalculator.calmar_from_returns(portfolio_returns, periods_per_year=252, years=1)

        # Benchmark-relative metrics
        if not benchmark_returns.empty:
            beta = RiskCalculator.beta(portfolio_returns, benchmark_returns)
            alpha = PerformanceCalculator.alpha(portfolio_returns, benchmark_returns)
            info_ratio = PerformanceCalculator.information_ratio(portfolio_returns, benchmark_returns)
            treynor = PerformanceCalculator.treynor_ratio(portfolio_returns, benchmark_returns, rf_annual=rf_annual, periods_per_year=252)
            tracking_error = PerformanceCalculator.tracking_error(portfolio_returns, benchmark_returns)
            up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(portfolio_returns, benchmark_returns, periods_per_year=None)
            up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(portfolio_returns, benchmark_returns, periods_per_year=252)
        else:
            beta = alpha = info_ratio = treynor = tracking_error = float("nan")
            up_cap_daily = down_cap_daily = up_cap_ann = down_cap_ann = float("nan")

        # Advanced risk-adjusted metrics
        omega = PerformanceCalculator.omega_ratio_from_annual(portfolio_returns)
        burke = PerformanceCalculator.burke_ratio(portfolio_returns)
        sterling = PerformanceCalculator.sterling_ratio_from_returns(portfolio_returns)
        martin = PerformanceCalculator.martin_ratio(portfolio_returns)

        # Win/loss metrics
        win_rate = PerformanceCalculator.win_rate(portfolio_returns)
        profit_factor = PerformanceCalculator.profit_factor_from_returns(portfolio_returns)

        # Drawdown and risk metrics
        equity = (1.0 + portfolio_returns).cumprod()
        dd = equity / equity.cummax() - 1.0
        max_drawdown = float(dd.min()) if not dd.empty else float("nan")

        # Pain and tail metrics
        pain_index = PerformanceCalculator.pain_index(portfolio_returns)
        tail_ratio = PerformanceCalculator.tail_ratio(portfolio_returns)
        ulcer_index = PerformanceCalculator.ulcer_index(portfolio_returns)

        # Helper to round floats safely
        def _rd(x):
            try:
                return round(float(x), 4)
            except Exception:
                return x

        # Build complete metrics dictionary
        all_metrics = {
            # Core returns
            "cagr": _rd(cagr),
            "annualized_return": _rd(ann_return),
            "annualized_volatility": _rd(ann_volatility),

            # Risk-adjusted
            "sharpe": _rd(sharpe),
            "sortino": _rd(sortino),
            "calmar_1y": _rd(calmar_1y),

            # Benchmark-relative
            "beta": _rd(beta),
            "alpha": _rd(alpha),
            "information_ratio": _rd(info_ratio),
            "treynor": _rd(treynor),
            "tracking_error": _rd(tracking_error),

            # Capture ratios
            "up_capture_daily": _rd(up_cap_daily),
            "down_capture_daily": _rd(down_cap_daily),
            "up_capture_annual": _rd(up_cap_ann),
            "down_capture_annual": _rd(down_cap_ann),

            # Advanced metrics
            "omega": _rd(omega),
            "burke": _rd(burke),
            "sterling": _rd(sterling),
            "martin": _rd(martin),

            # Win/loss
            "win_rate": _rd(win_rate),
            "profit_factor": _rd(profit_factor),

            # Drawdown and risk
            "max_drawdown": _rd(max_drawdown),
            "pain_index": _rd(pain_index),
            "tail_ratio": _rd(tail_ratio),
            "ulcer_index": _rd(ulcer_index),
        }

        # Apply filters
        if "all" in filters or not filters:
            # Return everything (backward compatible)
            filtered_metrics = all_metrics
        else:
            # Build filtered dict based on requested groups
            filtered_metrics = {}
            requested_metrics = set()

            # Collect all metrics from requested groups
            for filter_name in filters:
                if filter_name in METRIC_GROUPS:
                    requested_metrics.update(METRIC_GROUPS[filter_name])
                else:
                    # Invalid filter name - return error
                    valid_filters = list(METRIC_GROUPS.keys()) + ["all"]
                    return error_response(f"Invalid filter '{filter_name}'. Valid filters: {valid_filters}")

            # Extract only requested metrics
            for metric_name in requested_metrics:
                if metric_name in all_metrics:
                    filtered_metrics[metric_name] = all_metrics[metric_name]

        return success_response(filtered_metrics)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
CALCULATE_PORTFOLIO_PERFORMANCE_DESCRIPTION = (
    "Calculate portfolio performance metrics with optional filtering for token efficiency. "
    "Returns 26 total metrics across 7 groups (core, risk_adjusted, benchmark_relative, capture_ratios, advanced, win_loss, drawdown). "
    "\n\n**TOKEN EFFICIENCY - Use Filters to Reduce Response Size:**"
    "\n  Full response (filters=['all']): ~270 tokens with 25 metrics"
    "\n  Filtered response (filters=['core', 'risk_adjusted']): ~120 tokens with 6 metrics (55% reduction)"
    "\n  Minimal response (filters=['core']): ~80 tokens with 3 metrics (70% reduction)"
    "\n\n**Common Filter Patterns:**"
    "\n  • Quick check: ['core', 'risk_adjusted']"
    "\n  • Risk analysis: ['core', 'risk_adjusted', 'drawdown']"
    "\n  • Benchmark comparison: ['core', 'benchmark_relative', 'capture_ratios']"
    "\n  • Full analysis: ['all'] (default)"
    "\n\n**Critical Requirements:**"
    "\n  • You MUST include portfolio_dict with ALL holdings (allocation + position)"
    "\n  • Use filters to request only needed metrics (saves tokens)"
    "\n  • Default lookback: 3 years (756 days), benchmark: SPY"
    "\n\n**Examples:**"
    "\n  calculate_portfolio_performance(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, ...}, filters=['core', 'risk_adjusted'])"
    "\n  calculate_portfolio_performance(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, ...}, filters=['benchmark_relative'])"
    "\n  calculate_portfolio_performance(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, ...}, filters=['all'])"
)

CALCULATE_PORTFOLIO_PERFORMANCE_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "filters": {
            "type": "array",
            "description": (
                "Filter which metric groups to return. Reduces token usage by 50-90% for focused analysis. "
                "Provide a list of group names or ['all'] for everything (default). "
                "\n\n**Available Metric Groups:**"
                "\n  • 'core' (3 metrics): cagr, annualized_return, annualized_volatility"
                "\n  • 'risk_adjusted' (3 metrics): sharpe, sortino, calmar_1y"
                "\n  • 'benchmark_relative' (5 metrics): beta, alpha, information_ratio, treynor, tracking_error"
                "\n  • 'capture_ratios' (4 metrics): up_capture_daily, down_capture_daily, up_capture_annual, down_capture_annual"
                "\n  • 'advanced' (4 metrics): omega, burke, sterling, martin"
                "\n  • 'win_loss' (2 metrics): win_rate, profit_factor"
                "\n  • 'drawdown' (4 metrics): max_drawdown, pain_index, tail_ratio, ulcer_index"
                "\n  • 'all': Return all 25 metrics (default behavior)"
                "\n\n**Common Use Cases:**"
                "\n  Quick Check → ['core', 'risk_adjusted'] (6 metrics, 77% reduction)"
                "\n  Risk Analysis → ['core', 'risk_adjusted', 'drawdown'] (10 metrics, 62% reduction)"
                "\n  vs Benchmark → ['core', 'benchmark_relative'] (8 metrics, 68% reduction)"
                "\n  Full Report → ['all'] (25 metrics, for comprehensive analysis)"
                "\n\n**Token Efficiency:**"
                "\n  • ['core'] only: ~80 tokens (70% reduction vs full)"
                "\n  • ['core', 'risk_adjusted']: ~120 tokens (55% reduction)"
                "\n  • ['all']: ~270 tokens (complete metrics)"
                "\n\n**Examples:**"
                "\n  filters=['core', 'risk_adjusted']  # Quick performance overview"
                "\n  filters=['benchmark_relative', 'capture_ratios']  # Compare to SPY"
                "\n  filters=['all']  # Everything (default)"
            ),
            "items": {
                "type": "string",
                "enum": ["all", "core", "risk_adjusted", "benchmark_relative", "capture_ratios", "advanced", "win_loss", "drawdown"]
            },
            "default": ["all"]
        }
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CALCULATE_PORTFOLIO_PERFORMANCE_TOOL = {
    "name": "calculate_portfolio_performance",
    "description": CALCULATE_PORTFOLIO_PERFORMANCE_DESCRIPTION,
    "parameters": CALCULATE_PORTFOLIO_PERFORMANCE_PARAMETERS,
    "function": calculate_portfolio_performance,
}
