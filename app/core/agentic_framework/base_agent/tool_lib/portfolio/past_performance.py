from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.models.portfolio_models import PortfolioInput
import pandas as pd
from app.core.calculations.core.config import DEFAULT_RF_ANNUAL, DEFAULT_TRADING_DAYS
from app.utils.gpt_parser import canonical_portfolio

def calculate_portfolio_past_performance(
    portfolio_dict: PortfolioInput | dict,
    rf_annual: float = DEFAULT_RF_ANNUAL,
    lookback_years: int = 3,
    benchmark: str = "SPY",
) -> dict:
    """Compute core performance metrics for the portfolio using calculations_v2.

    Returns a dict with metrics rounded to 5 decimals when numeric.
    Uses SPY as the benchmark.
    """
    if not portfolio_dict:
        return "You Must provide a portfolio dictionary to calculate the portfolio past performance"
        
    portfolio_dict = canonical_portfolio(portfolio_dict)
    
    lookback_days = int(DEFAULT_TRADING_DAYS * max(1, lookback_years))
    
    # Use the new utility functions to get portfolio and benchmark returns
    r, weights = get_portfolio_returns(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=True,
        dropna=False,
        renormalize_each_day=True
    )
    
    if r is None or r.empty:
        return {}
    
    # Get benchmark returns using utility function
    rm = get_benchmark_returns(
        benchmark=benchmark,
        lookback_days=lookback_days,
        use_total_returns=True
    )

    # Core metrics (use total-return portfolio series; incorporate RF where supported)
    cagr = PerformanceCalculator.cagr_from_returns(r)
    # Build constant daily RF series aligned to r for accuracy
    rf_daily = (1.0 + float(rf_annual)) ** (1.0 / float(DEFAULT_TRADING_DAYS)) - 1.0
    rf_series = pd.Series(rf_daily, index=r.index)
    sharpe = PerformanceCalculator.sharpe_ratio(r, rf_annual=rf_annual, periods_per_year=DEFAULT_TRADING_DAYS, rf_series=rf_series)
    sortino = PerformanceCalculator.sortino_ratio(r, mar_annual=rf_annual, periods_per_year=DEFAULT_TRADING_DAYS, mar_daily=rf_daily)
    # Calmar (3y and 1y)
    calmar = PerformanceCalculator.calmar_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS, years=3)
    calmar_1y = PerformanceCalculator.calmar_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS, years=1)
    info = PerformanceCalculator.information_ratio(r, rm) if not rm.empty else float("nan")
    alpha = PerformanceCalculator.alpha(r, rm, risk_free_daily=rf_daily, trading_days=DEFAULT_TRADING_DAYS) if not rm.empty else float("nan")
    treynor = PerformanceCalculator.treynor_ratio(r, rm, rf_annual=rf_annual, periods_per_year=DEFAULT_TRADING_DAYS) if not rm.empty else float("nan")
    tracking_error = PerformanceCalculator.tracking_error(r, rm) if not rm.empty else float("nan")
    omega = PerformanceCalculator.omega_ratio_from_annual(r)
    burke = PerformanceCalculator.burke_ratio(r)
    sterling = PerformanceCalculator.sterling_ratio_from_returns(r)
    martin = PerformanceCalculator.martin_ratio(r)
    win_rate = PerformanceCalculator.win_rate(r)
    pf_ret = PerformanceCalculator.profit_factor_from_returns(r)
    tail = PerformanceCalculator.tail_ratio(r)
    ulcer = PerformanceCalculator.ulcer_index(r)
    beta = RiskCalculator.beta(r, rm) if not rm.empty else float("nan")
    # Max drawdown (on portfolio equity)
    equity = (1.0 + r).cumprod()
    dd = equity / equity.cummax() - 1.0
    max_drawdown = float(dd.min()) if not dd.empty else float("nan")

    # Calculate annualized returns using utility functions
    # Get price-only returns for annualized price return
    r_price, _ = get_portfolio_returns(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=True,
        dropna=False,
        renormalize_each_day=True
    )
    
    # Calculate annualized returns
    annual_price_ret = ReturnsCalculator.annualized_return(r_price, DEFAULT_TRADING_DAYS) if r_price is not None and not r_price.empty else float("nan")
    annual_total_ret = ReturnsCalculator.annualized_return(r, DEFAULT_TRADING_DAYS) if r is not None and not r.empty else float("nan")

    # Helper to round floats safely
    def _rd(x):
        try:
            return round(float(x), 5)
        except Exception:
            return x

    return {
        "cagr": _rd(cagr),
        "sharpe": _rd(sharpe),
        "sortino": _rd(sortino),
        "beta": _rd(beta),
        "alpha": _rd(alpha),
        "information_ratio": _rd(info),
        "treynor": _rd(treynor),
        "tracking_error": _rd(tracking_error),
        "omega": _rd(omega),
        "burke": _rd(burke),
        "sterling": _rd(sterling),
        "martin": _rd(martin),
        "max_drawdown": _rd(max_drawdown),
        "win_rate": _rd(win_rate),
        "profit_factor": _rd(pf_ret),
        "tail_ratio": _rd(tail),
        "ulcer_index": _rd(ulcer),
        "annualized_price_return": _rd(annual_price_ret),
        "annualized_total_return": _rd(annual_total_ret),
        "calmar": _rd(calmar),
        "calmar_1y": _rd(calmar_1y),
    }