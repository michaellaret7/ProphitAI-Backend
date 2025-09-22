import yaml
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
import pandas as pd
import numpy as np
from app.models.portfolio_models import PortfolioInput
from app.utils.gpt_parser import canonical_portfolio
from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker

def calculate_group_performances(portfolio_dict: PortfolioInput | dict, lookback_days: int = 756, use_total_returns: bool = True, group_by: str = None) -> str:
    """Generic grouping performance calculator.

    Returns a DataFrame with columns: [group_label, ann_total_return, ann_volatility]
    where group_label column name equals group_by.
    """
    if not portfolio_dict:
        return yaml.dump([], default_flow_style=False)
    
    portfolio_dict = canonical_portfolio(portfolio_dict)
    
    # 1) Data and weights
    weights, price_data, dividend_data = prepare_portfolio_data(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        include_dividends=use_total_returns,
        include_benchmark=None,
    )

    tickers = list(weights.keys())
    if not tickers:
        return yaml.dump([], default_flow_style=False)

    # 2) Per-ticker return series
    per_ticker_returns: dict[str, pd.Series] = {}
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

    # 3) Map tickers to group labels
    field = group_by
    session = MarketSession()
    try:
        rows = (
            session.query(Ticker)
            .filter(Ticker.ticker.in_([t.upper() for t in tickers]))
            .all()
        )
        ticker_to_group: dict[str, str | None] = {}
        for r in rows:
            ticker_to_group[r.ticker] = getattr(r, field, None)
    finally:
        session.close()

    # 4) Build group-level returns using gross-exposure normalization (weights normalized by abs-sum)
    rows: list[dict] = []
    # Group tickers by label
    group_to_tickers: dict[str | None, list[str]] = {}
    for t, lbl in ticker_to_group.items():
        group_to_tickers.setdefault(lbl if lbl is not None else "Unknown", []).append(t)

    for lbl, group_tickers in group_to_tickers.items():
        # Align returns and weights
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
            # Fallback: equal-weight
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
        # Stable ordering by label
        out = out[[group_by, "ann_total_return", "ann_volatility"]]
    return yaml.dump(out.to_dict('records'), default_flow_style=False)

# Tool Schema Constants
CALCULATE_GROUP_PERFORMANCES_DESCRIPTION = (
    "Calculate performance metrics grouped by industry or sub-industry. "
    "Returns a DataFrame with columns: [group_label, ann_total_return, ann_volatility] "
    "where group_label column name equals group_by parameter. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'group_by'. "
    "Example: calculate_group_performances(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}}, group_by='industry')"
)

CALCULATE_GROUP_PERFORMANCES_PARAMETERS = {
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
                "Uses 3-year lookback (756 days) and total returns by default."
                "\n\n"
                """Example of CORRECT function call:
                calculate_group_performances(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    },
                    group_by="industry"
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
        },
        "group_by": {
            "type": "string",
            "description": "Field to group by for performance analysis. Must be 'industry' or 'sub_industry'.",
            "enum": ["industry", "sub_industry"]
        },
    },
    "required": ["portfolio_dict", "group_by"],
    "additionalProperties": False
}

CALCULATE_GROUP_PERFORMANCES_TOOL = {
    "name": "calculate_group_performances",
    "description": CALCULATE_GROUP_PERFORMANCES_DESCRIPTION,
    "parameters": CALCULATE_GROUP_PERFORMANCES_PARAMETERS,
    "function": calculate_group_performances,
}