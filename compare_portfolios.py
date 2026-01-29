"""
Portfolio Performance Comparison Script

Calculates and compares performance metrics for initial vs final portfolios.
"""

import yaml
from datetime import datetime
from app.core.atlas.tools.portfolio import (
    calculate_portfolio_performance,
    calculate_portfolio_returns_metrics,
)
from app.utils.time_utils import get_current_utc_time

# Define portfolios
final_portfolio = {
    "MSFT": {"allocation": 0.0973, "position": "long"},
    "AMZN": {"allocation": 0.0387, "position": "long"},
    "JPM": {"allocation": 0.1239, "position": "long"},
    "XOM": {"allocation": 0.0743, "position": "long"},
    "PG": {"allocation": 0.0327, "position": "long"},
    "ORCL": {"allocation": 0.0583, "position": "long"},
    "AAPL": {"allocation": 0.0255, "position": "long"},
    "PEP": {"allocation": 0.0633, "position": "long"},
    "JNJ": {"allocation": 0.0061, "position": "long"},
    "VNQ": {"allocation": 0.0305, "position": "long"},
    "HYG": {"allocation": 0.0105, "position": "long"},
    "EEM": {"allocation": 0.0241, "position": "long"},
    "XLB": {"allocation": 0.0709, "position": "long"},
    "XLE": {"allocation": 0.0571, "position": "long"},
    "XLC": {"allocation": 0.127, "position": "long"},
    "LLY": {"allocation": 0.06, "position": "long"},
    "AMGN": {"allocation": 0.05, "position": "long"},
    "LMT": {"allocation": 0.05, "position": "long"}
}

initial_portfolio = {
    "MSFT": {"allocation": 0.0973, "position": "long"},
    "AMZN": {"allocation": 0.0087, "position": "long"},
    "JPM": {"allocation": 0.1239, "position": "long"},
    "XOM": {"allocation": 0.1243, "position": "long"},
    "PG": {"allocation": 0.0327, "position": "long"},
    "ORCL": {"allocation": 0.1183, "position": "long"},
    "AAPL": {"allocation": 0.0255, "position": "long"},
    "PEP": {"allocation": 0.0633, "position": "long"},
    "JNJ": {"allocation": 0.0061, "position": "long"},
    "VNQ": {"allocation": 0.0605, "position": "long"},
    "HYG": {"allocation": 0.0405, "position": "long"},
    "EEM": {"allocation": 0.0441, "position": "long"},
    "XLB": {"allocation": 0.0709, "position": "long"},
    "XLE": {"allocation": 0.0571, "position": "long"},
    "XLC": {"allocation": 0.127, "position": "long"}
}

def validate_portfolio(portfolio_dict, name):
    """Validate portfolio allocations sum to 1.0"""
    total = sum(holding["allocation"] for holding in portfolio_dict.values())
    print(f"\n{name} Total Allocation: {total:.4f}")
    if abs(total - 1.0) > 0.01:
        print(f"⚠️  WARNING: {name} allocations do not sum to 1.0")
    return total

def print_portfolio_holdings(portfolio_dict, name):
    """Print portfolio holdings in a formatted table"""
    print(f"\n{'=' * 60}")
    print(f"{name} Holdings")
    print(f"{'=' * 60}")
    print(f"{'Ticker':<8} {'Allocation':<12} {'Position':<10}")
    print(f"{'-' * 60}")
    for ticker, holding in sorted(portfolio_dict.items()):
        print(f"{ticker:<8} {holding['allocation']:>10.2%}   {holding['position']:<10}")

def compare_portfolios(initial, final):
    """Compare two portfolios and show changes"""
    print(f"\n{'=' * 60}")
    print("Portfolio Changes")
    print(f"{'=' * 60}")

    all_tickers = set(initial.keys()) | set(final.keys())

    print(f"{'Ticker':<8} {'Initial':<12} {'Final':<12} {'Change':<12}")
    print(f"{'-' * 60}")

    for ticker in sorted(all_tickers):
        initial_alloc = initial.get(ticker, {}).get("allocation", 0.0)
        final_alloc = final.get(ticker, {}).get("allocation", 0.0)
        change = final_alloc - initial_alloc

        change_str = f"{change:+.2%}" if change != 0 else "-"
        print(f"{ticker:<8} {initial_alloc:>10.2%}   {final_alloc:>10.2%}   {change_str:>10}")

def calculate_and_display_performance(portfolio_dict, name):
    """Calculate and display performance metrics for a portfolio"""
    print(f"\n{'=' * 60}")
    print(f"{name} Performance Metrics")
    print(f"{'=' * 60}")

    # Calculate days from 2023-12-31 to today
    start_date = datetime(2023, 12, 31)
    current_date = get_current_utc_time()
    lookback_days = (current_date - start_date).days

    print(f"  Period: 2023-12-31 to {current_date.strftime('%Y-%m-%d')} ({lookback_days} days)")

    # Calculate comprehensive performance metrics
    result = calculate_portfolio_performance(
        portfolio_dict=portfolio_dict,
        lookback_days=lookback_days,
        use_total_returns=True,
        rf_annual=0.04,
        benchmark="SPY"
    )

    # Parse YAML result
    metrics = yaml.safe_load(result)

    if metrics.get("success"):
        data = metrics.get("data", {})

        # Display core metrics
        print("\n📊 Core Metrics:")
        print(f"  Annualized Return:    {data.get('annualized_return', 'N/A'):>8.2%}")
        print(f"  Annualized Volatility: {data.get('annualized_volatility', 'N/A'):>8.2%}")

        # Display risk-adjusted metrics
        print("\n⚖️  Risk-Adjusted Metrics:")
        print(f"  Sharpe Ratio:         {data.get('sharpe', 'N/A'):>8.4f}")
        print(f"  Sortino Ratio:        {data.get('sortino', 'N/A'):>8.4f}")
        print(f"  Calmar Ratio (1Y):    {data.get('calmar_1y', 'N/A'):>8.4f}")

        # Display benchmark-relative metrics
        print("\n📈 Benchmark-Relative (vs SPY):")
        print(f"  Beta:                 {data.get('beta', 'N/A'):>8.4f}")
        print(f"  Alpha:                {data.get('alpha', 'N/A'):>8.4f}")
        print(f"  Information Ratio:    {data.get('information_ratio', 'N/A'):>8.4f}")
        print(f"  Tracking Error:       {data.get('tracking_error', 'N/A'):>8.4f}")

        # Display drawdown metrics
        print("\n📉 Risk Metrics:")
        print(f"  Max Drawdown:         {data.get('max_drawdown', 'N/A'):>8.2%}")
        print(f"  Ulcer Index:          {data.get('ulcer_index', 'N/A'):>8.4f}")
        print(f"  Pain Index:           {data.get('pain_index', 'N/A'):>8.4f}")

        # Display win/loss metrics
        print("\n🎯 Win/Loss Metrics:")
        print(f"  Win Rate:             {data.get('win_rate', 'N/A'):>8.2%}")
        print(f"  Profit Factor:        {data.get('profit_factor', 'N/A'):>8.4f}")

        return data
    else:
        print(f"❌ Error calculating performance: {metrics.get('error', 'Unknown error')}")
        return None

def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("PORTFOLIO PERFORMANCE COMPARISON")
    print("=" * 60)

    # Validate portfolios
    print("\n🔍 Validating Portfolios...")
    validate_portfolio(initial_portfolio, "Initial Portfolio")
    validate_portfolio(final_portfolio, "Final Portfolio")

    # Display holdings
    print_portfolio_holdings(initial_portfolio, "Initial Portfolio")
    print_portfolio_holdings(final_portfolio, "Final Portfolio")

    # Show changes
    compare_portfolios(initial_portfolio, final_portfolio)

    # Calculate performance for both portfolios
    initial_metrics = calculate_and_display_performance(initial_portfolio, "Initial Portfolio")
    final_metrics = calculate_and_display_performance(final_portfolio, "Final Portfolio")

    # Display comparison
    if initial_metrics and final_metrics:
        print(f"\n{'=' * 60}")
        print("Performance Comparison Summary")
        print(f"{'=' * 60}")

        metrics_to_compare = [
            ("Annualized Return", "annualized_return", True),
            ("Sharpe Ratio", "sharpe", False),
            ("Sortino Ratio", "sortino", False),
            ("Max Drawdown", "max_drawdown", True),
            ("Win Rate", "win_rate", True),
            ("Beta vs SPY", "beta", False),
            ("Alpha vs SPY", "alpha", False),
        ]

        print(f"\n{'Metric':<25} {'Initial':<12} {'Final':<12} {'Diff':<12} {'Winner'}")
        print(f"{'-' * 75}")

        for metric_name, metric_key, higher_is_better in metrics_to_compare:
            initial_val = initial_metrics.get(metric_key)
            final_val = final_metrics.get(metric_key)

            if initial_val is not None and final_val is not None:
                try:
                    diff = final_val - initial_val

                    # Determine winner (for max_drawdown, less negative is better)
                    if metric_key == "max_drawdown":
                        winner = "Final" if final_val > initial_val else "Initial" if final_val < initial_val else "Tie"
                    elif higher_is_better:
                        winner = "Final" if final_val > initial_val else "Initial" if final_val < initial_val else "Tie"
                    else:
                        winner = "Final" if final_val > initial_val else "Initial" if final_val < initial_val else "Tie"

                    winner_emoji = "🏆" if winner == "Final" else "📍" if winner == "Initial" else "🤝"

                    # Format values appropriately
                    if metric_name in ["Annualized Return", "Max Drawdown", "Win Rate"]:
                        print(f"{metric_name:<25} {initial_val:>10.2%}   {final_val:>10.2%}   {diff:>+10.2%}   {winner_emoji} {winner}")
                    else:
                        print(f"{metric_name:<25} {initial_val:>10.4f}   {final_val:>10.4f}   {diff:>+10.4f}   {winner_emoji} {winner}")
                except Exception:
                    print(f"{metric_name:<25} {'N/A':<12} {'N/A':<12} {'N/A':<12} N/A")

if __name__ == "__main__":
    main()
