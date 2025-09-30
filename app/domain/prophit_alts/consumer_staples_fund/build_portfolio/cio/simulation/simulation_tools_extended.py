"""Extended simulation tools for group and ticker performances.

This module contains additional simulation-aware wrappers for portfolio analysis tools.
Split from simulation_tools.py to keep file sizes manageable.
"""

import yaml
import pandas as pd
import numpy as np
from datetime import datetime

from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.config import SIMULATION_CUTOFF_DATE
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.simulation_tools import (
    prepare_portfolio_data_simulation,
    get_benchmark_returns_simulation,
)
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.utils.gpt_parser import canonical_portfolio
from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker


# ============================================================================
# GROUP PERFORMANCES TOOL (SIMULATION WRAPPER)
# ============================================================================

def calculate_group_performances_simulation(
    portfolio_dict: dict,
    lookback_days: int = 756,
    use_total_returns: bool = True,
    group_by: str = None
) -> str:
    """Simulation-aware version of calculate_group_performances."""
    if not portfolio_dict:
        return yaml.dump([], default_flow_style=False)

    portfolio_dict = canonical_portfolio(portfolio_dict)

    # Use simulation version
    weights, price_data, dividend_data = prepare_portfolio_data_simulation(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        include_dividends=use_total_returns,
        include_benchmark=None,
    )

    tickers = list(weights.keys())
    if not tickers:
        return yaml.dump([], default_flow_style=False)

    # Per-ticker return series
    per_ticker_returns = {}
    for t in tickers:
        s = price_data.get(t)
        if s is None or s.empty:
            continue
        if use_total_returns:
            divs = dividend_data.get(t)
            per_ticker_returns[t] = ReturnsCalculator.total_returns(s, divs)
        else:
            per_ticker_returns[t] = ReturnsCalculator.daily_price_returns(s)

    if not per_ticker_returns:
        return yaml.dump([], default_flow_style=False)

    # Map tickers to group labels
    field = group_by
    session = MarketSession()
    try:
        rows = (
            session.query(Ticker)
            .filter(Ticker.ticker.in_([t.upper() for t in tickers]))
            .all()
        )
        ticker_to_group = {}
        for r in rows:
            ticker_to_group[r.ticker] = getattr(r, field, None)
    finally:
        session.close()

    # Build group-level returns
    rows = []
    group_to_tickers = {}
    for t, lbl in ticker_to_group.items():
        group_to_tickers.setdefault(lbl if lbl is not None else "Unknown", []).append(t)

    for lbl, group_tickers in group_to_tickers.items():
        r_map = {t: per_ticker_returns[t] for t in group_tickers if t in per_ticker_returns}
        if not r_map:
            continue
        df = pd.concat(r_map, axis=1).dropna(how="any")
        if df.empty:
            continue
        w = pd.Series({t: weights.get(t, 0.0) for t in df.columns}, index=df.columns).astype(float)
        denom = float(np.abs(w).sum())
        if denom > 0:
            w_norm = w / denom
        else:
            w_norm = pd.Series(1.0 / len(df.columns), index=df.columns)

        grp_returns = (df * w_norm).sum(axis=1)
        ann_ret = ReturnsCalculator.annualized_return(grp_returns, 252)
        ann_vol = RiskCalculator.annualized_volatility(grp_returns, 252)

        row = {
            group_by: lbl,
            "ann_total_return": round(ann_ret, 4) if np.isfinite(ann_ret) else ann_ret,
            "ann_volatility": round(ann_vol, 4) if np.isfinite(ann_vol) else ann_vol,
        }
        rows.append(row)

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out[[group_by, "ann_total_return", "ann_volatility"]]
    return yaml.dump(out.to_dict('records'), default_flow_style=False)


CALCULATE_GROUP_PERFORMANCES_SIMULATION_TOOL = {
    "name": "calculate_group_performances",
    "description": (
        "Calculate performance metrics grouped by industry or sub-industry (SIMULATION MODE - data up to Sept 30, 2024). "
        "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'group_by'. "
        "Example: calculate_group_performances(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...}, group_by='industry')"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_dict": {
                "type": "object",
                "description": "Complete portfolio with ALL holdings.",
                "patternProperties": {
                    "^[A-Z]{1,5}$": {
                        "type": "object",
                        "properties": {
                            "allocation": {"type": "number", "minimum": 0, "maximum": 1},
                            "position": {"type": "string", "enum": ["long", "short"]}
                        },
                        "required": ["allocation", "position"],
                        "additionalProperties": False
                    }
                },
                "minProperties": 1,
                "additionalProperties": False
            },
            "group_by": {
                "type": "string",
                "description": "Field to group by ('industry' or 'sub_industry').",
                "enum": ["industry", "sub_industry"]
            },
        },
        "required": ["portfolio_dict", "group_by"],
        "additionalProperties": False
    },
    "function": calculate_group_performances_simulation,
}


# ============================================================================
# TICKER PERFORMANCES TOOL (SIMULATION WRAPPER)
# ============================================================================

def calculate_ticker_performances_simulation(
    portfolio_dict: dict,
    lookback_days: int = 504,
    use_total_returns: bool = True,
    benchmark: str = "SPY"
) -> str:
    """Simulation-aware version of calculate_ticker_performances."""
    portfolio_dict = canonical_portfolio(portfolio_dict)

    # Use simulation version
    weights, price_data, dividend_data = prepare_portfolio_data_simulation(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        include_dividends=use_total_returns,
        include_benchmark=None,
    )

    # Build per-ticker daily returns
    ticker_returns = {}
    for ticker in weights:
        series = price_data.get(ticker)
        if series is None or series.empty:
            continue
        if use_total_returns:
            divs = dividend_data.get(ticker)
            ticker_returns[ticker] = ReturnsCalculator.total_returns(series, divs)
        else:
            ticker_returns[ticker] = ReturnsCalculator.daily_price_returns(series)

    # Benchmark returns using simulation version
    benchmark_returns = get_benchmark_returns_simulation(
        benchmark=benchmark,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
    )

    rows = []
    for ticker, r in ticker_returns.items():
        try:
            # Core risk-adjusted metrics
            sharpe = PerformanceCalculator.sharpe_ratio(r)
            sortino = PerformanceCalculator.sortino_ratio(r)
            treynor = PerformanceCalculator.treynor_ratio(r, benchmark_returns)
            info = PerformanceCalculator.information_ratio(r, benchmark_returns)
            alpha = PerformanceCalculator.alpha_jensen(r, benchmark_returns)

            # Advanced metrics
            omega = PerformanceCalculator.omega_ratio_from_annual(r)
            sterling = PerformanceCalculator.sterling_ratio_from_returns(r)
            burke = PerformanceCalculator.burke_ratio(r)
            martin = PerformanceCalculator.martin_ratio(r)

            # Capture ratios
            up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(r, benchmark_returns, periods_per_year=None)
            up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(r, benchmark_returns, periods_per_year=252)

            # Win/loss metrics
            win_rate = PerformanceCalculator.win_rate(r)
            pf_ret = PerformanceCalculator.profit_factor_from_returns(r)
            pf_eq = PerformanceCalculator.profit_factor(r, start_equity=1.0)
            pain = PerformanceCalculator.pain_index(r)
            tail_ratio = PerformanceCalculator.tail_ratio(r, q=5.0)
            gain_loss = PerformanceCalculator.gain_loss_ratio(r, threshold=0.0, method="mean")
            ulcer = PerformanceCalculator.ulcer_index(r, window=None, as_percent=False)
            ulcer_252pct = PerformanceCalculator.ulcer_index(r, window=252, as_percent=True)

            # Additional metrics
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

            # Round numeric metrics
            for k, v in list(row.items()):
                if k == "ticker":
                    continue
                if isinstance(v, (float, int, np.floating)) and np.isfinite(v):
                    row[k] = round(float(v), 4)
            rows.append(row)
        except Exception:
            rows.append({"ticker": ticker})

    df = pd.DataFrame(rows)
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

    return yaml.dump(df.to_dict('records'), default_flow_style=False)


CALCULATE_TICKER_PERFORMANCES_SIMULATION_TOOL = {
    "name": "calculate_ticker_performances",
    "description": (
        "Calculate comprehensive performance metrics for each ticker (SIMULATION MODE - data up to Sept 30, 2024). "
        "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
        "Example: calculate_ticker_performances(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...})"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_dict": {
                "type": "object",
                "description": "Complete portfolio with ALL holdings. Uses 2-year lookback, total returns, and SPY benchmark by default.",
                "patternProperties": {
                    "^[A-Z]{1,5}$": {
                        "type": "object",
                        "properties": {
                            "allocation": {"type": "number", "minimum": 0, "maximum": 1},
                            "position": {"type": "string", "enum": ["long", "short"]}
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
    },
    "function": calculate_ticker_performances_simulation,
}


# ============================================================================
# TICKER FACTORS TOOL (SIMULATION WRAPPER)
# ============================================================================

def calculate_ticker_factors_simulation(ticker: str, factor: str) -> str:
    """Simulation-aware version of calculate_ticker_factors."""
    from app.core.calculations.factors.growth import GrowthFactors
    from app.core.calculations.factors.value import ValueFactors
    from app.core.calculations.factors.quality import QualityFactors
    from app.core.calculations.factors.momentum import MomentumFactors
    from app.core.calculations.factors.volatility import VolatilityFactors
    from app.core.calculations.core import DataService
    from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.simulation_tools import filter_series_by_date

    # Growth, Value, and Quality factors use fundamental data (no date issues)
    if factor in ["growth", "value", "quality"]:
        if factor == "growth":
            result = GrowthFactors(ticker).calc_all()
        elif factor == "value":
            result = ValueFactors(ticker).calc_all()
        else:  # quality
            result = QualityFactors(ticker).calc_all()
        return yaml.dump(result, default_flow_style=False)

    # Momentum and Volatility factors need price series (USE SIMULATION CUTOFF)
    elif factor in ["momentum", "volatility"]:
        ds = DataService()

        # Use simulation cutoff instead of datetime.now()
        end_date = SIMULATION_CUTOFF_DATE
        start_date = end_date - pd.Timedelta(days=252)  # ~1 year of data

        # Get price data for ticker
        price_data = ds.get_price_data(ticker, start_date, end_date)
        if price_data is None or price_data.frame.empty:
            return yaml.dump({"error": f"No price data available for {ticker}"}, default_flow_style=False)

        # Filter by simulation cutoff
        price_series = filter_series_by_date(price_data.frame['close'], SIMULATION_CUTOFF_DATE)

        # Get SPY data (also filtered)
        spy_data = ds.get_price_data("SPY", start_date, end_date)
        if spy_data and not spy_data.frame.empty:
            spy_prices = filter_series_by_date(spy_data.frame['close'], SIMULATION_CUTOFF_DATE)
        else:
            spy_prices = None

        if factor == "momentum":
            # Get volume data (filtered)
            volume_series = None
            if 'volume' in price_data.frame.columns:
                volume_series = filter_series_by_date(price_data.frame['volume'], SIMULATION_CUTOFF_DATE)

            # Get dividends (filtered)
            try:
                divs = ds.get_dividends(ticker, start_date, end_date).series
                divs = filter_series_by_date(divs, SIMULATION_CUTOFF_DATE)
                divs = divs.reindex(price_series.index).fillna(0.0)
            except Exception:
                divs = None

            result = MomentumFactors(
                price_series=price_series,
                volume_series=volume_series,
                market_price_series=spy_prices,
                dividends_series=divs
            ).calc_all()
        else:  # volatility
            result = VolatilityFactors(price_series, spy_price_series=spy_prices).calc_all()

        return yaml.dump(result, default_flow_style=False)

    else:
        return yaml.dump({"error": f"Unknown factor: {factor}"}, default_flow_style=False)


CALCULATE_TICKER_FACTORS_SIMULATION_TOOL = {
    "name": "calculate_ticker_factors",
    "description": (
        "Calculate all factor metrics for a given ticker and factor type (SIMULATION MODE - data up to Sept 30, 2024). "
        "Can calculate growth, value, momentum, quality, or volatility factors.\n\n"
        "Example: calculate_ticker_factors(ticker='KO', factor='growth')"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The ticker symbol to calculate factors for (e.g., 'AAPL', 'MSFT', 'KO').",
            },
            "factor": {
                "type": "string",
                "description": "The factor type to calculate. Options: 'growth', 'value', 'momentum', 'quality', 'volatility'.",
                "enum": ["growth", "value", "momentum", "quality", "volatility"]
            },
        },
        "required": ["ticker", "factor"],
    },
    "function": calculate_ticker_factors_simulation,
}