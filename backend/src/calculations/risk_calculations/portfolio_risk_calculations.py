import numpy as np
from scipy import stats
from typing import Dict
from datetime import datetime, timedelta
import pandas as pd
from backend.src.repositories.price_data import get_price_data_daily
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns

class PortfolioRiskCalculations:
    """
    Value at Risk (VaR) calculator for portfolio risk management and position sizing
    """
    def __init__(self, confidence_level: float = 0.99, trading_days: int = 252, tickers: list[str] = None):
        """
        Initialize VaR calculator
        
        Parameters:
        -----------
        confidence_level : float
            Confidence level for VaR (e.g., 0.99 for 99%)
        trading_days : int
            Number of trading days per year (default 252)
        tickers : list[str]
            List of tickers to calculate risk for
        """
        self.confidence_level = confidence_level
        self.trading_days = trading_days
        self.z_score = stats.norm.ppf(confidence_level)
        self.tickers = tickers
        # Common z-scores for reference
        self.z_scores = {
            0.90: 1.28,
            0.95: 1.65,
            0.99: 2.33,
            0.995: 2.58,
            0.999: 3.09
        }

        if tickers:
            self.returns_history = self._get_data_and_format()
            self.returns_data = self.returns_history.to_numpy()
            self.correlation_matrix = self.calculate_correlation_matrix()
            self.covariance_matrix = self.calculate_covariance_matrix()
        else:
            self.returns_history = None
            self.returns_data = None
            self.correlation_matrix = None
            self.covariance_matrix = None

    def _get_data_and_format(self) -> pd.DataFrame:
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        # Collect returns for each ticker
        returns_dict = {}
        
        print("Fetching price data and calculating returns...")
        for ticker in self.tickers:
            # Fetch price data
            price_data = get_price_data_daily(
                ticker,
                start_date,
                end_date
            )
            
            if price_data is not None and not price_data.empty:
                # Ensure datetime index
                if 'date' in price_data.columns:
                    price_data['date'] = pd.to_datetime(price_data['date'])
                    price_data.set_index('date', inplace=True)
                
                # Calculate returns
                ticker_calc = CalculateTickerReturns(price_data, ticker)
                daily_returns = ticker_calc.calculate_daily_price_returns()
                
                returns_dict[ticker] = daily_returns
                print(f"{ticker}: {len(daily_returns)} daily returns")
            else:
                print(f"Warning: No data for {ticker}")
        
        # Combine into DataFrame and align dates
        returns_df = pd.DataFrame(returns_dict)
        print(f"\nCombined returns shape before cleaning: {returns_df.shape}")
        
        # Drop any rows with NaN values
        returns_df = returns_df.dropna()
        print(f"Combined returns shape after removing NaN: {returns_df.shape}")

        return returns_df

    def _get_weights_and_volatilities(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Get weights and volatilities for the portfolio
        """
        weights = np.array([1/len(self.tickers)] * len(self.tickers))
        volatilities = np.std(self.returns_data, axis=0) * np.sqrt(self.trading_days)

        return weights, volatilities

    def calculate_var(self, portfolio_value: float, annual_volatility: float, time_horizon: int = 1) -> Dict[str, float]:
        """
        Calculate Value at Risk for a portfolio
        
        Parameters:
        -----------
        portfolio_value : float
            Total portfolio value in dollars
        annual_volatility : float
            Target annual volatility (e.g., 0.10 for 10%)
        time_horizon : int
            Time horizon in days (default 1 for daily VaR)
            
        Returns:
        --------
        dict : Dictionary containing VaR metrics
        """
        # Convert annual volatility to daily
        daily_volatility = annual_volatility / np.sqrt(self.trading_days)
        
        # Adjust for time horizon
        period_volatility = daily_volatility * np.sqrt(time_horizon)
        
        # Calculate VaR
        var_percentage = self.z_score * period_volatility
        var_dollars = portfolio_value * var_percentage
        
        return {
            'var_percentage': float(var_percentage),
            'var_dollars': float(var_dollars)
        }

    def calculate_var_with_correlation(self, weights: np.ndarray, volatilities: np.ndarray, correlation_matrix: np.ndarray, portfolio_value: float) -> Dict[str, float]:
        """
        Calculate portfolio VaR considering correlations
        
        Parameters:
        -----------
        weights : np.ndarray
            Array of position weights (should sum to 1)
        volatilities : np.ndarray
            Array of annual volatilities for each position
        correlation_matrix : np.ndarray
            Correlation matrix between positions
        portfolio_value : float
            Total portfolio value
            
        Returns:
        --------
        dict : Portfolio VaR metrics including diversification benefit
        """
        # Convert annual vols to daily
        daily_vols = volatilities / np.sqrt(self.trading_days)
        
        # Create covariance matrix
        # Cov = D * R * D where D is diagonal matrix of volatilities
        D = np.diag(daily_vols)
        covariance_matrix = D @ correlation_matrix @ D
        
        # Portfolio variance
        portfolio_variance = weights @ covariance_matrix @ weights.T
        portfolio_vol = np.sqrt(portfolio_variance)
        
        # Diversified VaR
        diversified_var_pct = self.z_score * portfolio_vol
        diversified_var_dollars = portfolio_value * diversified_var_pct
        
        # Undiversified VaR (sum of individual VaRs)
        individual_vars = np.abs(weights) * daily_vols * self.z_score
        undiversified_var_pct = np.sum(individual_vars)
        undiversified_var_dollars = portfolio_value * undiversified_var_pct
        
        # Diversification benefit
        diversification_benefit = (undiversified_var_dollars - diversified_var_dollars) / undiversified_var_dollars
        
        return {
            'portfolio_daily_vol': portfolio_vol,
            'portfolio_annual_vol': portfolio_vol * np.sqrt(self.trading_days),
            'diversified_var_pct': diversified_var_pct,
            'diversified_var_dollars': diversified_var_dollars,
            'undiversified_var_pct': undiversified_var_pct,
            'undiversified_var_dollars': undiversified_var_dollars,
            'diversification_benefit': diversification_benefit,
            'diversification_ratio': diversified_var_dollars / undiversified_var_dollars
        }
    
    def calculate_parametric_var(self, weights: np.ndarray) -> Dict[str, float]:
        """Parametric VaR calculation assuming normal distribution"""
        if isinstance(weights, pd.Series):
            weights = weights.values
        
        portfolio_variance = np.dot(weights, np.dot(self.covariance_matrix.values, weights))
        portfolio_vol = np.sqrt(portfolio_variance)
        
        daily_vol = portfolio_vol / np.sqrt(self.trading_days)
        
        var_1day = self.z_score * daily_vol
        
        return {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(self.trading_days),
            'portfolio_vol_annual': portfolio_vol,
            'portfolio_vol_daily': daily_vol
        }

    def calculate_historical_var(self, weights: np.ndarray) -> Dict[str, float]:
        """Historical simulation VaR"""
        portfolio_returns = (self.returns_history * weights).sum(axis=1)
        
        var_1day = -np.percentile(portfolio_returns, (1 - self.confidence_level) * 100)
        
        return {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(self.trading_days),
            'portfolio_vol_annual': portfolio_returns.std() * np.sqrt(self.trading_days),
            'portfolio_vol_daily': portfolio_returns.std()
        }

    def calculate_monte_carlo_var(self, weights: np.ndarray, n_simulations=10000) -> Dict[str, float]:
        """Monte Carlo VaR simulation"""
        mean_returns = self.returns_history.mean().values
        
        L = np.linalg.cholesky(self.covariance_matrix.values / self.trading_days)
        
        random_normals = np.random.normal(0, 1, (n_simulations, len(weights)))
        simulated_returns = mean_returns + np.dot(random_normals, L.T)
        
        portfolio_returns = np.dot(simulated_returns, weights)
        
        var_1day = -np.percentile(portfolio_returns, (1 - self.confidence_level) * 100)
        
        return {
            'var_1day': var_1day,
            'var_annual': var_1day * np.sqrt(self.trading_days),
            'portfolio_vol_annual': portfolio_returns.std() * np.sqrt(self.trading_days),
            'portfolio_vol_daily': portfolio_returns.std()
        }

    def calculate_covariance_matrix(self, window=252) -> pd.DataFrame:
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
        R = self.correlation_matrix
        
        # Calculate covariance matrix
        covariance_matrix = pd.DataFrame(
            np.dot(np.dot(D, R), D),
            index=self.returns_history.columns,
            columns=self.returns_history.columns
        )
        
        return covariance_matrix

    def calculate_diversified_vs_undiversified_var(self, weights):
        """Compare diversified vs undiversified VaR to measure diversification benefit"""
        if isinstance(weights, pd.Series):
            weights = weights.values
            
        # Diversified VaR (portfolio approach)
        diversified_var = self.calculate_parametric_var(weights)['var_1day']
        
        # Undiversified VaR (sum of individual VaRs)
        individual_vols = np.sqrt(np.diag(self.covariance_matrix.values)) / np.sqrt(self.trading_days)
        undiversified_var = np.sum(np.abs(weights) * individual_vols * self.z_score)
        
        diversification_benefit = (undiversified_var - diversified_var) / undiversified_var
        
        return {
            'diversified_var': diversified_var,
            'undiversified_var': undiversified_var,
            'diversification_benefit': diversification_benefit
        }

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

    def calculate_correlation_matrix(self, rowvar: bool = False) -> np.ndarray:
        """
        Calculate Pearson correlation matrix from returns data
        
        Parameters:
        -----------
        returns_data : np.ndarray
            2D array of returns data. Shape should be (n_observations, n_assets) if rowvar=False,
            or (n_assets, n_observations) if rowvar=True
        rowvar : bool
            If False (default), each column represents a variable/asset with observations in rows.
            If True, each row represents a variable/asset with observations in columns.
            
        Returns:
        --------
        np.ndarray : Correlation matrix where element [i,j] is the correlation between asset i and asset j
        
        Raises:
        -------
        ValueError : If input data has issues (not 2D, contains NaN, or has zero variance columns)
        """
    
        # Validate input
        if not isinstance(self.returns_data, np.ndarray):
            self.returns_data = np.array(self.returns_data)
            
        if self.returns_data.ndim != 2:
            raise ValueError(f"Input data must be 2D array, got {self.returns_data.ndim}D")
            
        # Check for NaN values
        if np.any(np.isnan(self.returns_data)):
            raise ValueError("Input data contains NaN values")
            
        correlation_matrix = np.corrcoef(self.returns_data, rowvar=rowvar)
        
        # Validate output
        if np.any(np.isnan(correlation_matrix)):
            # This can happen if a column has zero variance
            raise ValueError("Correlation matrix contains NaN values. Check for constant columns in input data.")
            
        return correlation_matrix
    
    def calculate_expected_shortfall(self, weights: np.ndarray, method='historical'):
        """Calculate Expected Shortfall (Conditional VaR)"""
        if method == 'historical':
            portfolio_returns = (self.returns_data * weights).sum(axis=1)
            var_threshold = -np.percentile(portfolio_returns, (1 - self.confidence_level) * 100)
            
            # Expected shortfall is average of losses beyond VaR
            tail_losses = portfolio_returns[portfolio_returns <= -var_threshold]
            expected_shortfall = -tail_losses.mean() if len(tail_losses) > 0 else var_threshold
            
        elif method == 'parametric':
            # For normal distribution: ES = σ * φ(Φ^(-1)(α)) / (1-α)
            # where φ is PDF and Φ is CDF
            portfolio_vol_daily = self.calculate_parametric_var(weights)['portfolio_vol_daily']
            alpha = 1 - self.confidence_level
            
            expected_shortfall = portfolio_vol_daily * stats.norm.pdf(stats.norm.ppf(alpha)) / alpha
        
        return expected_shortfall
    
    
# Test correlation matrix with actual data
if __name__ == "__main__":
    fund_size = 100_000
    target_vol = 0.10
    tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    calc = PortfolioRiskCalculations(tickers=tickers)

    # Use equal weights for demonstration
    weights = np.array([1/len(tickers)] * len(tickers))

    # --- Parametric VaR ---
    calculate_parametric_var = calc.calculate_parametric_var(weights)
    print("\n--- Parametric VaR ---")
    print(calculate_parametric_var)

    # --- Historical VaR ---
    historical_var = calc.calculate_historical_var(weights)
    print("\n--- Historical VaR ---")
    print(historical_var)

    # --- Monte Carlo VaR ---
    monte_carlo_var = calc.calculate_monte_carlo_var(weights)
    print("\n--- Monte Carlo VaR ---")
    print(monte_carlo_var)

    # --- Expected Shortfall ---
    es_historical = calc.calculate_expected_shortfall(weights, method='historical')
    es_parametric = calc.calculate_expected_shortfall(weights, method='parametric')
    print("\n--- Expected Shortfall ---")
    print(f"Historical ES: {es_historical:.4f}")
    print(f"Parametric ES: {es_parametric:.4f}")

    # --- VaR with Correlation ---
    _, volatilities = calc._get_weights_and_volatilities()
    portfolio_value = 1_000_000
    
    var_results = calc.calculate_var_with_correlation(
        weights=weights,
        volatilities=volatilities,
        correlation_matrix=calc.correlation_matrix,
        portfolio_value=portfolio_value
    )
    print("\n--- VaR with Correlation ---")
    print(var_results)

    # --- Diversification Analysis ---
    diversification_analysis = calc.calculate_diversified_vs_undiversified_var(weights)
    print("\n--- Diversification Analysis ---")
    print(diversification_analysis)

    # --- Marginal VaR ---
    marginal_var, component_var = calc.calculate_marginal_var(weights)
    print("\n--- Marginal VaR ---")
    print(marginal_var)
    print("\n--- Component VaR ---")
    print(component_var)

    print(calc.calculate_covariance_matrix())





