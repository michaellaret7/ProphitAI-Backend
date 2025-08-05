import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from backend.src.repositories.price_data import get_price_data_daily
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors

class CorrelationAwarePortfolioBuilder:
    """
    Portfolio builder that incorporates full risk analysis to optimize portfolio weights.
    Uses covariance matrix and VaR calculations to size positions based on risk contributions.
    """
    
    def __init__(self, tickers: Dict[str, Dict], target_annual_vol: float, portfolio_value: float, leverage: float = 1.0, target_net_exposure: Optional[float] = None, lookback_days: int = 252, max_position_weight: float = 0.10):
        """
        Initialize the portfolio builder.
        
        Parameters:
        -----------
        tickers : Dict[str, Dict]
            Dictionary with ticker symbols as keys and dict containing 'conviction' and 'position' (long/short)
        target_annual_vol : float
            Target annual volatility for the portfolio (e.g., 0.10 for 10%)
        portfolio_value : float
            Total portfolio value in dollars (base capital before leverage)
        leverage : float
            Leverage multiplier (e.g., 1.5 for 150% gross exposure, default 1.0 for no leverage)
        target_net_exposure : Optional[float]
            Target net exposure as fraction of base capital (e.g., 0.35 for 35%, default None for natural exposure)
        lookback_days : int
            Number of days to look back for historical data (default 252 trading days)
        max_position_weight : float
            Maximum weight for any single position (e.g., 0.10 for 10%, default 0.10)
        """
        self.tickers = tickers
        self.target_annual_vol = target_annual_vol
        self.portfolio_value = portfolio_value
        self.leverage = leverage
        self.target_net_exposure = target_net_exposure
        self.lookback_days = lookback_days
        self.max_position_weight = max_position_weight
        self.trading_days = 252
        
        # Initialize data storage
        self.price_data = {}
        self.returns_data = {}
        self.correlation_matrix = None
        self.covariance_matrix = None
        
    def fetch_all_price_data(self) -> None:
        """Fetch historical price data for all tickers in parallel."""
        print("Fetching historical price data...")
        start_date = datetime.now() - timedelta(days=int(self.lookback_days * 1.5))  # Extra buffer
        end_date = datetime.now()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(get_price_data_daily, ticker, start_date, end_date): ticker 
                for ticker in self.tickers.keys()
            }
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data = future.result()
                    if data is not None and not data.empty:
                        self.price_data[ticker] = data
                        print(f"  ☑️  {ticker}: {len(data)} days of data")
                    else:
                        print(f"  ❌ {ticker}: No data available")
                except Exception as e:
                    print(f"  ❌ {ticker}: Error fetching data - {str(e)}")
    
    def calculate_returns(self) -> pd.DataFrame:
        """Calculate daily returns for all assets and combine into a DataFrame."""
        print("\nCalculating returns...")
        returns_dict = {}
        
        for ticker, price_data in self.price_data.items():
            # Ensure datetime index
            if 'date' in price_data.columns:
                price_data = price_data.copy()
                price_data['date'] = pd.to_datetime(price_data['date'])
                price_data.set_index('date', inplace=True)
            
            # Calculate returns
            returns = price_data['close'].pct_change().dropna()
            returns_dict[ticker] = returns
        
        # Combine into DataFrame and align dates
        self.returns_data = pd.DataFrame(returns_dict).dropna()
        print(f"  Combined returns shape: {self.returns_data.shape}")
        return self.returns_data
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate the correlation matrix of asset returns."""
        if self.returns_data.empty:
            self.calculate_returns()
        
        self.correlation_matrix = self.returns_data.corr()
        print(f"\nCorrelation matrix calculated ({self.correlation_matrix.shape[0]}x{self.correlation_matrix.shape[1]})")
        
        # Print average correlations
        mask = np.ones_like(self.correlation_matrix, dtype=bool)
        np.fill_diagonal(mask, 0)
        avg_corr = self.correlation_matrix.values[mask].mean()
        print(f"  Average pairwise correlation: {avg_corr:.3f}")
        
        return self.correlation_matrix
    
    def calculate_covariance_matrix(self) -> pd.DataFrame:
        """Calculate the covariance matrix of asset returns."""
        if self.returns_data.empty:
            self.calculate_returns()
        
        # Annualized covariance matrix
        self.covariance_matrix = self.returns_data.cov() * self.trading_days
        return self.covariance_matrix
    

    def risk_based_portfolio(self, base_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Adjust portfolio weights based on risk contributions using full covariance matrix.
        Each position is sized inversely to its contribution to portfolio risk.
        """
        if self.covariance_matrix is None:
            self.calculate_covariance_matrix()
        
        if base_weights is None:
            base_weights = {ticker: self.tickers[ticker]['conviction'] for ticker in self.tickers}
        
        tickers = list(self.tickers.keys())
        cov_matrix = self.covariance_matrix.loc[tickers, tickers].values
        
        # Get individual volatilities from diagonal
        individual_vols = np.sqrt(np.diag(cov_matrix))
        
        # Calculate risk scores for each asset
        risk_scores = {}
        for i, ticker in enumerate(tickers):
            # Individual volatility component
            vol_score = individual_vols[i]
            
            # Correlation component (average absolute correlation with others)
            corr_with_others = []
            for j in range(len(tickers)):
                if i != j:
                    correlation = cov_matrix[i, j] / (individual_vols[i] * individual_vols[j])
                    corr_with_others.append(abs(correlation))
            avg_corr = np.mean(corr_with_others)
            
            # Combined risk score (higher = riskier)
            risk_scores[ticker] = vol_score * (1 + avg_corr)
        
        # Normalize risk scores
        max_risk = max(risk_scores.values())
        
        # Calculate risk-adjusted weights (inverse risk weighting)
        adjusted_weights = {}
        for ticker in tickers:
            # Lower weight for higher risk assets
            risk_adjustment = max_risk / risk_scores[ticker]
            adjusted_weights[ticker] = base_weights[ticker] * risk_adjustment
        
        # Separate long and short positions
        long_weights = {t: w for t, w in adjusted_weights.items() if self.tickers[t]['position'] == 'long'}
        short_weights = {t: w for t, w in adjusted_weights.items() if self.tickers[t]['position'] == 'short'}
        
        # Normalize within each group
        long_total = sum(long_weights.values())
        short_total = sum(short_weights.values())
        
        if long_total > 0:
            long_weights = {k: v/long_total for k, v in long_weights.items()}
        if short_total > 0:
            short_weights = {k: v/short_total for k, v in short_weights.items()}
        
        # Apply target net exposure if specified
        if self.target_net_exposure is not None:
            # Calculate target long and short values
            gross_exposure = self.leverage
            net_exposure = self.target_net_exposure
            
            # Validate that target net exposure is achievable
            if abs(net_exposure) > gross_exposure:
                raise ValueError(f"Target net exposure ({net_exposure}) cannot exceed gross exposure ({gross_exposure})")
            
            # Solve: long - short = net, long + short = gross
            target_long_pct = (gross_exposure + net_exposure) / 2
            target_short_pct = (gross_exposure - net_exposure) / 2
            
            # Validate we have both long and short positions if needed
            if target_long_pct > 0 and len(long_weights) == 0:
                raise ValueError("Target net exposure requires long positions but none provided")
            if target_short_pct > 0 and len(short_weights) == 0:
                raise ValueError("Target net exposure requires short positions but none provided")
            
            # Scale weights to hit targets
            final_weights = {}
            for ticker, weight in long_weights.items():
                final_weights[ticker] = weight * target_long_pct
            for ticker, weight in short_weights.items():
                final_weights[ticker] = weight * target_short_pct
        else:
            # Natural allocation based on convictions
            total_conviction = sum(base_weights.values())
            final_weights = {k: v/total_conviction for k, v in adjusted_weights.items()}
        
        # Apply position signs before volatility check
        signed_weights = self._apply_position_signs(final_weights)
        
        # Calculate current portfolio volatility
        current_metrics = self.calculate_portfolio_metrics(signed_weights)
        current_vol = current_metrics['annual_volatility']
        
        # Scale weights to achieve target volatility
        if current_vol > 0 and self.target_annual_vol > 0:
            vol_scale = self.target_annual_vol / current_vol
            scaled_weights = {k: v * vol_scale for k, v in signed_weights.items()}
            
            print(f"\nVolatility Scaling:")
            print(f"  Current volatility: {current_vol:.2%}")
            print(f"  Target volatility:  {self.target_annual_vol:.2%}")
            print(f"  Scaling factor:     {vol_scale:.3f}")
            
            # Apply position weight cap after volatility scaling
            capped_weights = self._apply_position_weight_cap_signed(scaled_weights)
            
            return capped_weights
        
        # Apply cap even if no volatility scaling
        capped_weights = self._apply_position_weight_cap_signed(signed_weights)
        return capped_weights
    
    def _apply_position_signs(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply long/short position signs to weights."""
        signed_weights = {}
        for ticker, weight in weights.items():
            if self.tickers[ticker]['position'] == 'short':
                signed_weights[ticker] = -weight
            else:
                signed_weights[ticker] = weight
        return signed_weights
    
    def _apply_position_weight_cap(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Apply maximum position weight cap to ensure no single position exceeds the limit.
        Redistributes excess weight proportionally to uncapped positions in the same group.
        """
        # Separate long and short positions (based on unsigned weights)
        long_weights = {t: w for t, w in weights.items() if self.tickers[t]['position'] == 'long'}
        short_weights = {t: w for t, w in weights.items() if self.tickers[t]['position'] == 'short'}
        
        # Apply cap to each group separately
        capped_long = self._cap_weights_group(long_weights)
        capped_short = self._cap_weights_group(short_weights)
        
        # Combine back
        return {**capped_long, **capped_short}
    
    def _apply_position_weight_cap_signed(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Apply maximum position weight cap to signed weights (positive for long, negative for short).
        Redistributes excess weight proportionally to uncapped positions in the same group.
        """
        # Separate long and short positions based on sign
        long_weights = {t: w for t, w in weights.items() if w > 0}
        short_weights = {t: abs(w) for t, w in weights.items() if w < 0}  # Convert to positive for capping
        
        # Apply cap to each group separately
        capped_long = self._cap_weights_group(long_weights)
        capped_short = self._cap_weights_group(short_weights)
        
        # Combine back with proper signs
        result = {}
        result.update(capped_long)
        for ticker, weight in capped_short.items():
            result[ticker] = -weight  # Re-apply negative sign for shorts
        
        return result
    
    def _cap_weights_group(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Cap weights within a group (long or short) and redistribute excess."""
        if not weights:
            return weights
            
        result = weights.copy()
        max_iterations = 10  # Prevent infinite loops
        
        for _ in range(max_iterations):
            # Find positions exceeding cap
            capped_positions = []
            excess_weight = 0
            
            for ticker, weight in result.items():
                if weight > self.max_position_weight:
                    excess_weight += weight - self.max_position_weight
                    result[ticker] = self.max_position_weight
                    capped_positions.append(ticker)
            
            # If no positions exceed cap, we're done
            if not capped_positions:
                break
            
            # Redistribute excess weight to uncapped positions
            uncapped_positions = [t for t in result.keys() if t not in capped_positions]
            if uncapped_positions:
                # Calculate redistribution proportionally
                uncapped_total = sum(result[t] for t in uncapped_positions)
                if uncapped_total > 0:
                    for ticker in uncapped_positions:
                        result[ticker] += excess_weight * (result[ticker] / uncapped_total)
        
        return result
    
    def calculate_risk_contributions(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate each asset's contribution to portfolio risk."""
        if self.covariance_matrix is None:
            self.calculate_covariance_matrix()
        
        tickers = list(weights.keys())
        w = np.array([weights[ticker] for ticker in tickers])
        cov = self.covariance_matrix.loc[tickers, tickers].values
        
        # Portfolio variance
        portfolio_variance = np.dot(w.T, np.dot(cov, w))
        
        # Marginal contributions to variance
        marginal_contrib = np.dot(cov, w)
        
        # Risk contributions
        risk_contributions = {}
        for i, ticker in enumerate(tickers):
            contrib = w[i] * marginal_contrib[i] / portfolio_variance
            risk_contributions[ticker] = contrib
        
        return risk_contributions
    
    def calculate_portfolio_var(self, weights: Dict[str, float], confidence_levels: List[float] = [0.95, 0.99]) -> Dict[str, float]:
        """Calculate portfolio VaR at different confidence levels."""
        if self.returns_data.empty:
            return {}
        
        # Calculate portfolio returns
        tickers = list(weights.keys())
        portfolio_returns = pd.Series(0, index=self.returns_data.index)
        
        for ticker in tickers:
            if ticker in self.returns_data.columns:
                portfolio_returns += self.returns_data[ticker] * weights[ticker]
        
        # Calculate VaR for different confidence levels
        var_results = {}
        for conf_level in confidence_levels:
            var_percentile = (1 - conf_level) * 100
            daily_var = np.percentile(portfolio_returns, var_percentile)
            
            # Annualized VaR (assuming normal distribution for scaling)
            annual_var = daily_var * np.sqrt(252)
            
            # VaR in dollar terms (based on leveraged capital)
            dollar_var = annual_var * self.portfolio_value * self.leverage
            
            var_results[f'var_{int(conf_level*100)}'] = {
                'daily': daily_var,
                'annual': annual_var,
                'dollar': dollar_var
            }
        
        return var_results
    
    def calculate_portfolio_metrics(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate key portfolio metrics given weights."""
        if self.covariance_matrix is None:
            self.calculate_covariance_matrix()
        
        # Convert to numpy array
        tickers = list(weights.keys())
        w = np.array([weights[ticker] for ticker in tickers])
        
        # Get covariance matrix for these tickers
        cov = self.covariance_matrix.loc[tickers, tickers].values
        
        # Portfolio volatility
        portfolio_variance = np.dot(w.T, np.dot(cov, w))
        portfolio_vol = np.sqrt(portfolio_variance)
        
        # Expected returns (using historical mean)
        mean_returns = self.returns_data[tickers].mean() * self.trading_days
        portfolio_return = np.dot(w, mean_returns)
        
        # Diversification ratio
        weighted_avg_vol = np.dot(np.abs(w), np.sqrt(np.diag(cov)))
        diversification_ratio = weighted_avg_vol / portfolio_vol
        
        # Effective number of assets (using Herfindahl index)
        herfindahl = np.sum(w**2)
        effective_n_assets = 1 / herfindahl if herfindahl > 0 else 0
        
        return {
            'annual_volatility': portfolio_vol,
            'expected_return': portfolio_return,
            'sharpe_ratio': portfolio_return / portfolio_vol if portfolio_vol > 0 else 0,
            'diversification_ratio': diversification_ratio,
            'effective_n_assets': effective_n_assets
        }
    
    def visualize_portfolio_returns(self, weights: Dict[str, float], save_plots: bool = True) -> None:
        """
        Visualize portfolio and individual asset returns.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
        save_plots : bool
            Whether to save plots to files
        """
        if self.returns_data.empty:
            print("No returns data available for visualization")
            return
        
        # Calculate portfolio returns
        tickers = list(weights.keys())
        portfolio_returns = pd.Series(0, index=self.returns_data.index)
        
        for ticker in tickers:
            if ticker in self.returns_data.columns:
                portfolio_returns += self.returns_data[ticker] * weights[ticker]
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Portfolio Returns Analysis', fontsize=16)
        
        # 1. Cumulative Returns Plot
        ax1 = axes[0, 0]
        cumulative_returns = (1 + self.returns_data).cumprod()
        portfolio_cumulative = (1 + portfolio_returns).cumprod()
        
        # Plot individual assets in light colors
        for ticker in self.returns_data.columns:
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
        
        # 4. Correlation Heatmap
        ax4 = axes[1, 1]
        if self.correlation_matrix is not None and len(self.correlation_matrix) <= 10:
            # Only show heatmap if we have 10 or fewer assets
            sns.heatmap(self.correlation_matrix, annot=True, fmt='.2f', 
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
    
    def calculate_detailed_performance_metrics(self, weights: Dict[str, float]) -> Dict:
        """
        Calculate detailed performance metrics over multiple time periods.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
            
        Returns:
        --------
        Dict with detailed performance metrics
        """
        if self.returns_data.empty:
            return {}
        
        # Calculate portfolio returns
        tickers = list(weights.keys())
        portfolio_returns = pd.Series(0, index=self.returns_data.index)
        
        for ticker in tickers:
            if ticker in self.returns_data.columns:
                portfolio_returns += self.returns_data[ticker] * weights[ticker]
        
        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # Calculate various metrics
        metrics = {}
        
        # Total return
        total_return = cumulative_returns.iloc[-1] - 1
        metrics['total_return'] = total_return
        
        # Total profit in dollars (based on leveraged capital)
        leveraged_capital = self.portfolio_value * self.leverage
        metrics['total_profit'] = total_return * leveraged_capital
        
        # Annualized returns for different periods
        days_held = len(portfolio_returns)
        years_held = days_held / 252
        
        metrics['annualized_return'] = (cumulative_returns.iloc[-1] ** (1/years_held)) - 1
        
        # Calculate returns for each year
        portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
        yearly_returns = portfolio_returns.groupby(portfolio_returns.index.year).apply(
            lambda x: (1 + x).prod() - 1
        )
        
        metrics['yearly_returns'] = yearly_returns.to_dict()
        metrics['best_year'] = (yearly_returns.max(), yearly_returns.idxmax())
        metrics['worst_year'] = (yearly_returns.min(), yearly_returns.idxmin())
        
        # Monthly returns statistics
        monthly_returns = portfolio_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        metrics['avg_monthly_return'] = monthly_returns.mean()
        metrics['avg_monthly_profit'] = metrics['avg_monthly_return'] * leveraged_capital
        metrics['best_month'] = monthly_returns.max()
        metrics['worst_month'] = monthly_returns.min()
        metrics['positive_months'] = (monthly_returns > 0).sum() / len(monthly_returns)
        
        # Risk metrics
        metrics['annual_volatility'] = portfolio_returns.std() * np.sqrt(252)
        metrics['downside_deviation'] = portfolio_returns[portfolio_returns < 0].std() * np.sqrt(252)
        
        # Sharpe and Sortino ratios
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        excess_returns = metrics['annualized_return'] - risk_free_rate
        metrics['sharpe_ratio'] = excess_returns / metrics['annual_volatility']
        metrics['sortino_ratio'] = excess_returns / metrics['downside_deviation']
        
        # Drawdown metrics
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        metrics['max_drawdown'] = drawdown.min()
        metrics['avg_drawdown'] = drawdown[drawdown < 0].mean()
        
        # Calmar ratio (annualized return / max drawdown)
        metrics['calmar_ratio'] = metrics['annualized_return'] / abs(metrics['max_drawdown'])
        
        # Win rate
        metrics['daily_win_rate'] = (portfolio_returns > 0).sum() / len(portfolio_returns)
        
        # Value at Risk (95% confidence)
        metrics['var_95'] = np.percentile(portfolio_returns, 5)
        metrics['cvar_95'] = portfolio_returns[portfolio_returns <= metrics['var_95']].mean()
        
        return metrics
    
    def display_performance_summary(self, weights: Dict[str, float]) -> None:
        """Display a comprehensive performance summary."""
        metrics = self.calculate_detailed_performance_metrics(weights)
        
        if not metrics:
            print("No performance metrics available")
            return
        
        print("\n" + "="*80)
        print("DETAILED PERFORMANCE METRICS")
        print("="*80)
        
        print("\n📈 RETURNS:")
        print(f"  Total Return:           {metrics['total_return']:>8.2%}")
        print(f"  Annualized Return:      {metrics['annualized_return']:>8.2%}")
        print(f"  Average Monthly Return: {metrics['avg_monthly_return']:>8.2%}")
        
        print("\n💰 PROFIT (on leveraged capital):")
        print(f"  Total Profit:           ${metrics['total_profit']:>15,.2f}")
        print(f"  Avg Monthly Profit:     ${metrics['avg_monthly_profit']:>15,.2f}")
        
        print("\n📅 YEARLY PERFORMANCE:")
        for year, ret in sorted(metrics['yearly_returns'].items()):
            print(f"  {year}:                   {ret:>8.2%}")
        
        print(f"\n  Best Year:  {metrics['best_year'][1]} ({metrics['best_year'][0]:>6.2%})")
        print(f"  Worst Year: {metrics['worst_year'][1]} ({metrics['worst_year'][0]:>6.2%})")
        
        print("\n📊 RISK METRICS:")
        print(f"  Annual Volatility:      {metrics['annual_volatility']:>8.2%}")
        print(f"  Downside Deviation:     {metrics['downside_deviation']:>8.2%}")
        print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>8.2%}")
        print(f"  Average Drawdown:       {metrics['avg_drawdown']:>8.2%}")
        print(f"  Value at Risk (95%):    {metrics['var_95']:>8.2%}")
        print(f"  CVaR (95%):             {metrics['cvar_95']:>8.2%}")
        
        print("\n📏 RISK-ADJUSTED RETURNS:")
        print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>8.3f}")
        print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>8.3f}")
        print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>8.3f}")
        
        print("\n🎯 WIN RATES:")
        print(f"  Daily Win Rate:         {metrics['daily_win_rate']:>8.1%}")
        print(f"  Positive Months:        {metrics['positive_months']:>8.1%}")
        
        print("\n📆 MONTHLY EXTREMES:")
        print(f"  Best Month:             {metrics['best_month']:>8.2%}")
        print(f"  Worst Month:            {metrics['worst_month']:>8.2%}")
        
        print("="*80)
    
    def build_portfolio(self) -> Dict[str, Dict]:
        """
        Build portfolio using risk-based strategy with target volatility scaling.
        
        Returns:
        --------
        Dict with ticker information including position sizes and metrics
        """
        # Fetch data and calculate correlations
        self.fetch_all_price_data()
        self.calculate_returns()
        self.calculate_correlation_matrix()
        self.calculate_covariance_matrix()
        
        # Get weights using risk-based strategy
        print(f"\nBuilding portfolio using risk-based strategy (covariance & VaR aware)...")
        weights = self.risk_based_portfolio()
        
        # Calculate risk contributions
        risk_contributions = self.calculate_risk_contributions(weights)
        
        # Calculate position sizes
        portfolio_positions = {}
        total_long_value = 0
        total_short_value = 0
        
        print(f"\nPortfolio Allocation (risk-based):")
        print(f"{'Ticker':<8} {'Position':<8} {'Weight':<10} {'Size':<15} {'Volatility':<10} {'Risk Contrib':<12} {'Note':<8}")
        print("-" * 80)
        
        capped_positions = []
        
        for ticker, weight in weights.items():
            position_size = abs(weight) * self.portfolio_value * self.leverage
            
            # Check if position hit the cap
            is_capped = abs(weight) >= (self.max_position_weight - 0.0001)  # Small tolerance for float comparison
            if is_capped:
                capped_positions.append(ticker)
            
            # Get individual volatility
            if ticker in self.price_data:
                vol = VolatilityFactors(self.price_data[ticker]['close']).annualized_volatility(lookback_days=self.lookback_days)
            else:
                vol = 0.0
            
            portfolio_positions[ticker] = {
                'position': self.tickers[ticker]['position'],
                'weight': weight,
                'position_size': position_size if weight >= 0 else -position_size,
                'volatility': vol
            }
            
            if weight >= 0:
                total_long_value += position_size
            else:
                total_short_value += position_size
            
            risk_contrib = risk_contributions.get(ticker, 0)
            note = "CAPPED" if is_capped else ""
            print(f"{ticker:<8} {self.tickers[ticker]['position']:<8} {weight:>9.2%} ${position_size:>13,.2f} {vol:>9.2%} {risk_contrib:>11.2%} {note:<8}")
        
        # Calculate portfolio metrics
        metrics = self.calculate_portfolio_metrics(weights)
        
        # Calculate VaR
        var_metrics = self.calculate_portfolio_var(weights)
        
        # Visualize portfolio returns
        self.visualize_portfolio_returns(weights)
        
        # Display performance summary
        self.display_performance_summary(weights)
        
        # Summary
        print("\n" + "=" * 60)
        print(f"PORTFOLIO SUMMARY")
        print(f"Base Capital:    ${self.portfolio_value:>12,.2f}")
        print(f"Leverage:        {self.leverage:>13.2f}x")
        print(f"Gross Capital:   ${self.portfolio_value * self.leverage:>12,.2f}")
        print(f"\nPOSITION BREAKDOWN:")
        print(f"Long positions:  ${total_long_value:>12,.2f} ({total_long_value/(self.portfolio_value*self.leverage):>6.1%} of gross)")
        print(f"Short positions: ${total_short_value:>12,.2f} ({total_short_value/(self.portfolio_value*self.leverage):>6.1%} of gross)")
        print(f"Gross exposure:  ${total_long_value + total_short_value:>12,.2f} ({(total_long_value + total_short_value)/self.portfolio_value:>6.1%} of base)")
        print(f"Net exposure:    ${total_long_value - total_short_value:>12,.2f} ({(total_long_value - total_short_value)/self.portfolio_value:>6.1%} of base)")
        print(f"\nPORTFOLIO METRICS:")
        print(f"  Annual Volatility:     {metrics['annual_volatility']:>6.2%}")
        print(f"  Expected Return:       {metrics['expected_return']:>6.2%}")
        print(f"  Sharpe Ratio:          {metrics['sharpe_ratio']:>6.3f}")
        print(f"  Diversification Ratio: {metrics['diversification_ratio']:>6.3f}")
        print(f"  Effective # Assets:    {metrics['effective_n_assets']:>6.1f}")
        
        # Display VaR metrics
        if var_metrics:
            print(f"\nRISK METRICS (VaR):")
            for conf_name, var_data in var_metrics.items():
                conf_level = conf_name.replace('var_', '')
                print(f"  {conf_level}% VaR (Daily):     {var_data['daily']:>6.2%}")
                print(f"  {conf_level}% VaR (Annual):    {var_data['annual']:>6.2%}")
                print(f"  {conf_level}% VaR (Dollar):    ${abs(var_data['dollar']):>10,.0f}")
                print()
        
        # Display risk contributions summary
        print("TOP RISK CONTRIBUTORS:")
        sorted_risk_contrib = sorted(risk_contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        for ticker, contrib in sorted_risk_contrib:
            print(f"  {ticker}: {contrib:>6.1%}")
        
        # Display capped positions summary
        if capped_positions:
            print(f"\nPOSITION WEIGHT CAP ({self.max_position_weight:.1%}):")
            print(f"  {len(capped_positions)} position(s) hit the maximum weight cap:")
            for ticker in capped_positions:
                print(f"  - {ticker}")
        
        return portfolio_positions 

if __name__ == "__main__":
    # Consumer Staples Portfolio
    tickers = {
        # Long positions
        "CASY": {"conviction": 0.10, "position": "long"},
        "CELH": {"conviction": 0.10, "position": "long"},
        "ODC": {"conviction": 0.05, "position": "long"},
        "ODD": {"conviction": 0.05, "position": "long"},
        "PM": {"conviction": 0.05, "position": "long"},
        "VITL": {"conviction": 0.05, "position": "long"},
        "WMT": {"conviction": 0.05, "position": "long"},
        "BJ": {"conviction": 0.05, "position": "long"},
        "SFM": {"conviction": 0.05, "position": "long"},
        "COCO": {"conviction": 0.05, "position": "long"},
        "MNST": {"conviction": 0.05, "position": "long"},
        "CL": {"conviction": 0.05, "position": "long"},
        "IPAR": {"conviction": 0.05, "position": "long"},
        "TPB": {"conviction": 0.05, "position": "long"},
        "DOLE": {"conviction": 0.05, "position": "long"},
        "PPC": {"conviction": 0.05, "position": "long"},
        "INGR": {"conviction": 0.05, "position": "long"},
        # Short positions
        "WBA": {"conviction": 0.05, "position": "short"},
        "ANDE": {"conviction": 0.05, "position": "short"},
        "TGT": {"conviction": 0.02, "position": "short"},
        "STZ": {"conviction": 0.05, "position": "short"},
        "PEP": {"conviction": 0.05, "position": "short"},
        "SAM": {"conviction": 0.05, "position": "short"},
        "MGPI": {"conviction": 0.05, "position": "short"},
        "ENR": {"conviction": 0.05, "position": "short"},
        "SPB": {"conviction": 0.05, "position": "short"},
        "COTY": {"conviction": 0.05, "position": "short"},
        "KVUE": {"conviction": 0.05, "position": "short"},
        "KLG": {"conviction": 0.05, "position": "short"},
        "JJSF": {"conviction": 0.05, "position": "short"},
        "SEB": {"conviction": 0.05, "position": "short"},
    }
    
    # Build portfolio with target volatility and portfolio value
    build_portfolio = CorrelationAwarePortfolioBuilder(
        tickers=tickers,
        target_annual_vol=0.17,  # 17% target volatility (adjust as needed)
        portfolio_value=1_000_000,  # $1M base capital (before leverage)
        leverage=1.5,  # 1.75x leverage (175% gross exposure)
        target_net_exposure=0.25,  # 35% net long exposure
        lookback_days=252 * 3  # 3 years of data
    )
    
    # Build risk-based portfolio with target volatility
    print("\n" + "="*80)
    print("CONSUMER STAPLES PORTFOLIO ANALYSIS (3-YEAR PERFORMANCE)")
    print("="*80)
    
    # Build with risk-based strategy and volatility targeting
    portfolio = build_portfolio.build_portfolio()