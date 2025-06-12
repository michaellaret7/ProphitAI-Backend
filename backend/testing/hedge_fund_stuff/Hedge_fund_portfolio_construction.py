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


class LiquidityAnalysis:
    """
    Liquidity analysis and management tools
    """
    
    def __init__(self, fund_manager):
        self.fund = fund_manager
        self.liquidity_tiers = {
            'Tier1': {'max_days_to_liquidate': 1, 'max_allocation': 1.0},
            'Tier2': {'max_days_to_liquidate': 5, 'max_allocation': 0.3},
            'Tier3': {'max_days_to_liquidate': 20, 'max_allocation': 0.2}
        }
    
    def classify_instrument_liquidity(self, volume_data, spread_data):
        """
        Classify instruments by liquidity tiers based on volume and spreads
        
        Parameters:
        volume_data: DataFrame with average daily volumes
        spread_data: DataFrame with bid-ask spreads
        """
        liquidity_scores = {}
        
        for instrument in volume_data.index:
            # Volume score (higher is better)
            volume_percentile = volume_data[instrument] / volume_data.quantile(0.95)
            
            # Spread score (lower is better)
            spread_percentile = 1 - (spread_data[instrument] / spread_data.quantile(0.95))
            
            # Combined score
            liquidity_score = (volume_percentile + spread_percentile) / 2
            
            # Assign tier
            if liquidity_score >= 0.7:
                tier = 'Tier1'
            elif liquidity_score >= 0.4:
                tier = 'Tier2'
            else:
                tier = 'Tier3'
            
            liquidity_scores[instrument] = {
                'score': liquidity_score,
                'tier': tier,
                'volume_score': volume_percentile,
                'spread_score': spread_percentile
            }
        
        return pd.DataFrame(liquidity_scores).T
    
    def calculate_liquidity_risk(self, weights, liquidity_classifications):
        """
        Calculate portfolio-level liquidity risk
        """
        tier_allocations = {}
        
        for tier in ['Tier1', 'Tier2', 'Tier3']:
            tier_instruments = liquidity_classifications[
                liquidity_classifications['tier'] == tier
            ].index
            
            tier_weight = weights[tier_instruments].sum() if len(tier_instruments) > 0 else 0
            tier_allocations[tier] = tier_weight
        
        # Check constraints
        constraints_met = {}
        for tier, allocation in tier_allocations.items():
            max_allowed = self.liquidity_tiers[tier]['max_allocation']
            constraints_met[tier] = allocation <= max_allowed
        
        return {
            'tier_allocations': tier_allocations,
            'constraints_met': constraints_met,
            'total_illiquid': tier_allocations.get('Tier2', 0) + tier_allocations.get('Tier3', 0)
        }


class OptionsStrategyAnalysis:
    """
    Options strategy analysis for enhanced theme expression
    """
    
    def __init__(self, fund_manager):
        self.fund = fund_manager
    
    def analyze_option_strategies(self, underlying, strategy_type='call', 
                                strike_range=0.1, expiration_days=30):
        """
        Analyze option strategies for theme expression
        
        Parameters:
        underlying: Underlying instrument
        strategy_type: 'call', 'put', 'straddle', 'collar'
        strike_range: Range around current price to analyze
        expiration_days: Days to expiration
        """
        # This would require real options data - showing framework
        
        strategies = {
            'long_call': self._analyze_long_call,
            'long_put': self._analyze_long_put,
            'collar': self._analyze_collar,
            'straddle': self._analyze_straddle
        }
        
        if strategy_type in strategies:
            return strategies[strategy_type](underlying, strike_range, expiration_days)
        else:
            raise ValueError(f"Strategy {strategy_type} not supported")
    
    def _analyze_long_call(self, underlying, strike_range, expiration_days):
        """Analyze long call strategy"""
        # Framework for call analysis
        return {
            'strategy': 'long_call',
            'max_profit': 'unlimited',
            'max_loss': 'premium_paid',
            'breakeven': 'strike + premium',
            'risk_reward_ratio': 'asymmetric_upside'
        }
    
    def _analyze_long_put(self, underlying, strike_range, expiration_days):
        """Analyze long put strategy"""
        return {
            'strategy': 'long_put',
            'max_profit': 'strike - premium',
            'max_loss': 'premium_paid',
            'breakeven': 'strike - premium',
            'risk_reward_ratio': 'asymmetric_downside'
        }
    
    def _analyze_collar(self, underlying, strike_range, expiration_days):
        """Analyze collar strategy"""
        return {
            'strategy': 'collar',
            'max_profit': 'call_strike - current_price + put_premium - call_premium',
            'max_loss': 'current_price - put_strike + call_premium - put_premium',
            'characteristics': 'limited_upside_and_downside'
        }
    
    def _analyze_straddle(self, underlying, strike_range, expiration_days):
        """Analyze straddle strategy"""
        return {
            'strategy': 'straddle',
            'max_profit': 'unlimited',
            'max_loss': 'total_premium_paid',
            'breakeven_upper': 'strike + total_premium',
            'breakeven_lower': 'strike - total_premium',
            'characteristics': 'volatility_play'
        }


# Example demonstration of advanced tools
def demonstrate_advanced_tools():
    """Demonstrate advanced portfolio construction tools"""
    
    # Create sample fund with data
    from datetime import datetime, timedelta
    
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
    
    instruments = [
        'SPY', 'EFA', 'EEM', 'TLT', 'HYG', 'GLD', 'DXY', 'CRUDE_OIL',
        'EURUSD', 'GBPUSD', 'USDJPY', 'TNX', 'VIX'
    ]
    
    # Generate returns
    n_instruments = len(instruments)
    correlation_matrix = np.random.rand(n_instruments, n_instruments)
    correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
    np.fill_diagonal(correlation_matrix, 1.0)
    
    # Ensure positive definiteness
    eigenvals, eigenvecs = np.linalg.eigh(correlation_matrix)
    eigenvals = np.maximum(eigenvals, 0.01)
    correlation_matrix = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
    
    # Generate correlated returns
    L = np.linalg.cholesky(correlation_matrix)
    random_returns = np.random.normal(0, 0.01, (len(dates), n_instruments))
    correlated_returns = random_returns @ L.T
    
    returns_df = pd.DataFrame(correlated_returns, index=dates, columns=instruments)    # Initialize fund and theme analysis
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from importlib import import_module
    
    # Import from the file with comma in name
    risk_mgmt = import_module('Hedge_fund_risk_,management')
    GlobalMacroFund = risk_mgmt.GlobalMacroFund
    
    fund = GlobalMacroFund()
    fund.load_market_data(returns_df)
    
    theme_analyzer = ThemeAnalysis(fund)
    
    print("=== Advanced Portfolio Construction Demo ===\n")
    
    # 1. Create sample themes
    print("1. Creating Macro Themes:")
    
    # Theme 1: USD Strength
    usd_strength_theme = theme_analyzer.construct_theme_portfolio(
        theme_name='USD_Strength',
        instruments=['DXY', 'USDJPY', 'TLT', 'SPY'],
        convictions={'DXY': 9, 'USDJPY': 8, 'TLT': 6, 'SPY': 7},
        max_positions=4,
        target_vol=0.08
    )
    print(f"   USD Strength Theme created with {len(usd_strength_theme['instruments'])} instruments")
    
    # Theme 2: Risk-Off
    risk_off_theme = theme_analyzer.construct_theme_portfolio(
        theme_name='Risk_Off',
        instruments=['TLT', 'GLD', 'VIX', 'HYG'],
        convictions={'TLT': 8, 'GLD': 9, 'VIX': 7, 'HYG': -6},  # Short HYG
        max_positions=4,
        target_vol=0.10
    )
    print(f"   Risk-Off Theme created with {len(risk_off_theme['instruments'])} instruments")
    
    # Theme 3: EM Outperformance
    em_theme = theme_analyzer.construct_theme_portfolio(
        theme_name='EM_Outperformance',
        instruments=['EEM', 'EURUSD', 'CRUDE_OIL', 'GLD'],
        convictions={'EEM': 8, 'EURUSD': 6, 'CRUDE_OIL': 7, 'GLD': 5},
        max_positions=4,
        target_vol=0.12
    )
    print(f"   EM Outperformance Theme created with {len(em_theme['instruments'])} instruments")
    
    # 2. Calculate theme correlations
    print("\n2. Theme Correlation Analysis:")
    theme_correlations = theme_analyzer.calculate_theme_correlations()
    print("   Theme correlation matrix:")
    print(theme_correlations.round(3))
    
    # 3. Optimize theme allocation
    print("\n3. Optimizing Theme Allocation:")
    try:
        allocation_result = theme_analyzer.optimize_theme_allocation(
            fund_target_vol=0.10,
            max_theme_weight=0.10
        )
        
        if allocation_result['optimization_success']:
            print(f"   Target Volatility: {allocation_result['target_volatility']:.1%}")
            print(f"   Achieved Volatility: {allocation_result['achieved_volatility']:.1%}")
            print("   Optimal Theme Weights:")
            for theme, weight in allocation_result['theme_weights'].items():
                print(f"     {theme}: {weight:.1%}")
        else:
            print(f"   Optimization failed: {allocation_result['error']}")
    except Exception as e:
        print(f"   Optimization error: {str(e)}")
    
    # 4. Risk attribution analysis
    print("\n4. Risk Attribution Analysis:")
    risk_analyzer = RiskAttributionAnalysis(fund)
    
    # Create sample factor returns
    factor_names = ['Equity_Factor', 'Rates_Factor', 'Credit_Factor', 'FX_Factor']
    factor_returns = pd.DataFrame(
        np.random.normal(0, 0.008, (len(dates), len(factor_names))),
        index=dates,
        columns=factor_names
    )
    
    try:
        factor_analysis = risk_analyzer.calculate_factor_exposures(factor_returns)
        print("   Factor Exposures:")
        for factor, exposure in factor_analysis['factor_exposures'].items():
            print(f"     {factor}: {exposure:.3f}")
        print(f"   Alpha: {factor_analysis['alpha']:.2%}")
        print(f"   R-squared: {factor_analysis['r_squared']:.3f}")
    except Exception as e:
        print(f"   Factor analysis error: {str(e)}")
    
    # 5. Liquidity analysis
    print("\n5. Liquidity Analysis:")
    liquidity_analyzer = LiquidityAnalysis(fund)
    
    # Sample volume and spread data
    volume_data = pd.Series(np.random.lognormal(10, 1, len(instruments)), index=instruments)
    spread_data = pd.Series(np.random.uniform(0.001, 0.05, len(instruments)), index=instruments)
    
    liquidity_classification = liquidity_analyzer.classify_instrument_liquidity(volume_data, spread_data)
    print("   Liquidity Classifications:")
    for instrument, data in liquidity_classification.iterrows():
        print(f"     {instrument}: {data['tier']} (Score: {data['score']:.2f})")
    
    # Sample portfolio weights for liquidity analysis
    sample_weights = pd.Series(1/len(instruments), index=instruments)
    liquidity_risk = liquidity_analyzer.calculate_liquidity_risk(sample_weights, liquidity_classification)
    print("\n   Liquidity Risk Assessment:")
    for tier, allocation in liquidity_risk['tier_allocations'].items():
        constraint_status = "✓" if liquidity_risk['constraints_met'][tier] else "✗"
        print(f"     {tier}: {allocation:.1%} {constraint_status}")
    
    # 6. Generate dashboard
    print("\n6. Generating Theme Dashboard...")
    try:
        theme_analyzer.generate_theme_dashboard()
    except Exception as e:
        print(f"   Dashboard generation error: {str(e)}")
    
    return theme_analyzer, risk_analyzer, liquidity_analyzer

# Run advanced demonstration
if __name__ == "__main__":
    theme_analyzer, risk_analyzer, liquidity_analyzer = demonstrate_advanced_tools()