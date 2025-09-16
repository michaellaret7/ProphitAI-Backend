import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.linalg import sqrtm
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class GlobalMacroFund:
    """
    Global Macro Hedge Fund Risk Management and Portfolio Construction System
    """
    
    def __init__(self, target_vol_min=0.07, target_vol_max=0.15, confidence_level=0.99):
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
            self.correlation_matrix = ewm_corr.iloc[-len(self.returns_history.columns):, :]
        else:
            self.correlation_matrix = self.returns_history.rolling(window=window).corr().iloc[-1]
            
        return self.correlation_matrix
    
    def calculate_covariance_matrix(self, window=252):
        """
        Calculate covariance matrix: Σ = DRD where D is volatility diagonal matrix
        """
        # Calculate volatilities
        volatilities = self.returns_history.rolling(window=window).std().iloc[-1] * np.sqrt(self.trading_days)
        
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
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if result.success:
            optimal_weights = pd.Series(result.x, index=expected_returns.index)
            return optimal_weights
        else:
            raise ValueError(f"Optimization failed: {result.message}")
    
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
        if self.current_drawdown >= 0.075:
            risk_scalar = 0.75  # Cut risk by 25% at 7.5% drawdown
           
            if self.current_drawdown >= 0.10:
                risk_scalar = 0.375  # Cut risk in half again (75% * 50% = 37.5%)
               
                if self.current_drawdown >= 0.15:
                    risk_scalar = 0.0  # All risk cut at 15% drawdown
           
            return risk_scalar
       
        # Calculate recovery from maximum drawdown
        recovery_level = 1 - (self.current_drawdown / self.max_drawdown) if self.max_drawdown > 0 else 1
       
        if recovery_level >= 1.0:  # Full recovery
            return 1.0
        elif recovery_level >= 0.75:  # 75% recovered
            return 0.75
        elif recovery_level >= 0.50:  # 50% recovered
            return 0.50
        else:
            return 0.5  # Still in drawdown mode
    
    def calculate_leverage_metrics(self, positions_df):
        """
        Calculate gross and net leverage
        
        Parameters:
        positions_df: DataFrame with columns ['instrument', 'market_value', 'direction']
        """
        total_long = positions_df[positions_df['market_value'] > 0]['market_value'].sum()
        total_short = abs(positions_df[positions_df['market_value'] < 0]['market_value'].sum())
        fund_nav = positions_df['market_value'].sum()  # Assuming this represents NAV
        
        gross_leverage = (total_long + total_short) / abs(fund_nav)
        net_leverage = abs(total_long - total_short) / abs(fund_nav)
        
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


# Example usage and demonstration
def demonstrate_fund_calculations():
    """Demonstrate the key calculations with sample data"""
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
    
    # Sample instruments
    instruments = [
        'SPY', 'EFA', 'EEM', 'TLT', 'HYG', 'GLD', 'DXY', 'CRUDE_OIL'
    ]
    
    # Generate correlated returns
    base_vols = [0.16, 0.18, 0.25, 0.12, 0.08, 0.20, 0.10, 0.35]  # Annual volatilities
    daily_vols = [vol / np.sqrt(252) for vol in base_vols]
    
    # Create correlation structure
    correlation = np.array([
        [1.00, 0.75, 0.65, -0.30, 0.20, -0.10, -0.15, 0.05],
        [0.75, 1.00, 0.70, -0.25, 0.25, -0.05, -0.20, 0.10],
        [0.65, 0.70, 1.00, -0.20, 0.35, 0.00, -0.10, 0.15],
        [-0.30, -0.25, -0.20, 1.00, -0.40, 0.30, 0.10, -0.05],
        [0.20, 0.25, 0.35, -0.40, 1.00, -0.15, -0.05, 0.20],
        [-0.10, -0.05, 0.00, 0.30, -0.15, 1.00, 0.05, 0.25],
        [-0.15, -0.20, -0.10, 0.10, -0.05, 0.05, 1.00, 0.30],
        [0.05, 0.10, 0.15, -0.05, 0.20, 0.25, 0.30, 1.00]
    ])
    
    # Generate multivariate normal returns
    L = np.linalg.cholesky(correlation)
    random_returns = np.random.normal(0, 1, (len(dates), len(instruments)))
    correlated_returns = np.dot(random_returns, L.T)
    
    # Scale by volatilities
    for i, vol in enumerate(daily_vols):
        correlated_returns[:, i] *= vol
    
    # Create returns DataFrame
    returns_df = pd.DataFrame(correlated_returns, index=dates, columns=instruments)
    
    # Initialize fund
    fund = GlobalMacroFund()
    fund.load_market_data(returns_df)
    
    # Example portfolio weights (high conviction themes)
    weights = pd.Series([0.15, 0.10, 0.08, 0.12, 0.05, 0.08, 0.20, 0.22], 
                       index=instruments)
    
    print("=== Global Macro Fund Risk Analysis ===\n")
    
    # 1. Portfolio VaR Analysis
    print("1. Portfolio VaR Analysis:")
    var_results = fund.calculate_portfolio_var(weights, method='parametric')
    print(f"   1-Day 99% VaR: {var_results['var_1day']:.4f} ({var_results['var_1day']*100:.2f}%)")
    print(f"   Annual Portfolio Volatility: {var_results['portfolio_vol_annual']:.4f} ({var_results['portfolio_vol_annual']*100:.1f}%)")
    print(f"   Daily Portfolio Volatility: {var_results['portfolio_vol_daily']:.4f} ({var_results['portfolio_vol_daily']*100:.2f}%)")
    
    # 2. Diversification Analysis
    print("\n2. Diversification Analysis:")
    div_analysis = fund.calculate_diversified_vs_undiversified_var(weights)
    print(f"   Diversified VaR: {div_analysis['diversified_var']:.4f}")
    print(f"   Undiversified VaR: {div_analysis['undiversified_var']:.4f}")
    print(f"   Diversification Benefit: {div_analysis['diversification_benefit']:.2%}")
    
    # 3. Expected Shortfall
    print("\n3. Expected Shortfall (Conditional VaR):")
    es = fund.calculate_expected_shortfall(weights, method='historical')
    print(f"   Expected Shortfall: {es:.4f} ({es*100:.2f}%)")
    
    # 4. Marginal VaR Analysis
    print("\n4. Marginal VaR Contributions:")
    marginal_var, component_var = fund.calculate_marginal_var(weights)
    for instrument in instruments:
        print(f"   {instrument}: Component VaR = {component_var[instrument]:.4f}")
    
    # 5. Position Sizing Example
    print("\n5. Position Sizing Examples:")
    fund_nav = 100_000_000  # $100M fund
    
    # High conviction theme
    high_conv_sizing = fund.calculate_position_sizing('high', 0.20, fund_nav)
    print(f"   High Conviction Theme (20% vol): ${high_conv_sizing['position_size']:,.0f}")
    print(f"   Risk Percentage: {high_conv_sizing['risk_percentage']:.1%}")
    
    # Low conviction theme
    low_conv_sizing = fund.calculate_position_sizing('low', 0.15, fund_nav)
    print(f"   Low Conviction Theme (15% vol): ${low_conv_sizing['position_size']:,.0f}")
    print(f"   Risk Percentage: {low_conv_sizing['risk_percentage']:.1%}")
    
    # 6. Stress Testing
    print("\n6. Stress Test Results:")
    stress_scenarios = {
        '2008_Crisis': [-0.20, -0.25, -0.35, 0.15, -0.15, 0.10, 0.05, -0.40],
        'COVID_Shock': [-0.30, -0.28, -0.40, 0.20, -0.20, 0.05, -0.02, -0.50],
        'Rate_Shock': [-0.05, -0.08, -0.10, -0.25, -0.10, -0.02, 0.15, 0.05]
    }
    
    stress_results = fund.stress_test_portfolio(weights, stress_scenarios)
    for scenario, result in stress_results.items():
        print(f"   {scenario}: Portfolio Return = {result['portfolio_return']:.2%}")
    
    # 7. Generate correlation heatmap
    print("\n7. Generating Correlation Matrix Heatmap...")
    fund.generate_correlation_heatmap()

    # Calculate portfolio returns using weights
    portfolio_returns = (returns_df * weights).sum(axis=1)
    
    print("8. Risk Management Backtest Results:")
    backtest_results = fund.backtest_risk_management(returns_series=portfolio_returns)
    print(f"Final NAV: {backtest_results['nav'].iloc[-1]:.2f}")
    print(f"Max Drawdown: {backtest_results['drawdown'].min():.2%}")
    print(f"Avg Risk Scalar: {backtest_results['risk_scalar'].mean():.2f}")
    print(f"Min Risk Scalar: {backtest_results['risk_scalar'].min():.2f}")
    
    return fund, weights, returns_df

# Run demonstration
if __name__ == "__main__":
    fund, weights, returns_df = demonstrate_fund_calculations()