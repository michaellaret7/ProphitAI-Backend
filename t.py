from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.utils.gpt_parser import canonical_portfolio
from app.models.portfolio_models import PortfolioInput
from app.db.core.db_config import ProphitAltsSession, UserSession, MarketSession
from app.db.core.prophit_alts_models import FundFinalPosition
from app.db.core.user_data_models import User, Portfolio
from app.db.core.market_data_models import Ticker
from app.utils.decorators.database import with_session
import yaml
from app.utils.serialize_output import serialize_sqlalchemy_obj
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

@with_session('prophit')
def get_final_portfolio_dict(session=None) -> str:
    """
    Get the initial portfolio dictionary.
    """
    positions_query = session.query(FundFinalPosition).filter(FundFinalPosition.fund_name == "consumer_staples_fund").all()

    final_positions = {}
    for position in positions_query:
        final_positions[position.ticker_name] = {
            "ticker": position.ticker_name,
            "allocation": position.portfolio_allocation,
            "position": position.position.value,
            "thesis": position.reasoning,
        }

    return yaml.dump(final_positions, default_flow_style=False)  

session = UserSession()
user = session.query(User).filter(User.email == "michaellaret7@gmail.com").first()
portfolio_id = session.query(Portfolio).filter(Portfolio.user_id == user.id, Portfolio.name == "Auto/Tech and ETF focused Portfolio").all()

portfolio =[]
for position in portfolio_id:
    portfolio.append({
        "ticker": position.ticker,
        "allocation": position.allocation,
        "position": "long" if position.allocation > 0 else "short",
    })

portfolio_original = canonical_portfolio(portfolio)
session.close()

optimized_portfolio = {"portfolio": [{"ticker": "APP", "allocation": 0.028, "position": "long", "changes_from_original": "Decreased allocation from 0.042 to 0.028 to lower portfolio beta and tech clustering."}, {"ticker": "AVGO", "allocation": 0.015, "position": "long", "changes_from_original": "Decreased allocation from 0.034 to 0.015 to reduce semi correlation and drawdown risk."}, {"ticker": "BSX", "allocation": 0.077, "position": "long", "changes_from_original": "Increased allocation from 0.051 to 0.077 due to strong low-beta growth and high Sharpe."}, {"ticker": "CB", "allocation": 0.049, "position": "long", "changes_from_original": "Added P&C insurance for low correlation, high quality/value, and defensive cash flows."}, {"ticker": "DBMF", "allocation": 0.116, "position": "long", "changes_from_original": "Added managed futures ETF for crisis alpha and structural diversification."}, {"ticker": "EIS", "allocation": 0.007, "position": "long", "changes_from_original": "Decreased allocation from 0.037 to 0.007 to minimize EM beta while keeping optionality."}, {"ticker": "IAU", "allocation": 0.094, "position": "long", "changes_from_original": "Added gold ETF as low-correlation hedge improving VaR and drawdown resilience."}, {"ticker": "JNJ", "allocation": 0.049, "position": "long", "changes_from_original": "Added mega-cap pharma to lower beta and improve quality tilt."}, {"ticker": "JPM", "allocation": 0.03, "position": "long", "changes_from_original": "Decreased allocation from 0.043 to 0.030 to moderate financials beta while retaining quality exposure."}, {"ticker": "KO", "allocation": 0.046, "position": "long", "changes_from_original": "Added staples franchise to reduce beta and add stable total return."}, {"ticker": "LMT", "allocation": 0.058, "position": "long", "changes_from_original": "Added defense exposure to diversify macro risk and reduce correlation with tech."}, {"ticker": "MRK", "allocation": 0.052, "position": "long", "changes_from_original": "Added pharma leader for defensive growth and improved risk-adjusted returns."}, {"ticker": "NRG", "allocation": 0.017, "position": "long", "changes_from_original": "Decreased allocation from 0.055 to 0.017 to reduce sector cluster risk while keeping alpha driver."}, {"ticker": "NVDA", "allocation": 0.061, "position": "long", "changes_from_original": "Decreased allocation from 0.065 to 0.061 to moderate semi cluster concentration while retaining core alpha."}, {"ticker": "PG", "allocation": 0.052, "position": "long", "changes_from_original": "Added staples quality compounder to lower correlation and volatility."}, {"ticker": "PLTR", "allocation": 0.017, "position": "long", "changes_from_original": "Decreased allocation from 0.027 to 0.017 to manage beta while keeping asymmetric upside."}, {"ticker": "VCSH", "allocation": 0.15, "position": "long", "changes_from_original": "Increased allocation from 0.030 to 0.150 to materially lower volatility and pairwise correlation."}, {"ticker": "WEC", "allocation": 0.082, "position": "long", "changes_from_original": "Increased allocation from 0.020 to 0.082 to strengthen defensive ballast and reduce correlation."}]}

# Function to get portfolio diversification data
@with_session('market')
def get_portfolio_diversification(portfolio_dict, session=None):
    """Get sector, industry, and sub-industry breakdown for a portfolio."""
    sector_breakdown = {}
    industry_breakdown = {}
    sub_industry_breakdown = {}
    
    for ticker, data in portfolio_dict.items():
        allocation = data.get('allocation', 0)
        if allocation <= 0:  # Skip short positions or zero allocations
            continue
            
        ticker_info = session.query(Ticker).filter(Ticker.ticker == ticker).first()
        if ticker_info:
            # Sector breakdown
            sector = ticker_info.sector or 'Unknown'
            sector_breakdown[sector] = sector_breakdown.get(sector, 0) + allocation
            
            # Industry breakdown
            industry = ticker_info.industry or 'Unknown'
            industry_breakdown[industry] = industry_breakdown.get(industry, 0) + allocation
            
            # Sub-industry breakdown
            sub_industry = ticker_info.sub_industry or 'Unknown'
            sub_industry_breakdown[sub_industry] = sub_industry_breakdown.get(sub_industry, 0) + allocation
        else:
            # If ticker not found, add to Unknown
            sector_breakdown['Unknown'] = sector_breakdown.get('Unknown', 0) + allocation
            industry_breakdown['Unknown'] = industry_breakdown.get('Unknown', 0) + allocation
            sub_industry_breakdown['Unknown'] = sub_industry_breakdown.get('Unknown', 0) + allocation
    
    return sector_breakdown, industry_breakdown, sub_industry_breakdown

# Portfolio Analysis - Last 2 Years
print("=" * 80)
print("PORTFOLIO COMPARISON ANALYSIS - LAST 2 YEARS")
print("=" * 80)

# Set date range for last 2 years
end_date = datetime.now()
start_date = end_date - timedelta(days=504)  # Approximately 2 years

print(f"Analysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print()

# Initialize calculators
returns_calculator = ReturnsCalculator()
performance_calculator = PerformanceCalculator()

# Calculate returns for original portfolio
print("Calculating returns for Original Portfolio...")
try:
    original_returns_series, _ = get_portfolio_returns(portfolio_original, lookback_days=504)
    original_returns = original_returns_series.tolist()
    print(f"✓ Original portfolio returns calculated: {len(original_returns)} data points")
except Exception as e:
    print(f"✗ Error calculating original portfolio returns: {e}")
    original_returns = None

# Calculate returns for optimized portfolio
print("Calculating returns for Optimized Portfolio...")
try:
    # Convert optimized_portfolio to the correct format
    optimized_portfolio_formatted = {}
    for item in optimized_portfolio["portfolio"]:
        optimized_portfolio_formatted[item["ticker"]] = {
            "position": item["position"],
            "allocation": item["allocation"]
        }
    
    optimized_returns_series, _ = get_portfolio_returns(optimized_portfolio_formatted, lookback_days=504)
    optimized_returns = optimized_returns_series.tolist()
    print(f"✓ Optimized portfolio returns calculated: {len(optimized_returns)} data points")
except Exception as e:
    print(f"✗ Error calculating optimized portfolio returns: {e}")
    optimized_returns = None

# Get benchmark returns (SPY)
print("Calculating benchmark returns (SPY)...")
try:
    benchmark_returns_series = get_benchmark_returns("SPY", start=start_date, end=end_date)
    benchmark_returns = benchmark_returns_series.tolist()
    print(f"✓ Benchmark returns calculated: {len(benchmark_returns)} data points")
except Exception as e:
    print(f"✗ Error calculating benchmark returns: {e}")
    benchmark_returns = None

print()

# Calculate performance metrics for both portfolios
def calculate_performance_metrics(returns, portfolio_name):
    if returns is None or len(returns) == 0:
        print(f"⚠️  No returns data available for {portfolio_name}")
        return None
    
    try:
        # Convert to numpy array for calculations
        returns_array = np.array(returns)
        
        # Calculate metrics
        annualized_return = np.mean(returns_array) * 252  # Assuming daily returns
        volatility = np.std(returns_array) * np.sqrt(252)  # Annualized volatility
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Calculate alpha (excess return over benchmark)
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            benchmark_array = np.array(benchmark_returns)
            excess_returns = returns_array - benchmark_array
            alpha = np.mean(excess_returns) * 252  # Annualized alpha
        else:
            alpha = None
        
        return {
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'alpha': alpha,
            'total_return': (1 + returns_array).prod() - 1
        }
    except Exception as e:
        print(f"✗ Error calculating metrics for {portfolio_name}: {e}")
        return None

# Calculate metrics for both portfolios
original_metrics = calculate_performance_metrics(original_returns, "Original Portfolio")
optimized_metrics = calculate_performance_metrics(optimized_returns, "Optimized Portfolio")

# Display results
print("=" * 80)
print("PERFORMANCE METRICS COMPARISON")
print("=" * 80)

if original_metrics:
    print("ORIGINAL PORTFOLIO:")
    print(f"  Annualized Return: {original_metrics['annualized_return']:.2%}")
    print(f"  Volatility: {original_metrics['volatility']:.2%}")
    print(f"  Sharpe Ratio: {original_metrics['sharpe_ratio']:.3f}")
    if original_metrics['alpha'] is not None:
        print(f"  Alpha (vs SPY): {original_metrics['alpha']:.2%}")
    print(f"  Total Return (2Y): {original_metrics['total_return']:.2%}")
    print()

if optimized_metrics:
    print("OPTIMIZED PORTFOLIO:")
    print(f"  Annualized Return: {optimized_metrics['annualized_return']:.2%}")
    print(f"  Volatility: {optimized_metrics['volatility']:.2%}")
    print(f"  Sharpe Ratio: {optimized_metrics['sharpe_ratio']:.3f}")
    if optimized_metrics['alpha'] is not None:
        print(f"  Alpha (vs SPY): {optimized_metrics['alpha']:.2%}")
    print(f"  Total Return (2Y): {optimized_metrics['total_return']:.2%}")
    print()

# Create comparison graph using Seaborn
if original_returns is not None and optimized_returns is not None:
    print("Creating performance comparison graph with Seaborn...")
    
    # Set Seaborn style
    sns.set_style("whitegrid")
    
    # Define custom colors - very distinct
    custom_colors = {
        'Original Portfolio': '#1f77b4',  # Strong Blue
        'Optimized Portfolio': '#ff7f0e',  # Bright Orange
        'SPY Benchmark': '#2ca02c'  # Green
    }
    sns.set_palette(list(custom_colors.values()))
    
    # Align the returns to have the same length (use the minimum length)
    min_length = min(len(original_returns), len(optimized_returns))
    if benchmark_returns is not None:
        min_length = min(min_length, len(benchmark_returns))
    
    # Take the last 'min_length' data points from each series
    original_returns_aligned = original_returns[-min_length:]
    optimized_returns_aligned = optimized_returns[-min_length:]
    
    # Create cumulative returns
    original_cumulative = np.cumprod(1 + np.array(original_returns_aligned)) - 1
    optimized_cumulative = np.cumprod(1 + np.array(optimized_returns_aligned)) - 1
    
    # Create date range for x-axis (using the aligned length)
    dates = pd.date_range(end=end_date, periods=min_length, freq='B')  # Business days
    
    # Create DataFrame for Seaborn
    df_plot = pd.DataFrame({
        'Date': dates,
        'Original Portfolio': original_cumulative * 100,
        'Optimized Portfolio': optimized_cumulative * 100
    })
    
    if benchmark_returns is not None:
        benchmark_returns_aligned = benchmark_returns[-min_length:]
        benchmark_cumulative = np.cumprod(1 + np.array(benchmark_returns_aligned)) - 1
        df_plot['SPY Benchmark'] = benchmark_cumulative * 100
    
    # Melt the dataframe for Seaborn
    df_melted = df_plot.melt(id_vars=['Date'], var_name='Portfolio', value_name='Cumulative Return (%)')
    
    # Get diversification data for both portfolios
    print("Calculating portfolio diversification...")
    orig_sector, orig_industry, orig_sub = get_portfolio_diversification(portfolio_original)
    opt_sector, opt_industry, opt_sub = get_portfolio_diversification(optimized_portfolio_formatted)
    
    # Create the plot with Seaborn - Updated layout for pie charts
    fig = plt.figure(figsize=(18, 12))
    
    # Create grid spec for complex layout
    gs = fig.add_gridspec(3, 3, height_ratios=[2, 1, 1.2], width_ratios=[1, 1, 1], hspace=0.3, wspace=0.25)
    
    # Main performance plot (spans top 3 columns)
    ax1 = fig.add_subplot(gs[0, :])
    
    # Metrics bar plot (spans middle 3 columns)
    ax2 = fig.add_subplot(gs[1, :])
    
    # Main performance plot
    sns.lineplot(data=df_melted, x='Date', y='Cumulative Return (%)', 
                hue='Portfolio', linewidth=2.5, ax=ax1, palette=custom_colors)
    
    ax1.set_title('Portfolio Performance Comparison', fontsize=18, fontweight='bold', pad=20)
    ax1.set_xlabel('')
    ax1.set_ylabel('Cumulative Return (%)', fontsize=14)
    ax1.legend(title='', fontsize=12, loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Add shaded regions for positive/negative returns
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
    ax1.fill_between(dates, 0, original_cumulative * 100, where=(original_cumulative > 0), 
                     alpha=0.1, color='green', label='_nolegend_')
    ax1.fill_between(dates, 0, original_cumulative * 100, where=(original_cumulative <= 0), 
                     alpha=0.1, color='red', label='_nolegend_')
    
    # Performance metrics comparison bar plot
    if original_metrics and optimized_metrics:
        metrics_df = pd.DataFrame({
            'Metric': ['Annualized Return', 'Volatility', 'Sharpe Ratio', 'Total Return'],
            'Original Portfolio': [
                original_metrics['annualized_return'] * 100,
                original_metrics['volatility'] * 100,
                original_metrics['sharpe_ratio'] * 10,  # Scale for visibility
                original_metrics['total_return'] * 100
            ],
            'Optimized Portfolio': [
                optimized_metrics['annualized_return'] * 100,
                optimized_metrics['volatility'] * 100,
                optimized_metrics['sharpe_ratio'] * 10,  # Scale for visibility
                optimized_metrics['total_return'] * 100
            ]
        })
        
        # Melt for grouped bar plot
        metrics_melted = metrics_df.melt(id_vars=['Metric'], var_name='Portfolio', value_name='Value')
        
        # Create grouped bar plot with matching colors
        bar_colors = {'Original Portfolio': '#1f77b4', 'Optimized Portfolio': '#ff7f0e'}
        sns.barplot(data=metrics_melted, x='Metric', y='Value', hue='Portfolio', ax=ax2, palette=bar_colors)
        ax2.set_title('Performance Metrics Comparison', fontsize=14, fontweight='bold')
        ax2.set_xlabel('')
        ax2.set_ylabel('Value (%)', fontsize=12)
        ax2.legend(title='', fontsize=10)
        
        # Add value labels on bars
        for container in ax2.containers:
            ax2.bar_label(container, fmt='%.1f', fontsize=9)
        
        # Add note about Sharpe Ratio scaling
        ax2.text(0.99, 0.99, 'Note: Sharpe Ratio scaled by 10x for visibility', 
                transform=ax2.transAxes, fontsize=9, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    
    # Add pie charts for diversification (bottom row)
    # Sector pie charts
    ax3 = fig.add_subplot(gs[2, 0])
    ax4 = fig.add_subplot(gs[2, 1])
    ax5 = fig.add_subplot(gs[2, 2])
    
    # Helper function to create cleaner pie charts
    def create_pie_chart(ax, data, title, threshold=0.02):
        """Create a pie chart with small slices grouped as 'Other'"""
        # Group small allocations
        grouped_data = {}
        other = 0
        for label, value in data.items():
            if value < threshold:
                other += value
            else:
                grouped_data[label] = value
        if other > 0:
            grouped_data['Other'] = other
        
        # Sort by value for consistent ordering
        sorted_data = dict(sorted(grouped_data.items(), key=lambda x: x[1], reverse=True))
        
        if sorted_data:
            colors = sns.color_palette("husl", len(sorted_data))
            wedges, texts, autotexts = ax.pie(sorted_data.values(), 
                                              labels=sorted_data.keys(), 
                                              autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
                                              colors=colors,
                                              startangle=90)
            ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
            
            # Adjust text properties
            for text in texts:
                text.set_fontsize(9)
            for autotext in autotexts:
                autotext.set_fontsize(8)
                autotext.set_color('white')
                autotext.set_weight('bold')
        else:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)
            ax.set_title(title, fontsize=11, fontweight='bold')
    
    # Create sector comparison
    create_pie_chart(ax3, orig_sector, 'Original Portfolio - Sector Allocation')
    create_pie_chart(ax4, opt_sector, 'Optimized Portfolio - Sector Allocation')
    
    # Create industry comparison for optimized portfolio (most relevant)
    create_pie_chart(ax5, opt_industry, 'Optimized Portfolio - Industry Allocation', threshold=0.03)
    
    plt.tight_layout()
    plt.show()
    print("✓ Seaborn graph with diversification analysis created and displayed")
    
else:
    print("⚠️  Cannot create graph - missing returns data")

print()
print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
