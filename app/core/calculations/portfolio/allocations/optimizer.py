import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.utils.gpt_parser import canonical_portfolio
from app.utils.time_utils import get_current_utc_time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*riskfolio.*")

# Riskfolio (install if missing: pip install riskfolio-lib)
try:
    import riskfolio as rp
except Exception as exc:  # pragma: no cover
    print("Missing dependency: riskfolio-lib. Install with: pip install riskfolio-lib")
    raise

from app.repositories.price_data import (
    fetch_bulk_price_data_for_tickers,
    get_dividends_series,
)
from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator
from app.core.calculations.core.helpers import build_returns_df_for_dates
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.models.portfolio_models import PortfolioInput

def _build_returns_matrix(
    tickers: List[str],
    start_date: datetime,
    end_date: datetime,
    *,
    use_total_returns: bool = False,
) -> pd.DataFrame:
    """Build a DataFrame of aligned daily returns for tickers.

    - If use_total_returns=True, include cash dividends in daily return calc
    - Index: dates, Columns: tickers
    """
    if not tickers:
        return pd.DataFrame()

    # Build returns with shared helper, dropping rows with any NaNs for stability
    returns_df = build_returns_df_for_dates(
        tickers,
        start_date,
        end_date,
        include_dividends=bool(use_total_returns),
        drop_rows='any',
    )
    
    if returns_df.empty:
        return pd.DataFrame()

    # Ensure all data is numeric and convert to float64
    returns_df = returns_df.astype(float)
    
    # Reset index to ensure clean integer index for Riskfolio
    returns_df = returns_df.reset_index(drop=True)
    
    # Store original column names for later reference
    original_columns = returns_df.columns.tolist()
    
    # Convert to pure numpy array
    returns_array = np.array(returns_df.values, dtype=np.float64)
    
    # Create a completely new DataFrame with clean structure
    # Use copy() to ensure no references to original data
    clean_df = pd.DataFrame(
        data=returns_array.copy(),
        columns=list(range(returns_array.shape[1])),
        dtype=np.float64
    )
    
    # Store the ticker mapping as an attribute
    clean_df.attrs['tickers'] = original_columns
    
    return clean_df


def optimize_portfolio_weights(
    portfolio_input: Dict[str, Any] | Any,
    *,
    lookback_days: int = 252,
    use_total_returns: bool = False,
    target_vol_cap: float = 0.15,
    net_budget: float = 0.1,
    max_short_budget: float = 0.75,
    per_asset_long_cap: float = 0.15,
    per_asset_short_cap: float = 0.08,
    gross_exposure_cap: float = 2.0,
    gross_exposure_min: float = 1.5,
) -> pd.Series:
    """Run Riskfolio MinRisk optimization on our data for given tickers.

    Returns a pd.Series of optimized weights (index=tickers).
    - If gross_exposure_cap is provided, we cap gross exposure G by tightening the
      short budget S using the identity G = B + 2S, where B is net budget.
    - If gross_exposure_min is provided, enforce sum(|w|) ≥ gross_exposure_min via
      a simple inequality constraint passed to the optimizer.
    """
    # Normalize input using canonical_portfolio (tickers, allocation, position)
    portfolio_canonical = canonical_portfolio(portfolio_input)
    tickers = list(portfolio_canonical.keys())
    
    # Track which tickers should be long vs short based on input
    long_tickers = [t for t, data in portfolio_canonical.items() if data.get("position") == "long"]
    short_tickers = [t for t, data in portfolio_canonical.items() if data.get("position") == "short"]

    end = get_current_utc_time()  # Use UTC time
    # Convert lookback_days (trading days) to calendar days
    calendar_days = int(lookback_days * 365 / 252)
    start = end - timedelta(days=calendar_days)

    returns_df = _build_returns_matrix(
        tickers, start, end, use_total_returns=use_total_returns
    )

    if returns_df.empty or returns_df.shape[1] < 2:
        raise ValueError("Not enough return history to optimize (need ≥2 assets with data)")

    # Get ticker names from the DataFrame attributes
    ticker_names = returns_df.attrs.get('tickers', list(range(returns_df.shape[1])))

    # Use already-cleaned returns DataFrame
    clean_returns = returns_df
    
    # Set up Riskfolio portfolio (canonical API)
    port = rp.Portfolio(returns=clean_returns)

    # Allow shorting and per-asset caps
    port.sht = True
    port.uppersht = float(per_asset_short_cap)
    port.upperlng = float(per_asset_long_cap)
    
    # Set up position direction constraints based on input
    # The columns in clean_returns are integers 0,1,2... but map to ticker_names
    n_assets = len(ticker_names)
    lower_bounds = []
    upper_bounds = []
    
    for i in range(n_assets):
        ticker = ticker_names[i]
        if ticker in long_tickers:
            # Long positions: must be >= 0, capped at per_asset_long_cap
            lower_bounds.append(0.0)
            upper_bounds.append(float(per_asset_long_cap))
        elif ticker in short_tickers:
            # Short positions: must be <= 0, with magnitude capped at per_asset_short_cap
            lower_bounds.append(-float(per_asset_short_cap))
            upper_bounds.append(0.0)
        else:
            # If not specified, allow both directions
            lower_bounds.append(-float(per_asset_short_cap))
            upper_bounds.append(float(per_asset_long_cap))
    
    # Apply bounds to portfolio - these should be numpy arrays
    port.lowerbound = np.array(lower_bounds)
    port.upperbound = np.array(upper_bounds)

    # Exposure budgets (net and short)
    port.budget = float(net_budget)
    port.budgetsht = float(max_short_budget)

    # Optional gross exposure cap via short budget derivation: G = B + 2S => S <= (G - B)/2
    if gross_exposure_cap is not None:
        G = float(gross_exposure_cap)
        B = float(port.budget)
        s_cap = max(0.0, (G - B) / 2.0)
        port.budgetsht = float(min(port.budgetsht, s_cap))

    # Target volatility cap
    port.upperdev = float(target_vol_cap)

    # Pre-compute stats (avoids dtype pitfalls)
    port.assets_stats(method_mu="hist", method_cov="hist")

    # Optimize: minimize variance given constraints
    weights = port.optimization(
        model="Classic",
        rm="MV",
        obj="MinRisk",
        rf=0,
        l=0,
        hist=True,
    )

    # Post-adjust weights to meet a minimum gross exposure if feasible
    if gross_exposure_min is not None:
        try:
            # Ensure weights as 1D Series with numeric index for math
            if isinstance(weights, pd.DataFrame) and weights.shape[1] == 1:
                weights = weights.iloc[:, 0]
            if not isinstance(weights, pd.Series):
                weights = pd.Series(weights, index=clean_returns.columns)

            w_vals = weights.values.astype(float)
            long_mask = w_vals > 0
            short_mask = w_vals < 0
            total_long = float(w_vals[long_mask].sum())
            total_short = float(-w_vals[short_mask].sum())
            net_exposure_now = total_long - total_short
            gross_exposure_now = total_long + total_short

            G_target = float(gross_exposure_min)
            # Do not exceed cap if both are provided
            if gross_exposure_cap is not None:
                G_target = float(min(G_target, float(gross_exposure_cap)))

            # Only scale if we currently fall short and have both long and short sides
            if gross_exposure_now < G_target and total_long > 0 and total_short > 0:
                new_total_long = (net_exposure_now + G_target) / 2.0
                new_total_short = (G_target - net_exposure_now) / 2.0
                # Feasibility check
                if new_total_long >= 0 and new_total_short >= 0:
                    scale_long = new_total_long / total_long if total_long > 0 else 1.0
                    scale_short = new_total_short / total_short if total_short > 0 else 1.0
                    w_vals[long_mask] *= scale_long
                    w_vals[short_mask] *= scale_short
                    weights = pd.Series(w_vals, index=weights.index)
        except Exception:
            pass

    # Ensure weights is a Series indexed by tickers
    if isinstance(weights, pd.DataFrame) and weights.shape[1] == 1:
        weights = weights.iloc[:, 0]
    if not isinstance(weights, pd.Series):
        weights = pd.Series(weights, index=clean_returns.columns)
    
    # Map back to ticker names
    weights.index = ticker_names
    
    # Enforce position directions and caps post-optimization
    # This is a failsafe in case Riskfolio doesn't respect the bounds
    for ticker in weights.index:
        if ticker in long_tickers:
            # Force to be non-negative, cap at per_asset_long_cap
            weights[ticker] = max(0.0, min(weights[ticker], float(per_asset_long_cap)))
        elif ticker in short_tickers:
            # Force to be non-positive, cap magnitude at per_asset_short_cap
            weights[ticker] = min(0.0, max(weights[ticker], -float(per_asset_short_cap)))
    
    # Final clipping for any remaining positions
    cap_long = float(per_asset_long_cap)
    cap_short = float(per_asset_short_cap)
    weights = weights.clip(lower=-cap_short, upper=cap_long)

    return weights.sort_values(ascending=False)

def print_portfolio_metrics(
    portfolio_input: PortfolioInput | dict,
    *,
    lookback_days: int = 252,
    use_total_returns: bool = True,
    renormalize_each_day: bool = True,
    normalization: str = "gross",
) -> None:
    """
    Print annualized return, annualized volatility, Sharpe, Alpha (vs SPY),
    net exposure, and gross exposure for a single portfolio input.
    """
    portfolio_dict = canonical_portfolio(portfolio_input)
    r, w = get_portfolio_returns(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
        dropna=True,
        renormalize_each_day=renormalize_each_day,
        normalization=normalization,
    )
    if r is None or r.empty:
        print("No data to compute metrics.")
        return
    ann_ret = float(ReturnsCalculator.annualized_return(r))
    ann_vol = float(r.std() * np.sqrt(252))
    bench = get_benchmark_returns(lookback_days=lookback_days, use_total_returns=use_total_returns)
    sharpe = float(PerformanceCalculator.sharpe_ratio(r))
    alpha = float(PerformanceCalculator.alpha_jensen(r, bench))
    net_exposure = float(sum(w.values()))
    gross_exposure = float(sum(abs(x) for x in w.values()))
    print(f"Annualized Return: {ann_ret}")
    print(f"Annualized Volatility: {ann_vol}")
    print(f"Sharpe: {sharpe}")
    print(f"Alpha (Jensen): {alpha}")
    print(f"Net Exposure: {net_exposure}")
    print(f"Gross Exposure: {gross_exposure}")
    
def plot_returns(
    portfolio_input: PortfolioInput | dict,
    *,
    lookback_days: int = 252,
    use_total_returns: bool = True,
    renormalize_each_day: bool = True,
    normalization: str = "gross",
) -> None:
    """Plot cumulative returns for the portfolio."""
    portfolio_dict = canonical_portfolio(portfolio_input)
    r, _ = get_portfolio_returns(
        portfolio=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=use_total_returns,
        dropna=True,
        renormalize_each_day=renormalize_each_day,
        normalization=normalization,
    )
    if r is None or r.empty:
        print("No data to plot.")
        return
    
    # Calculate cumulative returns
    cumulative = (1 + r).cumprod()
    
    # Simple plot
    plt.figure(figsize=(12, 6))
    plt.plot(cumulative.index, cumulative.values, linewidth=2)
    plt.title('Portfolio Cumulative Returns', fontsize=14)
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Minimal smoke test: raise if function errors
    portfolio = {
    "ACI": {"position": "long", "allocation": 0.02046},
    "ADM": {"position": "long", "allocation": 0.05139},
    "BJ": {"position": "long", "allocation": 0.02779},
    "CCEP": {"position": "long", "allocation": 0.06676},
    "CL": {"position": "long", "allocation": 0.03158},
    "GIS": {"position": "long", "allocation": 0.04037},
    "INGR": {"position": "long", "allocation": 0.095},
    "IPAR": {"position": "long", "allocation": 0.05},
    "KDP": {"position": "long", "allocation": 0.0696},
    "KMB": {"position": "long", "allocation": 0.10359},
    "KO": {"position": "long", "allocation": 0.08445},
    "KVUE": {"position": "long", "allocation": 0.05708},
    "LW": {"position": "long", "allocation": 0.04633},
    "MO": {"position": "long", "allocation": 0.10028},
    "PPC": {"position": "long", "allocation": 0.07188},
    "CELH": {"position": "short", "allocation": 0.05},
    "CLX": {"position": "short", "allocation": 0.08},
    "COTY": {"position": "short", "allocation": 0.04},
    "EL": {"position": "short", "allocation": 0.048},
    "ELF": {"position": "short", "allocation": 0.045},
    "FRPT": {"position": "short", "allocation": 0.044},
    "HSY": {"position": "short", "allocation": 0.08},
    "PFGC": {"position": "short", "allocation": 0.045},
    "SFM": {"position": "short", "allocation": 0.069},
    "STZ": {"position": "short", "allocation": 0.08},
    "USFD": {"position": "short", "allocation": 0.045},
    "UTZ": {"position": "short", "allocation": 0.08},
    "VITL": {"position": "short", "allocation": 0.065},
    "WDFC": {"position": "short", "allocation": 0.08},
    "AAL": {"position": "short", "allocation": 0.06},

    }

    # print_portfolio_metrics(portfolio, lookback_days=252)

    w = optimize_portfolio_weights(portfolio, lookback_days=252*3)
    w = canonical_portfolio(w)
    print_portfolio_metrics(w, lookback_days=252*3)
    print(json.dumps(w, indent=4))
    
    # Plot the returns
    plot_returns(w, lookback_days=252*3)
    plot_returns(portfolio, lookback_days=252*3)


    


