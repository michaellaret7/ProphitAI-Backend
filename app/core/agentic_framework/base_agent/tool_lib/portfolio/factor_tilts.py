from app.db.core.prophit_alts_models import FundInitialPosition
from app.db.core.market_data_models import Ticker
from app.db.core.db_config import ProphitAltsSession, MarketSession
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.factor_tilt import portfolio_factor_tilts
from app.models.portfolio_models import PortfolioInput

def factor_tilts_for_portfolio(portfolio_dict: PortfolioInput | dict, factors: str) -> dict:
    """Compute and print factor tilts (value/growth/momentum/quality/volatility)."""
    if not portfolio_dict:
        return {}
    portfolio_dict = canonical_portfolio(portfolio_dict)

    # Convert portfolio dict to signed weights expected by calculations_v2
    # Positive for longs, negative for shorts
    weights = {}
    for t, cfg in portfolio_dict.items():
        try:
            alloc = float(cfg.get("allocation", 0.0) or 0.0)
        except Exception:
            alloc = 0.0
        pos = (cfg.get("position") or "long").lower()
        weights[t] = -alloc if pos == "short" else alloc

    # Helper to round numeric values to 4 decimals in the tilt output
    def _round_tilt_output(res: dict) -> dict:
        if not isinstance(res, dict):
            return res
        out = {}
        for k, v in res.items():
            if k == "per_ticker_exposure" and isinstance(v, dict):
                out[k] = {tk: (round(float(tv), 4) if isinstance(tv, (int, float)) else tv) for tk, tv in v.items()}
            elif isinstance(v, (int, float)):
                out[k] = round(float(v), 4)
            else:
                out[k] = v
        return out

    # Keep only summary fields for "all" output
    def _summary(res: dict) -> dict:
        if not isinstance(res, dict):
            return res
        return {k: res.get(k) for k in ["factor", "net_tilt", "long_tilt", "short_tilt"] if k in res}

    if factors == "all":
        return {
            "value": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "value"))),
            "growth": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "growth"))),
            "momentum": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "momentum"))),
            "quality": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "quality"))),
            "volatility": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "volatility")))
        }

    if factors not in ["value", "growth", "momentum", "quality", "volatility", "all"]:
        raise ValueError(f"Invalid factor: {factors}")

    return _round_tilt_output(portfolio_factor_tilts(weights, factors))
