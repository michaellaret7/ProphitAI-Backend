import pandas as pd
import numpy as np
from .risk_model import RiskMetrics
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers

tickers = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'CSCO', 'INTC']

price_df = fetch_bulk_ohlcv_data_for_tickers(tickers, '2012-01-01', '2026-01-31')
price_df = pd.DataFrame({                                                                       
    ticker: df['adj_close'] for ticker, df in price_df.items()                                    
})    

class Portfolio:
    def __init__(self, name, tickers, weights, price_df):

        if len(tickers) != len(weights):
            raise ValueError("Tickers must match the amount of weights")

        self.name = name
        self.tickers = tickers
        self.weights = weights
        self.price_df = price_df
        self.positions = list(zip(tickers, weights))

        # Compute daily returns once, reuse everywhere
        self._daily_returns = self.price_df[self.tickers].pct_change().dropna()

        self.returns = self.calc_cumulative_returns()
        self.portfolio_returns = self.calc_portfolio_returns()

        self.corr: pd.DataFrame = self.corr_matrix()
        self.cov: pd.DataFrame = self.cov_matrix()
        self.volatility: float = self.calc_volatility()
        
        self.risk_metrics: RiskMetrics = self.calc_risk_metrics()

    
    def calc_cumulative_returns(self) -> pd.DataFrame:
        """
        Calculate cumulative returns for each ticker.

        Formula: (1 + daily_return).cumprod() - 1
        """
        return (1 + self._daily_returns).cumprod() - 1

    def calc_portfolio_returns(self) -> pd.Series:
        """Calculate cumulative weighted portfolio returns."""
        return (1 + self._get_daily_portfolio_returns()).cumprod() - 1
    
    def corr_matrix(self) -> pd.DataFrame:
        """Calculate the correlation matrix for the portfolio."""
        return self._daily_returns.corr()

    def cov_matrix(self) -> pd.DataFrame:
        """Calculate the covariance matrix for the portfolio."""
        return self._daily_returns.cov()

    def calc_volatility(self) -> float:
        """
        Calculate annualized portfolio volatility.

        Uses simple returns (not log returns) as they are additive across
        portfolio assets. Annualized using √252 trading days.

        Formula: annual = √(w' x Σ x w) x √252
        """
        weights = np.array(self.weights)
        cov = self.cov.values

        portfolio_var = np.dot(weights, np.dot(cov, weights))
        daily_vol = np.sqrt(portfolio_var)

        return daily_vol * np.sqrt(252)

    def _get_daily_portfolio_returns(self) -> pd.Series:
        """Get daily portfolio returns (not cumulative)."""
        return (self._daily_returns * self.weights).sum(axis=1)

    def _calc_drawdown_series(self) -> pd.Series:
        """Calculate drawdown series from cumulative returns."""
        cumulative = (1 + self._get_daily_portfolio_returns()).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown

    def calc_risk_metrics(self, benchmark_returns: pd.Series | None = None) -> RiskMetrics:
        """
        Calculate comprehensive portfolio risk metrics.

        Args:
            benchmark_returns: Optional daily returns series for beta/tracking error.
                              Typically SPY or market index returns.

        Returns:
            RiskMetrics dataclass with all risk measurements.
        """
        daily_returns = self._get_daily_portfolio_returns()
        drawdown_series = self._calc_drawdown_series()

        # === TIER 1: Essential Risk Metrics ===

        # 1. Volatility (annualized)
        volatility = daily_returns.std() * np.sqrt(252)

        # 2. Maximum Drawdown
        max_drawdown = drawdown_series.min()

        # 3. Value at Risk (Historical VaR)
        var_95 = np.percentile(daily_returns, 5)
        var_99 = np.percentile(daily_returns, 1)

        # 4. Conditional VaR / Expected Shortfall
        cvar_95 = daily_returns[daily_returns <= var_95].mean()
        cvar_99 = daily_returns[daily_returns <= var_99].mean()

        # === TIER 2: Downside-Focused Metrics ===

        # 5. Downside Deviation (semi-deviation)
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(252)

        # 6. Ulcer Index: UI = √(Σ(Drawdown²) / N)
        ulcer_index = np.sqrt((drawdown_series ** 2).mean())

        # 7. Average Drawdown
        in_drawdown = drawdown_series < 0
        drawdown_periods = []
        current_drawdown = []

        for is_dd, dd_val in zip(in_drawdown, drawdown_series):
            if is_dd:
                current_drawdown.append(dd_val)
            elif current_drawdown:
                drawdown_periods.append(min(current_drawdown))
                current_drawdown = []
        if current_drawdown:
            drawdown_periods.append(min(current_drawdown))

        avg_drawdown = np.mean(drawdown_periods) if drawdown_periods else 0.0

        # 8. Average Drawdown Duration (in trading days)
        drawdown_lengths = []
        current_length = 0
        for is_dd in in_drawdown:
            if is_dd:
                current_length += 1
            elif current_length > 0:
                drawdown_lengths.append(current_length)
                current_length = 0
        if current_length > 0:
            drawdown_lengths.append(current_length)

        avg_drawdown_duration = np.mean(drawdown_lengths) if drawdown_lengths else 0.0

        # === TIER 3: Market-Relative Metrics ===
        beta = None
        tracking_error = None

        if benchmark_returns is not None:
            aligned = pd.DataFrame({
                'portfolio': daily_returns,
                'benchmark': benchmark_returns
            }).dropna()

            if len(aligned) > 0:
                # 9. Beta = Cov(Rp, Rm) / Var(Rm)
                cov_pb = aligned['portfolio'].cov(aligned['benchmark'])
                var_b = aligned['benchmark'].var()
                beta = cov_pb / var_b if var_b != 0 else 0.0

                # 10. Tracking Error = Std(Rp - Rm) annualized
                excess_returns = aligned['portfolio'] - aligned['benchmark']
                tracking_error = excess_returns.std() * np.sqrt(252)

        return RiskMetrics(
            volatility=float(volatility),
            max_drawdown=float(max_drawdown),
            var_95=float(var_95),
            var_99=float(var_99),
            cvar_95=float(cvar_95),
            cvar_99=float(cvar_99),
            downside_deviation=float(downside_deviation),
            ulcer_index=float(ulcer_index),
            avg_drawdown=float(avg_drawdown),
            avg_drawdown_duration=float(avg_drawdown_duration),
            beta=float(beta) if beta is not None else None,
            tracking_error=float(tracking_error) if tracking_error is not None else None
        )


tech = Portfolio(
    'Tech', 
    tickers=['AAPL', 'MSFT', 'GOOG', 'AMZN'],
    weights=[0.3, 0.3, 0.2, 0.2],
    price_df=price_df[tickers]
)

chip = Portfolio(
    'Chips',
    tickers=['NVDA', 'INTC', 'CSCO'],
    weights=[0.3, 0.3, 0.4],
    price_df=price_df[tickers]
)

print(f"\n=== {tech.name} Portfolio Risk Metrics ===")
print(tech.risk_metrics)

print(f"\n=== {chip.name} Portfolio Risk Metrics ===")
print(chip.risk_metrics)