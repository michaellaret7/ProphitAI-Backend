"""
Monte Carlo Portfolio Simulation — GPU-Accelerated via PyTorch CUDA
===================================================================
Uses REAL historical price data from ProphitAI's database to compute
returns, volatilities, and correlation matrices.

Usage:
  python t.py
"""

import sys
import os
import time
import numpy as np
import torch
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago


# ══════════════════════════════════════════════════════════════════════
# --> Helper funcs
# ══════════════════════════════════════════════════════════════════════

def select_device() -> tuple[torch.device, str | None, bool]:
    """Detect GPU and return (device, gpu_name, gpu_available)."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        name = torch.cuda.get_device_name(0)
        print(f"CUDA detected - running on {name}")
        return device, name, True
    print("CUDA not available - running on CPU")
    return torch.device("cpu"), None, False


def fetch_historical_stats(
    tickers: list[str],
    weights: list[float],
    lookback_days: int = 756,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Fetch real OHLCV data and compute annualized returns, vols, and correlation.

    Args:
        tickers: List of ticker symbols.
        weights: Portfolio weights (decimal).
        lookback_days: Calendar days of history (~3 years default).

    Returns:
        (valid_tickers, weights, annual_returns, annual_vols, correlation_matrix).
    """
    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(lookback_days).strftime("%Y-%m-%d")

    print(f"\nFetching {len(tickers)} tickers from {start_date} to {end_date}...")
    ohlcv_data = fetch_bulk_ohlcv_data_for_tickers(
        tickers=tickers,
        start_date_str=start_date,
        end_date_str=end_date,
        frequency="daily",
    )

    # Reason: build adj_close DataFrame from the per-ticker OHLCV dict
    min_obs = 126  # ~6 months minimum
    adj_close_series: dict[str, pd.Series] = {}
    for ticker in tickers:
        if ticker not in ohlcv_data:
            print(f"  {ticker}: no data returned, skipping")
            continue
        df = ohlcv_data[ticker]
        if "adj_close" not in df.columns:
            print(f"  {ticker}: no adj_close column, skipping")
            continue
        series = df["adj_close"].dropna()
        if len(series) < min_obs:
            print(f"  {ticker}: only {len(series)} observations (need {min_obs}), skipping")
            continue
        adj_close_series[ticker] = series

    valid_tickers = [t for t in tickers if t in adj_close_series]
    prices_df = pd.DataFrame(adj_close_series).dropna()
    daily_returns = prices_df.pct_change().dropna()

    print(f"  {len(prices_df)} trading days of data loaded")
    print(f"  Date range: {prices_df.index[0].date()} to {prices_df.index[-1].date()}")

    # Annualize
    annual_returns = daily_returns.mean().values * 252
    annual_vols = daily_returns.std().values * np.sqrt(252)
    corr_matrix = daily_returns.corr().values

    # Reason: reindex weights to match valid_tickers and renormalize if any were dropped
    weight_map = dict(zip(tickers, weights))
    valid_weights = np.array([weight_map[t] for t in valid_tickers])
    valid_weights = valid_weights / valid_weights.sum()

    return valid_tickers, valid_weights, annual_returns, annual_vols, corr_matrix


# ══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

NUM_SIMULATIONS = 2_500_000
TRADING_DAYS = 252
INITIAL_PORTFOLIO_VALUE = 1_000_000
CONFIDENCE_LEVEL = 0.99

# Portfolio definition (weights must sum to 1.0)
# Portfolio definition (weights must sum to 1.0)
TICKERS = [
    "AMD", "SNOW", "CRWD", "DDOG", "NET", 
    "MDB", "ZS", "OKTA", "TEAM", "NOW", 
    "WDAY", "VEEV", "ADBE", "CRM", "INTU", 
    "SQ", "SHOP", "SPOT", "SPY", "ABNB", 
    "DASH", "RBLX", "COIN", "HOOD", "SOFI"
]
WEIGHTS = [
    0.06, 0.018, 0.05, 0.04, 0.005, 
    0.08, 0.04, 0.06, 0.015, 0.005, 
    0.04, 0.08, 0.06, 0.005, 0.015, 
    0.08, 0.04, 0.06, 0.015, 0.005, 
    0.08, 0.04, 0.06, 0.015, 0.005
]


# ══════════════════════════════════════════════════════════════════════
#  CORE SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════

def _estimate_batch_size(n_assets: int, gpu_available: bool) -> int:
    """Estimate max simulations per batch that fit in GPU VRAM (or RAM)."""
    if gpu_available:
        free_bytes = torch.cuda.mem_get_info()[0]
    else:
        free_bytes = 8 * 1024 ** 3  # Reason: assume 8GB available on CPU

    # Reason: each simulation needs ~(TRADING_DAYS * n_assets * 4 bytes) * 3 tensors
    # (uncorrelated + correlated + daily_asset_returns), plus output tensors
    bytes_per_sim = TRADING_DAYS * n_assets * 4 * 4  # 4 float32 tensors
    # Reason: use 70% of free memory to leave headroom
    max_sims = int(free_bytes * 0.70 / bytes_per_sim)
    return max(10_000, max_sims)


def run_monte_carlo(
    tickers: list[str],
    weights: np.ndarray,
    annual_returns: np.ndarray,
    annual_vols: np.ndarray,
    corr_matrix: np.ndarray,
    device: torch.device,
    gpu_available: bool,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Run the full Monte Carlo simulation on GPU/CPU via PyTorch, batched to fit in VRAM."""

    n_assets = len(tickers)

    # Convert annual stats to daily
    daily_returns = annual_returns / TRADING_DAYS
    daily_vols = annual_vols / np.sqrt(TRADING_DAYS)

    # Build covariance matrix from correlation + volatilities
    vol_diag = np.diag(daily_vols)
    cov_matrix = vol_diag @ corr_matrix @ vol_diag

    # Cholesky decomposition for correlated random returns
    cholesky = np.linalg.cholesky(cov_matrix)

    # Move small constant data to device
    weights_t = torch.tensor(weights, dtype=torch.float32, device=device)
    daily_returns_t = torch.tensor(daily_returns, dtype=torch.float32, device=device)
    cholesky_t = torch.tensor(cholesky, dtype=torch.float32, device=device)

    batch_size = _estimate_batch_size(n_assets, gpu_available)
    n_batches = (NUM_SIMULATIONS + batch_size - 1) // batch_size

    print(f"\nRunning {NUM_SIMULATIONS:,} simulations x {TRADING_DAYS} days x {n_assets} assets")
    if n_batches > 1:
        print(f"  Batching into {n_batches} chunks of ~{batch_size:,} sims (VRAM limit)")

    if gpu_available:
        torch.cuda.synchronize()
    start = time.perf_counter()

    all_paths = []
    all_daily_rets = []
    sims_remaining = NUM_SIMULATIONS

    for batch_idx in range(n_batches):
        batch_n = min(batch_size, sims_remaining)
        sims_remaining -= batch_n

        # Generate random draws for this batch
        uncorrelated = torch.randn(
            TRADING_DAYS, batch_n, n_assets,
            dtype=torch.float32, device=device,
        )

        # Apply Cholesky to correlate the random draws
        correlated_returns = uncorrelated @ cholesky_t.T

        # Add drift (expected daily return)
        daily_asset_returns = daily_returns_t + correlated_returns

        # Portfolio returns per day (weighted sum across assets)
        portfolio_daily_returns = daily_asset_returns @ weights_t

        # Compound returns to get price paths
        cumulative_returns = torch.cumprod(1.0 + portfolio_daily_returns, dim=0)
        portfolio_paths = INITIAL_PORTFOLIO_VALUE * cumulative_returns

        # Move batch results to CPU immediately to free VRAM
        all_paths.append(portfolio_paths.cpu().numpy())
        all_daily_rets.append(portfolio_daily_returns.cpu().numpy())

        # Reason: free GPU memory between batches
        del uncorrelated, correlated_returns, daily_asset_returns
        del portfolio_daily_returns, cumulative_returns, portfolio_paths
        if gpu_available:
            torch.cuda.empty_cache()

        if n_batches > 1:
            print(f"  Batch {batch_idx + 1}/{n_batches} done")

    if gpu_available:
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    # Concatenate all batches
    portfolio_paths_cpu = np.concatenate(all_paths, axis=1)
    portfolio_daily_returns_cpu = np.concatenate(all_daily_rets, axis=1)

    print(f"Completed in {elapsed:.3f} seconds")
    if gpu_available:
        samples_per_sec = (NUM_SIMULATIONS * TRADING_DAYS * n_assets) / elapsed
        print(f"~{samples_per_sec / 1e6:.0f}M random samples/sec on GPU")

    return portfolio_paths_cpu, portfolio_daily_returns_cpu, elapsed


# ══════════════════════════════════════════════════════════════════════
#  RISK METRICS
# ══════════════════════════════════════════════════════════════════════

def calculate_risk_metrics(
    paths: np.ndarray,
    daily_returns: np.ndarray,
) -> dict:
    """Calculate key portfolio risk metrics from simulation results."""

    final_values = paths[-1, :]
    total_returns = (final_values - INITIAL_PORTFOLIO_VALUE) / INITIAL_PORTFOLIO_VALUE

    # Value at Risk (VaR)
    var_percentile = (1 - CONFIDENCE_LEVEL) * 100
    var_return = np.percentile(total_returns, var_percentile)
    var_dollar = INITIAL_PORTFOLIO_VALUE * abs(var_return)

    # Conditional VaR (CVaR) - average loss beyond VaR
    tail_returns = total_returns[total_returns <= var_return]
    cvar_return = tail_returns.mean()
    cvar_dollar = INITIAL_PORTFOLIO_VALUE * abs(cvar_return)

    mean_return = total_returns.mean()
    median_return = float(np.median(total_returns))
    std_return = total_returns.std()
    best_case = total_returns.max()
    worst_case = total_returns.min()

    # Sharpe ratio (annualized, 0% risk-free rate)
    daily_mean = daily_returns.mean()
    daily_std = daily_returns.std()
    sharpe = (daily_mean / daily_std) * np.sqrt(252) if daily_std > 0 else 0.0

    prob_loss = (total_returns < 0).mean() * 100

    return {
        "mean_return": mean_return,
        "median_return": median_return,
        "std_return": std_return,
        "best_case": best_case,
        "worst_case": worst_case,
        "var_return": var_return,
        "var_dollar": var_dollar,
        "cvar_return": cvar_return,
        "cvar_dollar": cvar_dollar,
        "sharpe": sharpe,
        "prob_loss": prob_loss,
        "final_values": final_values,
        "total_returns": total_returns,
    }


# ══════════════════════════════════════════════════════════════════════
#  VISUALIZATION
# ══════════════════════════════════════════════════════════════════════

def _style_axes(fig: plt.Figure, gs: GridSpec, colors: dict) -> None:
    """Apply dark theme styling to all subplot axes."""
    for ax_pos in [gs[0, 0], gs[0, 1], gs[1, 0], gs[1, 1]]:
        ax = fig.add_subplot(ax_pos)
        ax.set_facecolor(colors['panel'])
        ax.tick_params(colors=colors['text'])
        ax.spines['bottom'].set_color(colors['grid'])
        ax.spines['left'].set_color(colors['grid'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.xaxis.label.set_color(colors['text'])
        ax.yaxis.label.set_color(colors['text'])
        ax.title.set_color(colors['text'])


def plot_results(
    paths: np.ndarray,
    metrics: dict,
    tickers: list[str],
    weights: np.ndarray,
    annual_returns: np.ndarray,
    annual_vols: np.ndarray,
    elapsed: float,
    gpu_available: bool,
) -> None:
    """Generate a 4-panel dashboard of simulation results."""

    fig = plt.figure(figsize=(16, 12), facecolor='#1a1a2e')
    fig.suptitle(
        f"Monte Carlo Portfolio Simulation - {NUM_SIMULATIONS:,} Paths x {TRADING_DAYS} Days",
        fontsize=16, fontweight='bold', color='white', y=0.98,
    )
    gs = GridSpec(2, 2, hspace=0.35, wspace=0.3)

    colors = {
        'bg': '#1a1a2e', 'panel': '#16213e', 'grid': '#2a2a4a',
        'text': '#e0e0e0', 'accent': '#00d4aa', 'warn': '#ff6b6b',
        'paths': '#4a90d9', 'median': '#00d4aa',
    }
    _style_axes(fig, gs, colors)

    dollar_fmt = FuncFormatter(lambda x, _: f'${x:,.0f}')

    # ── Panel 1: Simulation paths ─────────────────────────────────────
    ax1 = fig.axes[0]
    n_show = min(500, NUM_SIMULATIONS)
    ax1.plot(paths[:, :n_show], alpha=0.03, color=colors['paths'], linewidth=0.5)

    percentiles = np.percentile(paths, [5, 25, 50, 75, 95], axis=1)
    days = np.arange(TRADING_DAYS)
    ax1.fill_between(days, percentiles[0], percentiles[4], alpha=0.15, color=colors['accent'])
    ax1.fill_between(days, percentiles[1], percentiles[3], alpha=0.25, color=colors['accent'])
    ax1.plot(days, percentiles[2], color=colors['median'], linewidth=2, label='Median')
    ax1.axhline(y=INITIAL_PORTFOLIO_VALUE, color=colors['warn'], linestyle='--',
                alpha=0.5, label='Starting Value')
    ax1.set_title('Portfolio Value Paths (500 shown)', fontsize=12)
    ax1.set_xlabel('Trading Days')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(facecolor=colors['panel'], edgecolor=colors['grid'],
               labelcolor=colors['text'], fontsize=9)
    ax1.yaxis.set_major_formatter(dollar_fmt)

    # ── Panel 2: Final value distribution ─────────────────────────────
    ax2 = fig.axes[1]
    ax2.hist(metrics['final_values'], bins=200, color=colors['paths'],
             alpha=0.7, edgecolor='none', density=True)

    var_value = INITIAL_PORTFOLIO_VALUE * (1 + metrics['var_return'])
    cvar_value = INITIAL_PORTFOLIO_VALUE * (1 + metrics['cvar_return'])
    median_value = float(np.median(metrics['final_values']))
    conf_pct = int(CONFIDENCE_LEVEL * 100)

    ax2.axvline(x=var_value, color=colors['warn'], linewidth=2,
                linestyle='--', label=f'{conf_pct}% VaR: ${var_value:,.0f}')
    ax2.axvline(x=cvar_value, color='#ff4444', linewidth=2,
                linestyle=':', label=f'{conf_pct}% CVaR: ${cvar_value:,.0f}')
    ax2.axvline(x=median_value, color=colors['accent'],
                linewidth=2, label=f'Median: ${median_value:,.0f}')
    ax2.set_title('Distribution of Final Portfolio Values', fontsize=12)
    ax2.set_xlabel('Portfolio Value ($)')
    ax2.set_ylabel('Density')
    ax2.legend(facecolor=colors['panel'], edgecolor=colors['grid'],
               labelcolor=colors['text'], fontsize=9)
    ax2.xaxis.set_major_formatter(dollar_fmt)

    # ── Panel 3: Risk metrics summary ─────────────────────────────────
    ax3 = fig.axes[2]
    ax3.axis('off')

    mean_final = INITIAL_PORTFOLIO_VALUE * (1 + metrics['mean_return'])
    median_final = INITIAL_PORTFOLIO_VALUE * (1 + metrics['median_return'])
    best_final = INITIAL_PORTFOLIO_VALUE * (1 + metrics['best_case'])
    worst_final = INITIAL_PORTFOLIO_VALUE * (1 + metrics['worst_case'])

    summary_text = (
        f"{'─' * 48}\n"
        f"  PORTFOLIO RISK METRICS (Real Historical Data)\n"
        f"{'─' * 48}\n\n"
        f"  Initial Value:     ${INITIAL_PORTFOLIO_VALUE:>12,.0f}\n"
        f"  Mean Final Value:  ${mean_final:>12,.0f}\n"
        f"  Median Final Value:${median_final:>12,.0f}\n\n"
        f"  Expected Return:    {metrics['mean_return']:>11.2%}\n"
        f"  Volatility:         {metrics['std_return']:>11.2%}\n"
        f"  Sharpe Ratio:       {metrics['sharpe']:>11.2f}\n\n"
        f"  Best Case:          {metrics['best_case']:>11.2%}  "
        f"(${best_final:>10,.0f})\n"
        f"  Worst Case:         {metrics['worst_case']:>11.2%}  "
        f"(${worst_final:>10,.0f})\n\n"
        f"  {conf_pct}% VaR:           ${metrics['var_dollar']:>12,.0f}  ({metrics['var_return']:.2%})\n"
        f"  {conf_pct}% CVaR:          ${metrics['cvar_dollar']:>12,.0f}  ({metrics['cvar_return']:.2%})\n\n"
        f"  Probability of Loss: {metrics['prob_loss']:>9.1f}%\n\n"
        f"{'─' * 48}\n"
        f"  Compute time: {elapsed:.3f}s  |  "
        f"{'GPU' if gpu_available else 'CPU'}\n"
        f"{'─' * 48}"
    )
    ax3.text(0.05, 0.95, summary_text, transform=ax3.transAxes,
             fontsize=10, fontfamily='monospace', color=colors['text'],
             verticalalignment='top')

    # ── Panel 4: Portfolio composition with real stats ────────────────
    ax4 = fig.axes[3]
    pie_colors = ['#4a90d9', '#00d4aa', '#ff6b6b', '#ffd93d', '#6c5ce7',
                  '#a29bfe', '#fd79a8', '#00b894', '#e17055', '#0984e3']
    labels = [
        f"{t}\n({w:.0%}, ret:{r:+.0%}, vol:{v:.0%})"
        for t, w, r, v in zip(tickers, weights, annual_returns, annual_vols)
    ]
    _, _, autotexts = ax4.pie(
        weights, labels=labels, colors=pie_colors[:len(tickers)],
        autopct='%1.0f%%', startangle=90,
        textprops={'color': colors['text'], 'fontsize': 9},
    )
    for autotext in autotexts:
        autotext.set_color('#1a1a2e')
        autotext.set_fontweight('bold')
    ax4.set_title('Portfolio Allocation (Real Stats)', fontsize=12, color=colors['text'])

    plt.savefig('monte_carlo_results.png', dpi=150, bbox_inches='tight',
                facecolor=colors['bg'])
    print("\nChart saved to: monte_carlo_results.png")
    plt.show()


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    device, gpu_name, gpu_available = select_device()

    print("=" * 60)
    print("  MONTE CARLO PORTFOLIO SIMULATION (Real Data)")
    print(f"  {'GPU-Accelerated (PyTorch CUDA)' if gpu_available else 'CPU Mode (PyTorch)'}")
    if gpu_name:
        print(f"  Device: {gpu_name}")
    print("=" * 60)

    # Fetch real historical stats from DB
    valid_tickers, valid_weights, annual_returns, annual_vols, corr_matrix = (
        fetch_historical_stats(TICKERS, WEIGHTS)
    )

    # Print portfolio with real stats
    print("\nPortfolio (real historical stats):")
    for t, w, r, v in zip(valid_tickers, valid_weights, annual_returns, annual_vols):
        print(f"   {t:6s}  {w:5.0%}  (ann. return: {r:+.1%}, ann. vol: {v:.1%})")

    print(f"\nCorrelation matrix:")
    corr_df = pd.DataFrame(corr_matrix, index=valid_tickers, columns=valid_tickers)
    print(corr_df.round(2).to_string())

    # Run simulation
    paths, daily_rets, elapsed = run_monte_carlo(
        valid_tickers, valid_weights, annual_returns, annual_vols,
        corr_matrix, device, gpu_available,
    )

    # Calculate risk metrics
    metrics = calculate_risk_metrics(paths, daily_rets)

    # Print summary
    print(f"\nResults Summary:")
    print(f"   Expected return:   {metrics['mean_return']:+.2%}")
    print(f"   Portfolio vol:     {metrics['std_return']:.2%}")
    print(f"   Sharpe ratio:      {metrics['sharpe']:.2f}")
    print(f"   95% VaR:           ${metrics['var_dollar']:,.0f} ({metrics['var_return']:.2%})")
    print(f"   95% CVaR:          ${metrics['cvar_dollar']:,.0f} ({metrics['cvar_return']:.2%})")
    print(f"   P(loss):           {metrics['prob_loss']:.1f}%")

    # Plot
    plot_results(
        paths, metrics, valid_tickers, valid_weights,
        annual_returns, annual_vols, elapsed, gpu_available,
    )
