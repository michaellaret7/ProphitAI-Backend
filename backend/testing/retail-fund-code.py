import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.linalg import sqrtm
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class RetailFund:
    """
    Retail Sector Long/Short Equity Hedge Fund Risk Management and Portfolio Construction System
    """
    
    def __init__(self, target_vol_min=0.10, target_vol_max=0.25, confidence_level=0.99):
        self.target_vol_min = target_vol_min
        self.target_vol_max = target_vol_max
        self.confidence_level = confidence_level
        self.z_score = stats.norm.ppf(confidence_level)  # 2.33 for 99%
        self.trading_days = 252
        
        # Portfolio state variables
        self.positions = pd.DataFrame()
        self.returns_history = pd.DataFrame()
        self.correlation_matrix = pd.DataFrame()
        self.covariance_matrix = pd.DataFrame()
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.risk_scalar = 1.0
        
    def load_market_data(self, returns_data):
        """
        Load historical returns data for all instruments
        
        Parameters:
        returns_data: DataFrame with instruments as columns, dates as index
        """
        self.returns_history = returns_data
        self.calculate_correlation_matrix()
        self.calculate_covariance_matrix()
        
    def calculate_volatility(self, returns, window=252):
        """Calculate annualized volatility"""
        return returns.rolling(window=window).std() * np.sqrt(self.trading_days)
    
    def calculate_correlation_matrix(self, window=252, exponential_weight=True):
        """
        Calculate correlation matrix with optional exponential weighting
        """
        if exponential_weight:
            # Exponentially weighted correlation
            ewm_corr = self.returns_history.ewm(span=window).corr()
            # Get the most recent correlation matrix
            if len(ewm_corr) > 0:
                self.correlation_matrix = ewm_corr.iloc[-len(self.returns_history.columns):, :]
            else:
                self.correlation_matrix = self.returns_history.corr()
        else:
            self.correlation_matrix = self.returns_history.rolling(window=window).corr().iloc[-1]
            
        return self.correlation_matrix
    
    def calculate_covariance_matrix(self, window=252):
        """
        Calculate covariance matrix: Σ = DRD where D is volatility diagonal matrix
        """
        # Calculate volatilities
        volatilities = self.returns_history.rolling(window=window).std().iloc[-1] * np.sqrt(self.trading_days)
        
        # Handle NaN values
        volatilities = volatilities.fillna(self.returns_history.std() * np.sqrt(self.trading_days))
        
        # Create diagonal matrix of volatilities
        D = np.diag(volatilities)
        
        # Get correlation matrix
        R = self.correlation_matrix.values
        
        # Calculate covariance matrix
        self.covariance_matrix = pd.DataFrame(
            np.dot(np.dot(D, R), D),
            index=self.returns_history.columns,
            columns=self.returns_history.columns
        )
        
        # Ensure positive definiteness
        self.covariance_matrix = self._ensure_positive_definite(self.covariance_matrix)
        
        return self.covariance_matrix
    
    def _ensure_positive_definite(self, cov_matrix):
        """Ensure covariance matrix is positive definite using eigenvalue decomposition"""
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix.values)
        eigenvals = np.maximum(eigenvals, 1e-8)  # Set minimum eigenvalue
        
        reconstructed = np.dot(eigenvecs, np.dot(np.diag(eigenvals), eigenvecs.T))
        
        return pd.DataFrame(reconstructed, index=cov_matrix.index, columns=cov_matrix.columns)
    
    def calculate_portfolio_var(self, weights, method='parametric'):
        """
        Calculate portfolio VaR using different methods
        
        Parameters:
        weights: Series or array of portfolio weights
        method: 'parametric', 'historical', or 'monte_carlo'
        """
        if method == 'parametric':
            return self._parametric_var(weights)
        elif method == 'historical':
            return self._historical_var(weights)
        elif method == 'monte_carlo':
            return self._monte_carlo_var(weights)
    
    def _parametric_var(self, weights):
        """Parametric VaR calculation assuming normal distribution"""
        # Convert weights to numpy array if needed
        if isinstance(weights, pd.Series):
            weights = weights.values
        
        # Portfolio volatility (annualized)
        portfolio_variance = np.dot(weights, np.dot(self.covariance_matrix.values, weights))
        portfolio_vol = np.sqrt(portfolio_variance)
        
        # Daily portfolio volatility
        daily_vol = portfolio_vol / np.sqrt(self.trading_days)
        
        # 1-day VaR at specified confidence level
        var_1day = self.z_score * daily_vol
        
        return {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(self.trading_days),
            'portfolio_vol_annual': portfolio_vol,
            'portfolio_vol_daily': daily_vol
        }
    
    def _historical_var(self, weights):
        """Historical simulation VaR"""
        # Calculate portfolio returns
        portfolio_returns = (self.returns_history * weights).sum(axis=1)
        
        # Calculate VaR as percentile
        var_1day = -np.percentile(portfolio_returns, (1 - self.confidence_level) * 100)
        
        return {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(self.trading_days),
            'portfolio_vol_annual': portfolio_returns.std() * np.sqrt(self.trading_days),
            'portfolio_vol_daily': portfolio_returns.std()
        }
    
    def _monte_carlo_var(self, weights, n_simulations=10000):
        """Monte Carlo VaR simulation"""
        # Generate random returns based on covariance matrix
        mean_returns = self.returns_history.mean().values
        
        # Cholesky decomposition for correlated random variables
        L = np.linalg.cholesky(self.covariance_matrix.values / self.trading_days)
        
        # Generate simulations
        random_normals = np.random.normal(0, 1, (n_simulations, len(weights)))
        simulated_returns = mean_returns + np.dot(random_normals, L.T)
        
        # Calculate portfolio returns
        portfolio_returns = np.dot(simulated_returns, weights)
        
        # Calculate VaR
        var_1day = -np.percentile(portfolio_returns, (1 - self.confidence_level) * 100)
        
        return {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(self.trading_days),
            'portfolio_vol_annual': portfolio_returns.std() * np.sqrt(self.trading_days),
            'portfolio_vol_daily': portfolio_returns.std()
        }
    
    def calculate_diversified_vs_undiversified_var(self, weights):
        """Compare diversified vs undiversified VaR to measure diversification benefit"""
        # Diversified VaR (portfolio approach)
        diversified_var = self._parametric_var(weights)['var_1day']
        
        # Undiversified VaR (sum of individual VaRs)
        individual_vols = np.sqrt(np.diag(self.covariance_matrix.values)) / np.sqrt(self.trading_days)
        undiversified_var = np.sum(np.abs(weights) * individual_vols * self.z_score)
        
        diversification_benefit = (undiversified_var - diversified_var) / undiversified_var
        
        return {
            'diversified_var': diversified_var,
            'undiversified_var': undiversified_var,
            'diversification_benefit': diversification_benefit
        }
    
    def calculate_expected_shortfall(self, weights, method='historical'):
        """Calculate Expected Shortfall (Conditional VaR)"""
        if method == 'historical':
            portfolio_returns = (self.returns_history * weights).sum(axis=1)
            var_threshold = -np.percentile(portfolio_returns, (1 - self.confidence_level) * 100)
            
            # Expected shortfall is average of losses beyond VaR
            tail_losses = portfolio_returns[portfolio_returns <= -var_threshold]
            expected_shortfall = -tail_losses.mean() if len(tail_losses) > 0 else var_threshold
            
        elif method == 'parametric':
            # For normal distribution: ES = σ * φ(Φ^(-1)(α)) / (1-α)
            # where φ is PDF and Φ is CDF
            portfolio_vol_daily = self._parametric_var(weights)['portfolio_vol_daily']
            alpha = 1 - self.confidence_level
            
            expected_shortfall = portfolio_vol_daily * stats.norm.pdf(stats.norm.ppf(alpha)) / alpha
        
        return expected_shortfall
    
    def calculate_marginal_var(self, weights):
        """Calculate marginal VaR contribution of each position"""
        weights_array = weights.values if isinstance(weights, pd.Series) else weights
        
        # Portfolio volatility
        portfolio_var = np.dot(weights_array, np.dot(self.covariance_matrix.values, weights_array))
        portfolio_vol = np.sqrt(portfolio_var) / np.sqrt(self.trading_days)
        
        # Marginal VaR = (dVaR/dw_i) = (Σw * cov_i) / (portfolio_vol * sqrt(252)) * z_score
        marginal_var = np.dot(self.covariance_matrix.values, weights_array) / (portfolio_vol * np.sqrt(self.trading_days)) * self.z_score
        
        # Component VaR = weight * marginal VaR
        component_var = weights_array * marginal_var
        
        return pd.Series(marginal_var, index=self.covariance_matrix.index), pd.Series(component_var, index=self.covariance_matrix.index)
    
    def optimize_portfolio_weights(self, expected_returns, target_vol=None, max_weight=0.10):
        """
        Optimize portfolio weights given expected returns and constraints
        
        Parameters:
        expected_returns: Series of expected returns for each instrument
        target_vol: Target portfolio volatility (if None, use mean of target range)
        max_weight: Maximum weight per position (for high conviction trades)
        """
        if target_vol is None:
            target_vol = (self.target_vol_min + self.target_vol_max) / 2
        
        n_assets = len(expected_returns)
        
        # Objective function: maximize Sharpe ratio (minimize negative Sharpe)
        def objective(weights):
            portfolio_return = np.dot(weights, expected_returns.values)
            portfolio_var = np.dot(weights, np.dot(self.covariance_matrix.values, weights))
            portfolio_vol = np.sqrt(portfolio_var)
            
            if portfolio_vol == 0:
                return 1e6
            
            return -portfolio_return / portfolio_vol  # Negative for minimization
        
        # Volatility constraint
        def vol_constraint(weights):
            portfolio_var = np.dot(weights, np.dot(self.covariance_matrix.values, weights))
            portfolio_vol = np.sqrt(portfolio_var)
            return target_vol - portfolio_vol
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Weights sum to 1
            {'type': 'eq', 'fun': vol_constraint}  # Target volatility
        ]
        
        # Bounds: each weight between -max_weight and +max_weight
        bounds = [(-max_weight, max_weight) for _ in range(n_assets)]
        
        # Initial guess: equal weights
        x0 = np.ones(n_assets) / n_assets
        
        # Optimize
        try:
            result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
            if result.success:
                return pd.Series(result.x, index=expected_returns.index)
            else:
                # Fallback to equal weights
                return pd.Series(1/n_assets, index=expected_returns.index)
        except:
            # Fallback to equal weights
            return pd.Series(1/n_assets, index=expected_returns.index)
    
    def calculate_position_sizing(self, theme_conviction, theme_volatility, fund_nav):
        """
        Calculate position size based on theme conviction and risk budget
        
        Parameters:
        theme_conviction: 'high' or 'low' conviction level
        theme_volatility: Annual volatility of the theme
        fund_nav: Current fund NAV
        """
        if theme_conviction == 'high':
            max_risk_pct = 0.10  # 10% max risk for high conviction
            target_risk_pct = 0.07  # Target 7% for optimal diversification
        else:
            max_risk_pct = 0.03  # 3% max risk for exploratory
            target_risk_pct = 0.02  # Target 2%
        
        # Calculate position size to achieve target risk
        daily_vol = theme_volatility / np.sqrt(self.trading_days)
        target_daily_var = target_risk_pct * fund_nav * self.z_score / 100
        
        position_size = target_daily_var / (daily_vol * self.z_score)
        
        return {
            'position_size': position_size,
            'risk_percentage': target_risk_pct,
            'expected_daily_var': target_daily_var / fund_nav
        }
    
    def update_drawdown(self, current_nav, peak_nav):
        """Update drawdown calculations and risk scalar"""
        self.current_drawdown = (peak_nav - current_nav) / peak_nav
        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        
        # Update risk scalar based on drawdown management rules
        self.risk_scalar = self._calculate_risk_scalar()
        
        return {
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'risk_scalar': self.risk_scalar
        }
    
    def _calculate_risk_scalar(self):
        """Calculate risk scalar based on drawdown and recovery"""
        if self.current_drawdown >= 0.10:
            return 0.25  # 25% risk at 10% drawdown
        elif self.current_drawdown >= 0.075:
            return 0.50  # 50% risk at 7.5% drawdown
        elif self.current_drawdown >= 0.05:
            return 0.75  # 75% risk at 5% drawdown
        else:
            # Calculate recovery from maximum drawdown
            if self.max_drawdown > 0:
                recovery_level = 1 - (self.current_drawdown / self.max_drawdown)
                
                if recovery_level >= 1.0:  # Full recovery
                    return 1.0
                elif recovery_level >= 0.75:  # 75% recovered
                    return 0.75
                elif recovery_level >= 0.50:  # 50% recovered
                    return 0.50
                else:
                    return 0.25  # Still in drawdown mode
            else:
                return 1.0  # No drawdown history
    
    def calculate_leverage_metrics(self, positions_df):
        """
        Calculate gross and net leverage
        
        Parameters:
        positions_df: DataFrame with columns ['instrument', 'market_value', 'direction']
        """
        total_long = positions_df[positions_df['market_value'] > 0]['market_value'].sum()
        total_short = abs(positions_df[positions_df['market_value'] < 0]['market_value'].sum())
        fund_nav = abs(positions_df['market_value'].sum())  # Assuming this represents NAV
        
        if fund_nav == 0:
            return {
                'gross_leverage': 0,
                'net_leverage': 0,
                'long_exposure': 0,
                'short_exposure': 0
            }
        
        gross_leverage = (total_long + total_short) / fund_nav
        net_leverage = abs(total_long - total_short) / fund_nav
        
        return {
            'gross_leverage': gross_leverage,
            'net_leverage': net_leverage,
            'long_exposure': total_long,
            'short_exposure': total_short
        }
    
    def stress_test_portfolio(self, weights, stress_scenarios):
        """
        Perform stress testing under various scenarios
        
        Parameters:
        weights: Portfolio weights
        stress_scenarios: Dict of scenario names and corresponding return shocks
        """
        results = {}
        
        for scenario_name, shocks in stress_scenarios.items():
            # Apply shocks to returns
            shocked_returns = pd.Series(shocks, index=self.returns_history.columns)
            portfolio_shock = np.dot(weights.values, shocked_returns.values)
            
            results[scenario_name] = {
                'portfolio_return': portfolio_shock,
                'individual_contributions': weights * shocked_returns
            }
        
        return results
    
    def generate_correlation_heatmap(self, save_path=None):
        """Generate correlation matrix heatmap"""
        plt.figure(figsize=(12, 10))
        sns.heatmap(self.correlation_matrix, annot=True, cmap='RdYlBu_r', center=0,
                    square=True, fmt='.2f', cbar_kws={'shrink': 0.8})
        plt.title('Asset Correlation Matrix')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def backtest_risk_management(self, returns_series, initial_nav=100):
        """
        Backtest the risk management system
        
        Parameters:
        returns_series: Series of portfolio returns
        initial_nav: Starting NAV value
        """
        nav_series = [initial_nav]
        peak_nav = initial_nav
        drawdowns = []
        risk_scalars = []
        
        for ret in returns_series:
            # Calculate new NAV
            new_nav = nav_series[-1] * (1 + ret)
            nav_series.append(new_nav)
            
            # Update peak
            if new_nav > peak_nav:
                peak_nav = new_nav
            
            # Calculate drawdown and risk scalar
            dd_info = self.update_drawdown(new_nav, peak_nav)
            drawdowns.append(dd_info['current_drawdown'])
            risk_scalars.append(dd_info['risk_scalar'])
        
        return pd.DataFrame({
            'nav': nav_series[1:],  # Exclude initial value
            'drawdown': drawdowns,
            'risk_scalar': risk_scalars
        }, index=returns_series.index)


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
        
        # Ensure instruments exist in returns data
        available_instruments = [inst for inst in top_instruments if inst in self.fund.returns_history.columns]
        if not available_instruments:
            raise ValueError(f"No instruments from {top_instruments} found in returns data")
        
        # Get returns for these instruments
        theme_returns = self.fund.returns_history[available_instruments]
        
        # Calculate expected returns based on convictions and momentum
        expected_returns = self._calculate_expected_returns(theme_returns, conviction_series[available_instruments])
        
        # Optimize weights
        try:
            weights = self.fund.optimize_portfolio_weights(
                expected_returns, 
                target_vol=target_vol,
                max_weight=0.40  # Higher concentration allowed within themes
            )
        except:
            # Fall back to conviction-weighted approach
            weights = conviction_series[available_instruments] / conviction_series[available_instruments].sum()
        
        # Calculate theme metrics
        theme_var = self.fund.calculate_portfolio_var(weights)
        theme_correlation = theme_returns.corr()
        
        self.themes[theme_name] = {
            'instruments': available_instruments,
            'weights': weights,
            'convictions': conviction_series[available_instruments],
            'expected_returns': expected_returns,
            'var_metrics': theme_var,
            'correlation_matrix': theme_correlation,
            'target_volatility': target_vol
        }
        
        return self.themes[theme_name]
    
    def _calculate_expected_returns(self, returns_data, convictions, momentum_weight=0.3):
        """Calculate expected returns based on conviction and momentum"""
        # Historical momentum (6-month return or available data)
        momentum_window = min(126, len(returns_data))
        momentum = returns_data.iloc[-momentum_window:].mean() * 252  # Annualized
        
        # Conviction-based expected returns (normalize convictions to 0-1 range)
        if convictions.max() == convictions.min():
            normalized_convictions = pd.Series(0.1, index=convictions.index)
        else:
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
    
    def optimize_theme_allocation(self, fund_target_vol=0.10, max_theme_weight=0.40):
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
        
        n_themes = len(self.themes)
        if n_themes == 1:
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            axes = [axes[0], axes[1], None, None]
        else:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            axes = axes.flatten()
        
        # 1. Theme correlation heatmap
        if len(self.theme_correlations) > 1:
            sns.heatmap(self.theme_correlations, annot=True, cmap='RdYlBu_r', 
                       center=0, ax=axes[0], fmt='.2f')
            axes[0].set_title('Theme Correlations')
        else:
            axes[0].text(0.5, 0.5, 'Need 2+ themes\nfor correlation', 
                        ha='center', va='center', transform=axes[0].transAxes)
            axes[0].set_title('Theme Correlations')
        
        # 2. Theme volatilities
        theme_vols = []
        theme_names = []
        for name, data in self.themes.items():
            theme_vols.append(data['var_metrics']['portfolio_vol_annual'])
            theme_names.append(name)
        
        axes[1].bar(theme_names, theme_vols)
        axes[1].set_title('Theme Volatilities')
        axes[1].set_ylabel('Annual Volatility')
        axes[1].tick_params(axis='x', rotation=45)
        
        if n_themes > 1:
            # 3. Theme VaR contributions
            theme_vars = []
            for name, data in self.themes.items():
                theme_vars.append(data['var_metrics']['var_1day'])
            
            axes[2].bar(theme_names, theme_vars)
            axes[2].set_title('Theme 1-Day VaR (99%)')
            axes[2].set_ylabel('VaR')
            axes[2].tick_params(axis='x', rotation=45)
            
            # 4. Conviction vs Expected Return scatter
            convictions_all = []
            expected_returns_all = []
            theme_labels = []
            
            for name, data in self.themes.items():
                for instrument in data['instruments']:
                    convictions_all.append(data['convictions'][instrument])
                    expected_returns_all.append(data['expected_returns'][instrument])
                    theme_labels.append(name)
            
            if convictions_all and expected_returns_all:
                scatter = axes[3].scatter(convictions_all, expected_returns_all, 
                                        c=range(len(convictions_all)), cmap='viridis', alpha=0.7)
                axes[3].set_xlabel('Conviction Score')
                axes[3].set_ylabel('Expected Return')
                axes[3].set_title('Conviction vs Expected Return')
        
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
            volume_percentile = min(volume_percentile, 1.0)  # Cap at 1.0
            
            # Spread score (lower is better)
            spread_percentile = 1 - (spread_data[instrument] / spread_data.quantile(0.95))
            spread_percentile = max(spread_percentile, 0.0)  # Floor at 0.0
            
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
            
            tier_weight = weights[weights.index.isin(tier_instruments)].sum() if len(tier_instruments) > 0 else 0
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


# Example demonstration of the complete system
def demonstrate_retail_fund():
    """Demonstrate the complete retail sector hedge fund system"""
    print("=== Retail Sector Long/Short Equity Fund Demo ===\n")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
    
    # Retail sector instruments
    instruments = [
        'WMT', 'TGT', 'COST', 'HD', 'LOW', 'AMZN', 'BBY', 'DG',
        'TJX', 'ROST', 'M', 'KSS', 'ULTA', 'LULU', 'NKE'
    ]
    
    # Generate realistic returns with correlations
    n_instruments = len(instruments)
    base_vols = np.random.uniform(0.15, 0.35, n_instruments)
    daily_vols = base_vols / np.sqrt(252)
    
    # Create retail sector correlation matrix (higher correlations)
    correlation_matrix = np.random.rand(n_instruments, n_instruments) * 0.4 + 0.5
    correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
    np.fill_diagonal(correlation_matrix, 1.0)
    
    # Ensure positive definiteness
    eigenvals, eigenvecs = np.linalg.eigh(correlation_matrix)
    eigenvals = np.maximum(eigenvals, 0.01)
    correlation_matrix = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
    
    # Generate correlated returns
    L = np.linalg.cholesky(correlation_matrix)
    random_returns = np.random.normal(0, 1, (len(dates), n_instruments))
    correlated_returns = random_returns @ L.T
    
    # Scale by volatilities
    for i, vol in enumerate(daily_vols):
        correlated_returns[:, i] *= vol
    
    returns_df = pd.DataFrame(correlated_returns, index=dates, columns=instruments)
    
    # Initialize fund
    fund = RetailFund()
    fund.load_market_data(returns_df)
    
    print("1. Fund Initialization Complete")
    print(f"   Loaded {len(instruments)} retail sector stocks")
    print(f"   Data period: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
    
    # Example portfolio
    weights = pd.Series({
        'WMT': 0.15, 'TGT': 0.12, 'COST': 0.10, 'HD': 0.08, 'LOW': 0.05,
        'AMZN': 0.10, 'BBY': -0.10, 'DG': 0.08, 'TJX': 0.06, 'ROST': 0.04,
        'M': -0.05, 'KSS': -0.08, 'ULTA': 0.05, 'LULU': 0.06, 'NKE': 0.04
    })
    
    print("\n2. Portfolio Risk Analysis:")
    var_results = fund.calculate_portfolio_var(weights, method='parametric')
    print(f"   1-Day 99% VaR: {var_results['var_1day']:.4f} ({var_results['var_1day']*100:.2f}%)")
    print(f"   Annual Portfolio Volatility: {var_results['portfolio_vol_annual']:.4f} ({var_results['portfolio_vol_annual']*100:.1f}%)")
    
    # Diversification analysis
    div_analysis = fund.calculate_diversified_vs_undiversified_var(weights)
    print(f"\n3. Diversification Analysis:")
    print(f"   Diversification Benefit: {div_analysis['diversification_benefit']:.2%}")
    
    # Expected Shortfall
    es = fund.calculate_expected_shortfall(weights, method='historical')
    print(f"\n4. Expected Shortfall: {es:.4f} ({es*100:.2f}%)")
    
    # Position sizing example
    fund_nav = 100_000_000  # $100M fund
    high_conv_sizing = fund.calculate_position_sizing('high', 0.20, fund_nav)
    print(f"\n5. Position Sizing (High Conviction, 20% vol):")
    print(f"   Position Size: ${high_conv_sizing['position_size']:,.0f}")
    print(f"   Risk Percentage: {high_conv_sizing['risk_percentage']:.1%}")
    
    # Stress testing
    print("\n6. Stress Test Results:")
    stress_scenarios = {
        'Consumer_Recession': dict(zip(instruments, 
            [-0.25, -0.30, -0.20, -0.35, -0.40, -0.15, -0.45, -0.20,
             -0.35, -0.40, -0.50, -0.55, -0.30, -0.25, -0.20])),
        'E_Commerce_Surge': dict(zip(instruments,
            [-0.15, -0.20, -0.10, -0.05, -0.10, 0.25, -0.30, -0.05,
             -0.15, -0.20, -0.40, -0.45, 0.10, 0.05, 0.00]))
    }
    
    stress_results = fund.stress_test_portfolio(weights, stress_scenarios)
    for scenario, result in stress_results.items():
        print(f"   {scenario}: Portfolio Return = {result['portfolio_return']:.2%}")
    
    # Generate correlation heatmap
    print("\n7. Generating Correlation Matrix Heatmap...")
    fund.generate_correlation_heatmap()
    
    return fund, weights


# Run demonstration
if __name__ == "__main__":
    fund, weights = demonstrate_retail_fund()