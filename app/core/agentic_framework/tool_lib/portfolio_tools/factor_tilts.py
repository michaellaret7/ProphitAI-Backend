from app.db.core.models.prophit_alts_models import FundInitialPosition
from app.db.core.models.market_data_models import Ticker
from app.db.core.db_config import ProphitAltsSession, MarketSession
from app.core.calculations.portfolio.factor_tilt import portfolio_factor_tilts
from app.models.portfolio_models import PortfolioInput
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

@log_simulation_data_range()
def factor_tilts_for_portfolio(portfolio_dict: PortfolioInput | dict, factors: str, **kwargs) -> str:
    """Compute and print factor tilts (value/growth/momentum/quality/volatility)."""
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_enum('factors', factors, ['all', 'value', 'growth', 'momentum', 'quality', 'volatility'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    factors = v.get('factors')

    try:

        # Extract simulation date if present (for backtesting/simulation)
        end_date = kwargs.get('_simulation_date', None)

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
            result = {
                "value": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "value", end=end_date))),
                "growth": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "growth", end=end_date))),
                "momentum": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "momentum", end=end_date))),
                "quality": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "quality", end=end_date))),
                "volatility": _summary(_round_tilt_output(portfolio_factor_tilts(weights, "volatility", end=end_date)))
            }
            return success_response(result)

        if factors not in ["value", "growth", "momentum", "quality", "volatility", "all"]:
            return error_response(f"Invalid factor: {factors}")

        data = _round_tilt_output(portfolio_factor_tilts(weights, factors, end=end_date))
        return success_response(data)
    except Exception as e:
        return error_response(e)

# Tool Schema Constants
FACTOR_TILTS_FOR_PORTFOLIO_DESCRIPTION = (
    "Compute style tilts ('value','growth','momentum','quality','volatility' or 'all'). "
    "CRITICAL: include portfolio_dict and specify 'factors'. Returns net_tilt, long_tilt, short_tilt (and per_ticker_exposure for single-factor requests). "
    "Example: factor_tilts_for_portfolio(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}}, factors='all')"
)

FACTOR_TILTS_FOR_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "factors": {
            "type": "string",
            "description": (
                "Factor to compute. Use 'all' for a summary across all factors; otherwise choose one of: "
                "'value', 'growth', 'momentum', 'quality', 'volatility'."
            ),
            "enum": ["all", "value", "growth", "momentum", "quality", "volatility"],
        },
    },
    "required": ["portfolio_dict", "factors"],
    "additionalProperties": False
}

FACTOR_TILTS_FOR_PORTFOLIO_TOOL = {
    "name": "calculate_portfolio_factor_tilts",
    "description": FACTOR_TILTS_FOR_PORTFOLIO_DESCRIPTION,
    "parameters": FACTOR_TILTS_FOR_PORTFOLIO_PARAMETERS,
    "function": factor_tilts_for_portfolio,
}