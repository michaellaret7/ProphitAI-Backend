import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import yfinance as yf  # For data fetching example

class ThemeAnalysis:
    """
    Advanced theme identification and portfolio construction tools
    """
    
    def __init__(self, fund_manager):
        self.fund = fund_manager
        self.themes = {}
        self.theme_correlations = pd.DataFrame()
        
    def identify_macro_themes(self, economic_data, market_data, lookback_days=252):
        """
        Identify macro themes using PCA and clustering analysis
        
        Parameters:
        economic_data: DataFrame with economic indicators
        market_data: DataFrame with market returns
        lookback_days: Lookback period for analysis
        """
        # Combine economic and market data
        combined_data = pd.concat([economic_data, market_data], axis=1).dropna()
        
        # Standardize data
        standardized_data = (combined_data - combined_data.mean()) / combined_data.std()
        
        # Principal Component Analysis
        pca = PCA(n_components=min(10, len(combined_data.columns)))
        pca_results = pca.fit_transform(standardized_data.iloc[-lookback_days:])
        
        # Extract loadings for interpretation
        loadings = pd.DataFrame(
            pca.components_.T,
            columns=[f'PC{i+1}' for i in range(pca.n_components_)],
            index=combined_data.columns
        )
        
        # Clustering analysis
        n_clusters = min(5, len(combined_data.columns) // 3)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(standardized_data.iloc[-lookback_days:].T)
        
        cluster_assignments = pd.Series(clusters, index=combined_data.columns)
        
        return {
            'pca_loadings': loadings,
            'explained_variance': pca.explained_variance_ratio_,
            'cluster_assignments': cluster_assignments,
            'pca_components': pca_results
        }
    
    def construct_theme_portfolio(self, theme_name, instruments, convictions, 
                                max_positions=5, target_vol=0.08):
        """
        Construct a portfolio for a specific macro theme
        
        Parameters:
        theme_name: Name of the theme
        instruments: List of instruments that express the theme
        convictions: Dict mapping instruments to conviction scores (0-10)
        max_positions: Maximum number of positions in theme
        target_vol: Target volatility for the theme
        """
        
        # Filter to top conviction instruments
        conviction_series = pd.Series(convictions)
        top_instruments = conviction_series.nlargest(max_positions).index.tolist()
        
        # Get returns for these instruments
        theme_returns = self.fund.returns_history[top_instruments]
        
        # Calculate expected returns based on convictions and momentum
        expected_returns = self._calculate_expected_returns(theme_returns, conviction_series[top_instruments])
        
        # Optimize weights
        try:
            weights = self.fund.optimize_portfolio_weights(
                expected_returns, 
                target_vol=target_vol,
                max_weight=0.40  # Higher concentration allowed within themes
            )
        except:
            # Fall back to conviction-weighted approach
            weights = conviction_series[top_instruments] / conviction_series[top_instruments].sum()
          # Calculate theme metrics - use only the instruments in this theme
        theme_covariance = self.fund.covariance_matrix.loc[top_instruments, top_instruments]
        
        # Calculate portfolio variance for theme
        portfolio_variance = np.dot(weights.values, np.dot(theme_covariance.values, weights.values))
        portfolio_vol = np.sqrt(portfolio_variance)
        daily_vol = portfolio_vol / np.sqrt(252)
        
        # Create simplified VaR metrics for theme
        z_score = 2.33  # 99% confidence
        var_1day = z_score * daily_vol
        
        theme_var = {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(252),
            'portfolio_vol_annual': portfolio_vol,
            'portfolio_vol_daily': daily_vol
        }
        
        theme_correlation = theme_returns.corr()
        
        self.themes[theme_name] = {
            'instruments': top_instruments,
            'weights': weights,
            'convictions': conviction_series[top_instruments],
            'expected_returns': expected_returns,
            'var_metrics': theme_var,
            'correlation_matrix': theme_correlation,
            'target_volatility': target_vol
        }
        
        return self.themes[theme_name]
    
    def _calculate_expected_returns(self, returns_data, convictions, momentum_weight=0.3):
        """Calculate expected returns based on conviction and momentum"""
        # Historical momentum (6-month return)
        momentum = returns_data.iloc[-126:].mean() * 252  # Annualized
        
        # Conviction-based expected returns (normalize convictions to 0-1 range)
        normalized_convictions = (convictions - convictions.min()) / (convictions.max() - convictions.min())
        conviction_returns = normalized_convictions * 0.15  # Scale to reasonable return expectations
        
        # Combine momentum and conviction
        expected_returns = momentum_weight * momentum + (1 - momentum_weight) * conviction_returns
        
        return expected_returns
    
    def calculate_theme_correlations(self):
        """Calculate correlations between all themes"""
        if len(self.themes) < 2:
            return pd.DataFrame()
        
        theme_returns = {}
        
        for theme_name, theme_data in self.themes.items():
            # Calculate theme-level returns
            instruments = theme_data['instruments']
            weights = theme_data['weights']
            theme_ret = (self.fund.returns_history[instruments] * weights).sum(axis=1)
            theme_returns[theme_name] = theme_ret
        
        theme_returns_df = pd.DataFrame(theme_returns)
        self.theme_correlations = theme_returns_df.corr()
        
        return self.theme_correlations
    
    def optimize_theme_allocation(self, fund_target_vol=0.10, max_theme_weight=0.10):
        """
        Optimize allocation across themes to achieve target fund volatility
        """
        if len(self.themes) == 0:
            raise ValueError("No themes defined. Create themes first.")
        
        # Calculate theme returns and covariance
        theme_returns = {}
        for theme_name, theme_data in self.themes.items():
            instruments = theme_data['instruments']
            weights = theme_data['weights']
            theme_ret = (self.fund.returns_history[instruments] * weights).sum(axis=1)
            theme_returns[theme_name] = theme_ret
        
        theme_returns_df = pd.DataFrame(theme_returns)
        theme_cov = theme_returns_df.cov() * 252  # Annualized
        
        n_themes = len(self.themes)
        
        # Objective: minimize tracking error to target volatility
        def objective(theme_weights):
            portfolio_var = np.dot(theme_weights, np.dot(theme_cov.values, theme_weights))
            portfolio_vol = np.sqrt(portfolio_var)
            return (portfolio_vol - fund_target_vol) ** 2
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        # Bounds
        bounds = [(0, max_theme_weight) for _ in range(n_themes)]
        
        # Initial guess
        x0 = np.ones(n_themes) / n_themes
        
        # Optimize
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if result.success:
            optimal_theme_weights = pd.Series(result.x, index=theme_returns_df.columns)
            achieved_vol = np.sqrt(np.dot(result.x, np.dot(theme_cov.values, result.x)))
            
            return {
                'theme_weights': optimal_theme_weights,
                'achieved_volatility': achieved_vol,
                'target_volatility': fund_target_vol,
                'optimization_success': True
            }
        else:
            return {
                'optimization_success': False,
                'error': result.message
            }
    
    def generate_theme_dashboard(self, save_path=None):
        """Generate comprehensive theme analysis dashboard"""
        if len(self.themes) == 0:
            print("No themes to display. Create themes first.")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Theme correlation heatmap
        if len(self.theme_correlations) > 0:
            sns.heatmap(self.theme_correlations, annot=True, cmap='RdYlBu_r', 
                       center=0, ax=axes[0,0], fmt='.2f')
            axes[0,0].set_title('Theme Correlations')
        
        # 2. Theme volatilities
        theme_vols = []
        theme_names = []
        for name, data in self.themes.items():
            theme_vols.append(data['var_metrics']['portfolio_vol_annual'])
            theme_names.append(name)
        
        axes[0,1].bar(theme_names, theme_vols)
        axes[0,1].set_title('Theme Volatilities')
        axes[0,1].set_ylabel('Annual Volatility')
        axes[0,1].tick_params(axis='x', rotation=45)
        
        # 3. Theme VaR contributions
        theme_vars = []
        for name, data in self.themes.items():
            theme_vars.append(data['var_metrics']['var_1day'])
        
        axes[1,0].bar(theme_names, theme_vars)
        axes[1,0].set_title('Theme 1-Day VaR (99%)')
        axes[1,0].set_ylabel('VaR')
        axes[1,0].tick_params(axis='x', rotation=45)
        
        # 4. Conviction vs Expected Return scatter
        convictions_all = []
        expected_returns_all = []
        theme_labels = []
        
        for name, data in self.themes.items():
            for instrument in data['instruments']:
                convictions_all.append(data['convictions'][instrument])
                expected_returns_all.append(data['expected_returns'][instrument])
                theme_labels.append(name)
        
        scatter = axes[1,1].scatter(convictions_all, expected_returns_all, 
                                  c=range(len(convictions_all)), cmap='viridis', alpha=0.7)
        axes[1,1].set_xlabel('Conviction Score')
        axes[1,1].set_ylabel('Expected Return')
        axes[1,1].set_title('Conviction vs Expected Return')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()

class RiskAttributionAnalysis:
    """
    Advanced risk attribution and performance analysis tools
    """
    
    def __init__(self, fund_manager):
        self.fund = fund_manager
        self.attribution_history = []
    
    def calculate_factor_exposures(self, factor_returns):
        """
        Calculate factor exposures using regression analysis
        
        Parameters:
        factor_returns: DataFrame with factor returns (e.g., equity, rates, credit, FX)
        """
        if self.fund.returns_history.empty:
            raise ValueError("No returns history available")
        
        # Get portfolio returns (assuming equal weights for demonstration)
        portfolio_weights = pd.Series(1/len(self.fund.returns_history.columns), 
                                    index=self.fund.returns_history.columns)
        portfolio_returns = (self.fund.returns_history * portfolio_weights).sum(axis=1)
        
        # Align dates
        common_dates = portfolio_returns.index.intersection(factor_returns.index)
        port_ret = portfolio_returns.loc[common_dates]
        factor_ret = factor_returns.loc[common_dates]
        
        # Multiple regression
        from sklearn.linear_model import LinearRegression
        
        X = factor_ret.values
        y = port_ret.values
        
        reg = LinearRegression().fit(X, y)
        
        factor_exposures = pd.Series(reg.coef_, index=factor_returns.columns)
        alpha = reg.intercept_
        r_squared = reg.score(X, y)
        
        # Calculate factor contributions
        factor_contributions = factor_exposures * factor_ret.mean() * 252  # Annualized
        
        return {
            'factor_exposures': factor_exposures,
            'alpha': alpha * 252,  # Annualized
            'r_squared': r_squared,
            'factor_contributions': factor_contributions
        }
    
    def calculate_performance_attribution(self, weights, benchmark_weights=None):
        """
        Calculate performance attribution at instrument level
        """
        if benchmark_weights is None:
            benchmark_weights = pd.Series(0, index=weights.index)  # Cash benchmark
        
        # Calculate returns
        instrument_returns = self.fund.returns_history.iloc[-21:].mean() * 252  # Last month annualized
        
        # Allocation effect: (w_p - w_b) * R_b
        allocation_effect = (weights - benchmark_weights) * instrument_returns
        
        # Selection effect: w_b * (R_p - R_b) [simplified - assuming R_p = R_i]
        selection_effect = benchmark_weights * (instrument_returns - instrument_returns.mean())
        
        # Interaction effect: (w_p - w_b) * (R_p - R_b)
        interaction_effect = (weights - benchmark_weights) * (instrument_returns - instrument_returns.mean())
        
        total_attribution = allocation_effect + selection_effect + interaction_effect
        
        return pd.DataFrame({
            'allocation_effect': allocation_effect,
            'selection_effect': selection_effect,
            'interaction_effect': interaction_effect,
            'total_attribution': total_attribution,
            'instrument_return': instrument_returns,
            'weight': weights
        })
    
    def rolling_risk_decomposition(self, weights, window=63):
        """
        Calculate rolling risk decomposition over time
        """
        results = []
        
        for i in range(window, len(self.fund.returns_history)):
            # Get window data
            window_returns = self.fund.returns_history.iloc[i-window:i]
            window_cov = window_returns.cov() * 252
            
            # Calculate portfolio metrics for this window
            portfolio_var = np.dot(weights.values, np.dot(window_cov.values, weights.values))
            portfolio_vol = np.sqrt(portfolio_var)
            
            # Individual contributions
            marginal_contributions = np.dot(window_cov.values, weights.values) / portfolio_vol
            component_contributions = weights.values * marginal_contributions
            
            results.append({
                'date': self.fund.returns_history.index[i],
                'portfolio_vol': portfolio_vol,
                'components': dict(zip(weights.index, component_contributions))
            })
        
        return pd.DataFrame(results)



# Simple usage example
def main():
    """
    Simple example showing how to use ThemeAnalysis with price data
    """
    from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers
    
    # 1. Define theme instruments
    ai_stocks = ['NVDA', 'MSFT', 'GOOGL', 'AMD']
    energy_stocks = ['PLTR', 'FSLR', 'NEE', 'ENPH']
    all_tickers = ai_stocks + energy_stocks
    
    # 2. Fetch price data using your function
    print("Fetching price data...")
    price_data = fetch_bulk_price_data_for_tickers(
        tickers=all_tickers,
        start_date_str='2023-01-01',
        end_date_str='2024-01-01',
        frequency='daily'
    )
    
    # 3. Create returns data
    returns_data = {}
    for ticker, prices in price_data.items():
        if len(prices) > 1:
            returns_data[ticker] = prices.pct_change().dropna()
    
    returns_df = pd.DataFrame(returns_data).dropna()
    print(f"Returns data shape: {returns_df.shape}")
    
    # 4. Create minimal fund manager mock
    class SimpleFund:
        def __init__(self, returns_history):
            self.returns_history = returns_history
            self.covariance_matrix = returns_history.cov() * 252  # Annualized
            
        def optimize_portfolio_weights(self, expected_returns, target_vol=0.08, max_weight=0.4):
            # Simple equal weight with bounds
            n_assets = len(expected_returns)
            equal_weight = 1.0 / n_assets
            
            # Cap individual weights at max_weight
            if equal_weight > max_weight:
                # If too many assets, use conviction-weighted approach
                weights = expected_returns / expected_returns.sum()
                weights = weights.clip(0, max_weight)  # No shorts, cap max
                weights = weights / weights.sum()      # Renormalize
            else:
                weights = pd.Series(equal_weight, index=expected_returns.index)
            
            return weights
    
    fund = SimpleFund(returns_df)
    
    # 5. Initialize ThemeAnalysis
    theme_analyzer = ThemeAnalysis(fund)
    
    # 6. Create AI theme
    ai_convictions = {'NVDA': 10, 'MSFT': 8, 'GOOGL': 7, 'AMD': 9}
    ai_theme = theme_analyzer.construct_theme_portfolio(
        theme_name='AI_Revolution',
        instruments=ai_stocks,
        convictions=ai_convictions,
        max_positions=4,
        target_vol=0.12
    )
    
    print("\n=== AI Theme Results ===")
    print(f"Instruments: {ai_theme['instruments']}")
    print(f"Weights:\n{ai_theme['weights']}")
    print(f"Annual Volatility: {ai_theme['var_metrics']['portfolio_vol_annual']:.2%}")
    print(f"1-Day VaR: {ai_theme['var_metrics']['var_1day']:.2%}")
    
    # 7. Create Energy theme  
    energy_convictions = {'PLTR': 9, 'FSLR': 7, 'NEE': 6, 'ENPH': 8}
    energy_theme = theme_analyzer.construct_theme_portfolio(
        theme_name='Energy_Transition',
        instruments=energy_stocks,
        convictions=energy_convictions,
        max_positions=4,
        target_vol=0.15
    )
    
    print("\n=== Energy Theme Results ===")
    print(f"Instruments: {energy_theme['instruments']}")
    print(f"Weights:\n{energy_theme['weights']}")
    print(f"Annual Volatility: {energy_theme['var_metrics']['portfolio_vol_annual']:.2%}")
    
    # 8. Calculate theme correlations
    correlations = theme_analyzer.calculate_theme_correlations()
    print(f"\n=== Theme Correlations ===")
    print(correlations)
    
    # 9. Optimize theme allocation
    allocation = theme_analyzer.optimize_theme_allocation(
        fund_target_vol=0.10,
        max_theme_weight=0.60
    )
    
    if allocation['optimization_success']:
        print(f"\n=== Optimal Theme Allocation ===")
        print(f"Target Vol: {allocation['target_volatility']:.2%}")
        print(f"Achieved Vol: {allocation['achieved_volatility']:.2%}")
        print(f"Theme Weights:\n{allocation['theme_weights']}")
    
    return theme_analyzer

def demo_theme_identification():
    """
    Demonstrate theme identification using dummy economic data
    """
    from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers
    
    # 1. Create dummy economic data
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='D')
    np.random.seed(42)
    
    # Generate realistic economic indicators with some correlation structure
    economic_data = pd.DataFrame({
        'fed_funds_rate': np.random.normal(5.0, 0.5, len(dates)).cumsum() * 0.01 + 4.5,
        '10yr_treasury': np.random.normal(4.2, 0.3, len(dates)).cumsum() * 0.01 + 4.0,
        'cpi_yoy': np.random.normal(3.5, 0.2, len(dates)).cumsum() * 0.005 + 3.2,
        'unemployment': np.random.normal(3.8, 0.1, len(dates)).cumsum() * 0.003 + 3.7,
        'gdp_growth': np.random.normal(2.1, 0.3, len(dates)),
        'oil_price': np.random.normal(75, 5, len(dates)).cumsum() * 0.1 + 70,
        'vix': np.abs(np.random.normal(18, 3, len(dates))),
        'dollar_index': np.random.normal(103, 2, len(dates)).cumsum() * 0.05 + 102
    }, index=dates)
    
    print("=== Economic Data Sample ===")
    print(economic_data.head())
    print(f"Economic data shape: {economic_data.shape}")
    
    # 2. Get market data  
    tickers = ['SPY', 'TLT', 'GLD', 'MSFT', 'GOOGL']
    print(f"\nFetching market data for: {tickers}")
    price_data = fetch_bulk_price_data_for_tickers(
        tickers=tickers,
        start_date_str='2023-01-01', 
        end_date_str='2024-01-01',
        frequency='daily'
    )
    
    # Convert to returns
    market_returns = {}
    for ticker, prices in price_data.items():
        if len(prices) > 1:
            market_returns[ticker] = prices.pct_change().dropna()
    
    market_data = pd.DataFrame(market_returns).dropna()
    print(f"Market data shape: {market_data.shape}")
    
    # 3. Create minimal fund for theme analysis
    class SimpleFund:
        def __init__(self):
            pass
    
    fund = SimpleFund()
    theme_analyzer = ThemeAnalysis(fund)
    
    # 4. Run theme identification
    print("\n=== Running Theme Identification ===")
    theme_results = theme_analyzer.identify_macro_themes(
        economic_data=economic_data,
        market_data=market_data,
        lookback_days=200
    )
    
    # 5. Display results
    print("\n=== PCA Results ===")
    print("Explained Variance by Component:")
    for i, var in enumerate(theme_results['explained_variance'][:5]):
        print(f"PC{i+1}: {var:.3f} ({var*100:.1f}%)")
    
    print(f"\nTotal variance explained by first 5 PCs: {theme_results['explained_variance'][:5].sum():.1%}")
    
    print("\n=== Top Loadings for First 3 Principal Components ===")
    loadings = theme_results['pca_loadings']
    
    for pc in ['PC1', 'PC2', 'PC3']:
        print(f"\n{pc} - Top Contributors:")
        top_loadings = loadings[pc].abs().nlargest(5)
        for indicator, loading in top_loadings.items():
            direction = "+" if loadings.loc[indicator, pc] > 0 else "-"
            print(f"  {direction} {indicator}: {abs(loading):.3f}")
    
    print("\n=== Cluster Assignments ===")
    clusters = theme_results['cluster_assignments']
    for cluster_id in sorted(clusters.unique()):
        indicators = clusters[clusters == cluster_id].index.tolist()
        print(f"Cluster {cluster_id}: {indicators}")
    
    print("\n=== Theme Interpretation ===")
    # Interpret the first principal component
    pc1_loadings = loadings['PC1']
    top_positive = pc1_loadings.nlargest(3)
    top_negative = pc1_loadings.nsmallest(3)
    
    print("PC1 could represent a macro theme driven by:")
    print("Positive drivers (move together):")
    for indicator, loading in top_positive.items():
        print(f"  - {indicator}: {loading:.3f}")
    
    print("Negative drivers (move opposite):")  
    for indicator, loading in top_negative.items():
        print(f"  - {indicator}: {loading:.3f}")
    
    return theme_results

# Uncomment to run the example
if __name__ == "__main__":
    # analyzer = main()  # Theme construction example
    theme_results = demo_theme_identification()  # Theme identification example

