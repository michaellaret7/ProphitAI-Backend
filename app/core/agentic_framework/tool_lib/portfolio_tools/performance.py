import yaml
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
import pandas as pd
from app.core.calculations.core.config import DEFAULT_RF_ANNUAL, DEFAULT_TRADING_DAYS
from app.models.portfolio_models import PortfolioInput
from app.utils.gpt_parser import canonical_portfolio


def calculate_portfolio_performance(portfolio_dict: PortfolioInput | dict, lookback_days=756, use_total_returns=True, rf_annual=0.04, benchmark="SPY") -> str:
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
    try:
        if not portfolio_dict:
            return yaml.dump({"success": True, "data": {}}, default_flow_style=False)

        portfolio_dict = canonical_portfolio(portfolio_dict)

        # Get portfolio returns
        portfolio_returns, weights = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days,
            use_total_returns=use_total_returns,
            dropna=True,
            normalization="gross"
        )

        if portfolio_returns is None or portfolio_returns.empty:
            return yaml.dump({"success": True, "data": {}}, default_flow_style=False)

        # Get benchmark returns
        benchmark_returns = get_benchmark_returns(
            benchmark=benchmark,
            lookback_days=lookback_days,
            use_total_returns=use_total_returns
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
            alpha = PerformanceCalculator.alpha(portfolio_returns, benchmark_returns, risk_free_daily=rf_daily, trading_days=252)
            alpha_jensen = PerformanceCalculator.alpha_jensen(portfolio_returns, benchmark_returns)
            info_ratio = PerformanceCalculator.information_ratio(portfolio_returns, benchmark_returns)
            treynor = PerformanceCalculator.treynor_ratio(portfolio_returns, benchmark_returns, rf_annual=rf_annual, periods_per_year=252)
            tracking_error = PerformanceCalculator.tracking_error(portfolio_returns, benchmark_returns)
            up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(portfolio_returns, benchmark_returns, periods_per_year=None)
            up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(portfolio_returns, benchmark_returns, periods_per_year=252)
        else:
            beta = alpha = alpha_jensen = info_ratio = treynor = tracking_error = float("nan")
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

        # Return all metrics
        return yaml.dump({"success": True, "data": {
            # Core returns
            # "cagr": _rd(cagr),
            "annualized_return": _rd(ann_return),
            "annualized_volatility": _rd(ann_volatility),

            # Risk-adjusted
            "sharpe": _rd(sharpe),
            "sortino": _rd(sortino),
            "calmar_1y": _rd(calmar_1y),

            # Benchmark-relative
            "beta": _rd(beta),
            "alpha": _rd(alpha),
            "alpha_jensen": _rd(alpha_jensen),
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
        }}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


# Tool Schema Constants
CALCULATE_PORTFOLIO_PERFORMANCE_DESCRIPTION = (
    "Calculate portfolio performance metrics. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter. "
    "NEVER call this without portfolio_dict. "
    "The portfolio_dict must contain ALL portfolio holdings with their allocations and positions. "
    "Example: portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, ...}"
)

CALCULATE_PORTFOLIO_PERFORMANCE_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": {
            "type": "object",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "Complete portfolio with ALL holdings. "
                "Keys = ticker symbols (e.g., 'AAPL'). "
                "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
                "You MUST include this parameter with all portfolio tickers. "
                "Uses 3-year lookback (756 days) and SPY benchmark by default."
                "\n\n"
                """Example of CORRECT function call:
                calculate_portfolio_performance(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    }
                )"""
            ),
            "patternProperties": {
                "^[A-Z]{1,5}$": {
                    "type": "object",
                    "properties": {
                        "allocation": {
                            "type": "number",
                            "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "position": {
                            "type": "string",
                            "description": "Must be 'long' or 'short'",
                            "enum": ["long", "short"]
                        }
                    },
                    "required": ["allocation", "position"],
                    "additionalProperties": False
                }
            },
            "minProperties": 1,
            "additionalProperties": False
        }
    },
    "required": ["portfolio_dict"],  # This is critical
    "additionalProperties": False
}

CALCULATE_PORTFOLIO_PERFORMANCE_TOOL = {
    "name": "calculate_portfolio_performance",
    "description": CALCULATE_PORTFOLIO_PERFORMANCE_DESCRIPTION,
    "parameters": CALCULATE_PORTFOLIO_PERFORMANCE_PARAMETERS,
    "function": calculate_portfolio_performance,
}
