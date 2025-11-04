"""
Portfolio Evaluation Script

Calculates and displays comprehensive performance metrics for a single portfolio.
"""

import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import calculate_portfolio_performance
from app.utils.time_utils import get_current_utc_time
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns


# Define portfolio to evaluate
portfolio = {
    "LLY": {
        "allocation": 0.0619,
        "position": "long"
    },
    "JNJ": {
        "allocation": 0.0567,
        "position": "long"
    },
    "AMGN": {
        "allocation": 0.0464,
        "position": "long"
    },
    "UNH": {
        "allocation": 0.0412,
        "position": "long"
    },
    "MSFT": {
        "allocation": 0.0619,
        "position": "long"
    },
    "ADBE": {
        "allocation": 0.0515,
        "position": "long"
    },
    "ORCL": {
        "allocation": 0.0412,
        "position": "long"
    },
    "JPM": {
        "allocation": 0.0619,
        "position": "long"
    },
    "BLK": {
        "allocation": 0.0412,
        "position": "long"
    },
    "PG": {
        "allocation": 0.0515,
        "position": "long"
    },
    "KO": {
        "allocation": 0.0515,
        "position": "long"
    },
    "CAT": {
        "allocation": 0.0722,
        "position": "long"
    },
    "HD": {
        "allocation": 0.0515,
        "position": "long"
    },
    "BND": {
        "allocation": 0.1340,
        "position": "long"
    },
    "SHY": {
        "allocation": 0.0515,
        "position": "long"
    },
    "SCHD": {
        "allocation": 0.0722,
        "position": "long"
    },
    "VEA": {
        "allocation": 0.0309,
        "position": "long"
    },
    "XLU": {
        "allocation": 0.0206,
        "position": "long"
    }
}


def validate_portfolio(portfolio_dict):
    """Validate portfolio allocations sum to 1.0"""
    total = sum(holding["allocation"] for holding in portfolio_dict.values())
    print(f"\n📊 Total Allocation: {total:.4f}")

    if abs(total - 1.0) > 0.01:
        print(f"⚠️  WARNING: Portfolio allocations do not sum to 1.0")
        return False

    print("✅ Portfolio allocations are valid")
    return True


def format_percentage(value, width=8, decimals=2):
    """Format a value as percentage, handling None and 'N/A'"""
    if value is None or value == 'N/A' or (isinstance(value, str) and value == 'N/A'):
        return f"{'N/A':>{width}}"
    try:
        return f"{value:>{width}.{decimals}%}"
    except (ValueError, TypeError):
        return f"{'N/A':>{width}}"


def format_float(value, width=8, decimals=4):
    """Format a value as float, handling None and 'N/A'"""
    if value is None or value == 'N/A' or (isinstance(value, str) and value == 'N/A'):
        return f"{'N/A':>{width}}"
    try:
        return f"{value:>{width}.{decimals}f}"
    except (ValueError, TypeError):
        return f"{'N/A':>{width}}"


def print_portfolio_holdings(portfolio_dict):
    """Print portfolio holdings in a formatted table"""
    print(f"\n{'=' * 60}")
    print("Portfolio Holdings")
    print(f"{'=' * 60}")
    print(f"{'Ticker':<8} {'Allocation':<12} {'Position':<10}")
    print(f"{'-' * 60}")

    for ticker, holding in sorted(portfolio_dict.items()):
        print(f"{ticker:<8} {holding['allocation']:>10.2%}   {holding['position']:<10}")

    print(f"\n�� Total Securities: {len(portfolio_dict)}")


def calculate_and_display_performance(portfolio_dict, start_date_str="2023-12-31", benchmark="SPY", rf_annual=0.04):
    """Calculate and display comprehensive performance metrics for a portfolio"""
    print(f"\n{'=' * 60}")
    print("Performance Metrics")
    print(f"{'=' * 60}")

    # Calculate days from start date to today
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    current_date = get_current_utc_time()
    lookback_days = (current_date - start_date).days

    print(f"\n⏰ Period: {start_date_str} to {current_date.strftime('%Y-%m-%d')} ({lookback_days} days)")
    print(f"📊 Benchmark: {benchmark}")
    print(f"💰 Risk-Free Rate: {rf_annual:.2%} annual")

    # Calculate comprehensive performance metrics
    result = calculate_portfolio_performance(
        portfolio_dict=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=True,
        rf_annual=rf_annual,
        benchmark=benchmark
    )

    # Parse YAML result
    metrics = yaml.safe_load(result)

    if metrics.get("success"):
        data = metrics.get("data", {})

        # Display core metrics
        print("\n📊 Core Performance Metrics:")
        print(f"  Annualized Return:     {format_percentage(data.get('annualized_return'))}")
        print(f"  Annualized Volatility: {format_percentage(data.get('annualized_volatility'))}")
        print(f"  Total Return:          {format_percentage(data.get('total_return'))}")

        # Display risk-adjusted metrics
        print("\n⚖️  Risk-Adjusted Metrics:")
        print(f"  Sharpe Ratio:          {format_float(data.get('sharpe'))}")
        print(f"  Sortino Ratio:         {format_float(data.get('sortino'))}")
        print(f"  Calmar Ratio (1Y):     {format_float(data.get('calmar_1y'))}")

        # Display benchmark-relative metrics
        print(f"\n📈 Benchmark-Relative (vs {benchmark}):")
        print(f"  Beta:                  {format_float(data.get('beta'))}")
        print(f"  Alpha:                 {format_float(data.get('alpha'))}")
        print(f"  Information Ratio:     {format_float(data.get('information_ratio'))}")
        print(f"  Tracking Error:        {format_float(data.get('tracking_error'))}")

        # Display drawdown metrics
        print("\n📉 Drawdown & Risk Metrics:")
        print(f"  Max Drawdown:          {format_percentage(data.get('max_drawdown'))}")
        print(f"  Ulcer Index:           {format_float(data.get('ulcer_index'))}")
        print(f"  Pain Index:            {format_float(data.get('pain_index'))}")

        # Display win/loss metrics
        print("\n🎯 Win/Loss Metrics:")
        print(f"  Win Rate:              {format_percentage(data.get('win_rate'))}")
        print(f"  Profit Factor:         {format_float(data.get('profit_factor'))}")

        # Display summary assessment
        print(f"\n{'=' * 60}")
        print("Portfolio Assessment")
        print(f"{'=' * 60}")

        annualized_return = data.get('annualized_return', 0) or 0
        sharpe = data.get('sharpe', 0) or 0
        max_drawdown = data.get('max_drawdown', 0) or 0

        print(f"\n📋 Quick Summary:")
        returns_label = 'Strong' if annualized_return > 0.10 else 'Moderate' if annualized_return > 0.05 else 'Weak'
        risk_adj_label = 'Excellent' if sharpe > 1.5 else 'Good' if sharpe > 1.0 else 'Fair' if sharpe > 0.5 else 'Poor'
        downside_label = 'High' if max_drawdown < -0.20 else 'Moderate' if max_drawdown < -0.10 else 'Low'

        print(f"  Returns:               {returns_label} ({format_percentage(annualized_return).strip()})")
        print(f"  Risk-Adjusted Returns: {risk_adj_label} (Sharpe: {sharpe:.2f})")
        print(f"  Downside Risk:         {downside_label} (Max DD: {format_percentage(max_drawdown).strip()})")

        return data
    else:
        print(f"❌ Error calculating performance: {metrics.get('error', 'Unknown error')}")
        return None


def plot_returns_vs_benchmark(portfolio_dict, start_date_str="2023-12-31", benchmark="SPY"):
    """Plot cumulative returns of portfolio vs benchmark"""
    print(f"\n{'=' * 60}")
    print(f"Plotting Returns vs {benchmark}")
    print(f"{'=' * 60}")

    try:
        # Calculate date range
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        current_date = get_current_utc_time()
        lookback_days = (current_date - start_date).days

        print(f"\n📥 Fetching portfolio and benchmark data (including dividends)...")

        # Use the same functions as the performance calculator to ensure consistency
        # This includes dividends in the returns calculation
        portfolio_returns, weights = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days,
            use_total_returns=True,  # Include dividends for accurate returns
            dropna=False,
            normalization="gross"
        )

        if portfolio_returns is None or portfolio_returns.empty:
            print("❌ Failed to fetch portfolio data")
            return

        # Get benchmark returns (also with dividends)
        benchmark_returns = get_benchmark_returns(
            benchmark=benchmark,
            lookback_days=lookback_days,
            use_total_returns=True
        )

        if benchmark_returns is None or benchmark_returns.empty:
            print(f"❌ Failed to fetch {benchmark} data")
            return

        # Align the indices
        common_index = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_returns = portfolio_returns.loc[common_index]
        benchmark_returns = benchmark_returns.loc[common_index]

        # Calculate cumulative returns
        portfolio_cumulative = (1 + portfolio_returns).cumprod() - 1
        benchmark_cumulative = (1 + benchmark_returns).cumprod() - 1

        # Create the plot
        plt.figure(figsize=(14, 8))

        # Plot cumulative returns
        plt.plot(portfolio_cumulative.index, portfolio_cumulative * 100,
                label='Portfolio', linewidth=2, color='#2E86AB')
        plt.plot(benchmark_cumulative.index, benchmark_cumulative * 100,
                label=benchmark, linewidth=2, color='#A23B72', linestyle='--')

        # Formatting
        plt.title(f'Portfolio vs {benchmark} - Cumulative Returns',
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Date', fontsize=12, fontweight='bold')
        plt.ylabel('Cumulative Return (%)', fontsize=12, fontweight='bold')
        plt.legend(fontsize=11, loc='upper left')
        plt.grid(True, alpha=0.3, linestyle='--')

        # Format y-axis as percentage
        ax = plt.gca()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

        # Calculate final returns and annualized metrics
        final_portfolio_return = portfolio_cumulative.iloc[-1] * 100
        final_benchmark_return = benchmark_cumulative.iloc[-1] * 100
        outperformance = final_portfolio_return - final_benchmark_return

        # Calculate annualized returns using actual data range
        actual_start_date = portfolio_returns.index[0]
        actual_end_date = portfolio_returns.index[-1]
        num_days = (actual_end_date - actual_start_date).days
        years = num_days / 365.25

        # Annualized return formula: (1 + total_return) ^ (1/years) - 1
        portfolio_total_return = portfolio_cumulative.iloc[-1]
        benchmark_total_return = benchmark_cumulative.iloc[-1]

        portfolio_annualized = ((1 + portfolio_total_return) ** (1 / years) - 1) * 100
        benchmark_annualized = ((1 + benchmark_total_return) ** (1 / years) - 1) * 100
        annualized_outperformance = portfolio_annualized - benchmark_annualized

        text_str = f'Portfolio: {final_portfolio_return:+.2f}%\n{benchmark}: {final_benchmark_return:+.2f}%\nOutperformance: {outperformance:+.2f}%'
        plt.text(0.02, 0.98, text_str, transform=ax.transAxes,
                fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'))

        plt.tight_layout()

        # Save the plot
        output_file = "portfolio_vs_benchmark.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n✅ Plot saved to: {output_file}")

        # Display the plot
        plt.show()

        print(f"\n📊 Final Results:")
        print(f"  Period:                {actual_start_date.strftime('%Y-%m-%d')} to {actual_end_date.strftime('%Y-%m-%d')}")
        print(f"  Duration:              {num_days} days ({years:.2f} years)")
        print(f"\n  Total Returns (incl. dividends):")
        print(f"    Portfolio:           {final_portfolio_return:>8.2f}%")
        print(f"    {benchmark}:                 {final_benchmark_return:>8.2f}%")
        print(f"    Outperformance:      {outperformance:>+8.2f}%")
        print(f"\n  Annualized Returns (incl. dividends):")
        print(f"    Portfolio:           {portfolio_annualized:>8.2f}%")
        print(f"    {benchmark}:                 {benchmark_annualized:>8.2f}%")
        print(f"    Outperformance:      {annualized_outperformance:>+8.2f}%")

    except Exception as e:
        print(f"❌ Error creating plot: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("PORTFOLIO EVALUATION")
    print("=" * 60)

    # Validate portfolio
    print("\n🔍 Validating Portfolio...")
    is_valid = validate_portfolio(portfolio)

    if not is_valid:
        print("\n⚠️  Please fix allocation issues before continuing")
        return

    # Display holdings
    print_portfolio_holdings(portfolio)

    # Calculate and display performance
    metrics = calculate_and_display_performance(
        portfolio,
        start_date_str="2023-12-31",
        benchmark="SPY",
        rf_annual=0.002
    )

    if metrics:
        # Plot returns vs benchmark
        plot_returns_vs_benchmark(
            portfolio,
            start_date_str="2023-12-31",
            benchmark="SPY"
        )

        print(f"\n{'=' * 60}")
        print("✅ Portfolio evaluation complete!")
        print(f"{'=' * 60}\n")
    else:
        print(f"\n{'=' * 60}")
        print("❌ Portfolio evaluation failed")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
