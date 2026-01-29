from datetime import datetime
from typing import Optional
import pandas as pd
from app.core.calculations.portfolio.utils import get_portfolio_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_3Y
from app.models.portfolio_models import PortfolioInput
import numpy as np
from app.utils.tool_validator import ToolValidator
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response

@log_simulation_data_range()
def drawdown_profile(
    portfolio_dict: PortfolioInput | dict = None,
    *,
    _simulation_date: Optional[datetime] = None
) -> str:
    """
    Analyze portfolio drawdown characteristics.

    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    - _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
    - max_dd: Maximum drawdown (worst peak-to-trough decline)
    - avg_dd: Average drawdown across all episodes
    - ulcer: Ulcer Index (measure of drawdown severity and duration)
    - episodes: List of drawdown episodes with start/end dates and recovery times
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')

    try:

        # Get portfolio returns using the utility for last 3 years (industry standard for risk analysis)
        portfolio_returns, weights = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=DEFAULT_LOOKBACK_3Y,  # 3 years for comprehensive drawdown analysis
            use_total_returns=False,  # Use price returns for drawdown analysis
            dropna=True,
            _simulation_date=_simulation_date
        )

        if portfolio_returns is None or portfolio_returns.empty:
            return error_response("No price data available")

        # Log actual data range
        if isinstance(portfolio_returns, pd.Series) and len(portfolio_returns) > 0:
            if hasattr(portfolio_returns, 'index') and isinstance(portfolio_returns.index, pd.DatetimeIndex):
                start_date = portfolio_returns.index.min().date()
                end_date = portfolio_returns.index.max().date()
                count = len(portfolio_returns)
                print(f"  📅 ACTUAL DATA USED:")
                if _simulation_date:
                    cutoff_ok = portfolio_returns.index.max() <= _simulation_date
                    cutoff_status = "✅" if cutoff_ok else "⚠️ EXCEEDS CUTOFF"
                    print(f"    • drawdown_data: {start_date} → {end_date} ({count} points) {cutoff_status}")
                else:
                    print(f"    • drawdown_data: {start_date} → {end_date} ({count} points)")

        # Calculate cumulative portfolio value (NAV)
        portfolio_nav = (1 + portfolio_returns).cumprod()

        # Calculate running maximum (peak values)
        running_max = portfolio_nav.expanding().max()

        # Calculate drawdown series
        drawdown = (portfolio_nav - running_max) / running_max

        # Calculate key metrics using v2 for max drawdown and ulcer index
        max_drawdown = float(RiskCalculator.max_drawdown(portfolio_nav))

        # Find drawdown episodes
        episodes = []
        in_drawdown = False
        episode_start = None
        episode_peak = None

        for i, (date, dd_value) in enumerate(drawdown.items()):
            if not in_drawdown and dd_value < -0.001:  # Start of drawdown (>0.1% decline)
                in_drawdown = True
                episode_start = date
                episode_peak = running_max.iloc[i]

            elif in_drawdown and dd_value >= -0.001:  # End of drawdown
                if episode_start is not None:
                    episode_end = date
                    episode_trough = portfolio_nav.loc[episode_start:episode_end].min()
                    episode_max_dd = (episode_trough - episode_peak) / episode_peak

                    # Calculate recovery time (days to get back to peak)
                    recovery_date = None
                    future_nav = portfolio_nav[episode_end:]
                    recovery_nav = future_nav[future_nav >= episode_peak]
                    if not recovery_nav.empty:
                        recovery_date = recovery_nav.index[0]
                        recovery_days = (recovery_date - episode_start).days
                    else:
                        recovery_days = None  # Not yet recovered

                    episodes.append({
                        'start_date': episode_start.strftime('%Y-%m-%d'),
                        'end_date': episode_end.strftime('%Y-%m-%d'),
                        'max_drawdown': round(float(episode_max_dd), 4),
                        'duration_days': (episode_end - episode_start).days,
                        'recovery_days': recovery_days,
                        'recovered': recovery_days is not None
                    })

                in_drawdown = False
                episode_start = None

        # Calculate average drawdown
        if episodes:
            avg_drawdown = float(np.mean([ep['max_drawdown'] for ep in episodes]))
        else:
            avg_drawdown = 0.0

        # Calculate Ulcer Index (RMS of drawdowns) via v2
        ulcer_index = float(RiskCalculator.ulcer_index(portfolio_nav))

        result = {
            'analysis_period_days': len(portfolio_nav),
            'max_dd': round(max_drawdown, 4),
            'avg_dd': round(avg_drawdown, 4),
            'ulcer': round(ulcer_index, 4),
            'num_episodes': len(episodes),
            'episodes': episodes,
            'current_drawdown': round(float(drawdown.iloc[-1]), 4)
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Failed to calculate drawdown_profile: {str(e)}")


# Tool Schema Constants
DRAWDOWN_PROFILE_DESCRIPTION = (
    "Analyze portfolio drawdown characteristics including maximum drawdown, average drawdown, ulcer index, and detailed drawdown episodes. "
    "Returns comprehensive drawdown analysis with start/end dates, recovery times, and episode statistics. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: drawdown_profile(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}})"
)

DRAWDOWN_PROFILE_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

DRAWDOWN_PROFILE_TOOL = {
    "name": "portfolio_drawdown_profile",
    "description": DRAWDOWN_PROFILE_DESCRIPTION,
    "parameters": DRAWDOWN_PROFILE_PARAMETERS,
    "function": drawdown_profile,
}
