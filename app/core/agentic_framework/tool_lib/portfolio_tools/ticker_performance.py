import yaml
from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_benchmark_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
import pandas as pd
import numpy as np
from app.models.portfolio_models import PortfolioInput
from app.utils.gpt_parser import canonical_portfolio
from app.utils.decorators.tool_validation import log_simulation_data_range, validate_portfolio_dict, validate_required_args

@validate_required_args('portfolio_dict')
@validate_portfolio_dict()
@log_simulation_data_range()
def calculate_ticker_performances(portfolio_dict: PortfolioInput | dict, lookback_days: int = 504, use_total_returns: bool = True, benchmark: str = "SPY", _simulation_date: Optional[datetime] = None) -> str:
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
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)

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
        # Optional: stable column ordering if data present
        cols = [
            "ticker",
            "sharpe", "sortino", "treynor", "info", "alpha",
            "omega", "sterling", "burke", "martin",
            "up_cap_daily", "down_cap_daily", "up_cap_ann", "down_cap_ann",
            "win_rate", "pf_ret", "pf_eq", "pain", "tail_ratio", "gain_loss",
            "ulcer", "ulcer_252pct",
            "max_drawdown", "ann_total_return", "ann_volatility",
        ]
        if not df.empty:
            existing = [c for c in cols if c in df.columns]
            df = df[existing]

        return yaml.dump({"success": True, "data": df.to_dict('records')}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

# Tool Schema Constants
CALCULATE_TICKER_PERFORMANCES_DESCRIPTION = (
    "Calculate comprehensive performance metrics for each ticker in the portfolio. "
    "Returns a DataFrame with detailed risk-adjusted metrics including Sharpe, Sortino, Treynor, Information Ratio, Alpha, "
    "Omega, Sterling, Burke, Martin ratios, capture ratios, win rates, profit factors, pain index, tail ratio, "
    "gain/loss ratio, ulcer index, max drawdown, annual returns, and volatility. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: calculate_ticker_performances(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}})"
)

CALCULATE_TICKER_PERFORMANCES_PARAMETERS = {
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
                "Uses 2-year lookback (504 days), total returns, and SPY benchmark by default."
                "\n\n"
                """Example of CORRECT function call:
                calculate_ticker_performances(
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
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CALCULATE_TICKER_PERFORMANCES_TOOL = {
    "name": "calculate_ticker_performances",
    "description": CALCULATE_TICKER_PERFORMANCES_DESCRIPTION,
    "parameters": CALCULATE_TICKER_PERFORMANCES_PARAMETERS,
    "function": calculate_ticker_performances,
}