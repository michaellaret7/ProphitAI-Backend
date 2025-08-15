"""
Portfolio visualization module for correlation-aware portfolio builder.
Handles all charting and plotting operations.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict
import warnings
warnings.filterwarnings('ignore')


class PortfolioVisualizer:
    """Handles portfolio visualization and charting."""
    
    def __init__(self):
        """Initialize the portfolio visualizer."""
        pass
    
    def visualize_portfolio_returns(self, weights: Dict[str, float], returns_data: pd.DataFrame,
                                   correlation_matrix=None, save_plots: bool = True) -> None:
        """
        Visualize portfolio and individual asset returns.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
        returns_data : pd.DataFrame
            Historical returns data
        correlation_matrix : pd.DataFrame, optional
            Correlation matrix for heatmap
        save_plots : bool
            Whether to save plots to files
        """
        if returns_data.empty:
            print("No returns data available for visualization")
            return
        
        # Calculate portfolio returns
        tickers = list(weights.keys())
        portfolio_returns = pd.Series(0, index=returns_data.index)
        
        for ticker in tickers:
            if ticker in returns_data.columns:
                # Only add to portfolio returns where ticker data exists
                ticker_returns = returns_data[ticker].fillna(0)  # Fill NaN with 0 for missing data
                portfolio_returns += ticker_returns * weights[ticker]
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Portfolio Returns Analysis', fontsize=16)
        
        # 1. Cumulative Returns Plot
        ax1 = axes[0, 0]
        cumulative_returns = (1 + returns_data).cumprod()
        portfolio_cumulative = (1 + portfolio_returns).cumprod()
        
        # Plot individual assets in light colors
        for ticker in returns_data.columns:
            ax1.plot(cumulative_returns.index, cumulative_returns[ticker], 
                    alpha=0.3, linewidth=1, label=ticker)
        
        # Plot portfolio in bold
        ax1.plot(portfolio_cumulative.index, portfolio_cumulative, 
                color='red', linewidth=3, label='Portfolio', alpha=0.8)
        
        ax1.set_title('Cumulative Returns')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Cumulative Return')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. Daily Returns Distribution
        ax2 = axes[0, 1]
        portfolio_returns.hist(bins=50, ax=ax2, alpha=0.7, color='blue', edgecolor='black')
        ax2.axvline(x=0, color='red', linestyle='--', alpha=0.5)
        ax2.set_title('Portfolio Daily Returns Distribution')
        ax2.set_xlabel('Daily Return')
        ax2.set_ylabel('Frequency')
        
        # Add statistics
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        skew = portfolio_returns.skew()
        kurtosis = portfolio_returns.kurtosis()
        
        stats_text = f'Mean: {mean_return:.4f}\nStd: {std_return:.4f}\nSkew: {skew:.2f}\nKurtosis: {kurtosis:.2f}'
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 3. Rolling Volatility
        ax3 = axes[1, 0]
        rolling_vol = portfolio_returns.rolling(window=21).std() * np.sqrt(252)  # 21-day rolling vol
        ax3.plot(rolling_vol.index, rolling_vol, color='orange', linewidth=2)
        ax3.fill_between(rolling_vol.index, rolling_vol, alpha=0.3, color='orange')
        ax3.set_title('Portfolio 21-Day Rolling Volatility (Annualized)')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Volatility')
        ax3.grid(True, alpha=0.3)
        
        # 4. Correlation Heatmap or Portfolio Composition
        ax4 = axes[1, 1]
        if correlation_matrix is not None and len(correlation_matrix) <= 10:
            # Only show heatmap if we have 10 or fewer assets
            sns.heatmap(correlation_matrix, annot=True, fmt='.2f', 
                       cmap='coolwarm', center=0, square=True, 
                       linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax4)
            ax4.set_title('Asset Correlation Matrix')
        else:
            # Show portfolio composition instead
            positions = pd.Series({k: abs(v) for k, v in weights.items()})
            positions = positions.sort_values(ascending=True)
            colors = ['green' if weights[ticker] > 0 else 'red' for ticker in positions.index]
            
            positions.plot(kind='barh', ax=ax4, color=colors, alpha=0.7)
            ax4.set_title('Portfolio Composition (Absolute Weights)')
            ax4.set_xlabel('Weight')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_plots:
            plt.savefig('portfolio_returns_analysis.png', dpi=300, bbox_inches='tight')
            print("\nReturns visualization saved to 'portfolio_returns_analysis.png'")
        
        plt.show()
        
        # Additional plot: Drawdown analysis
        self._plot_drawdown_analysis(portfolio_returns, save_plots)
    
    def _plot_drawdown_analysis(self, portfolio_returns: pd.Series, save_plots: bool = True) -> None:
        """
        Plot drawdown analysis for the portfolio.
        
        Parameters:
        -----------
        portfolio_returns : pd.Series
            Portfolio returns series
        save_plots : bool
            Whether to save the plot
        """
        fig2, ax = plt.subplots(figsize=(12, 6))
        
        # Calculate drawdown
        portfolio_cumulative = (1 + portfolio_returns).cumprod()
        running_max = portfolio_cumulative.expanding().max()
        drawdown = (portfolio_cumulative - running_max) / running_max
        
        # Plot drawdown
        ax.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
        ax.plot(drawdown.index, drawdown, color='red', linewidth=1)
        
        # Highlight maximum drawdown
        max_drawdown = drawdown.min()
        max_dd_date = drawdown.idxmin()
        ax.scatter(max_dd_date, max_drawdown, color='darkred', s=100, zorder=5)
        ax.annotate(f'Max DD: {max_drawdown:.2%}\n{max_dd_date.strftime("%Y-%m-%d")}', 
                   xy=(max_dd_date, max_drawdown), xytext=(10, 10), 
                   textcoords='offset points', bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7))
        
        ax.set_title('Portfolio Drawdown Analysis', fontsize=14)
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(top=0.05)  # Add some space at the top
        
        if save_plots:
            plt.savefig('portfolio_drawdown_analysis.png', dpi=300, bbox_inches='tight')
            print("Drawdown analysis saved to 'portfolio_drawdown_analysis.png'")
        
        plt.show()
