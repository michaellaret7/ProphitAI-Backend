from backend.src.repositories.market_data.cached_ticker_repository import get_cached_ticker_data
from datetime import datetime, timedelta
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
import numpy as np
from backend.src.data_models.performance_models import PerformanceMetrics

lookback_years = 1.5

class TickerPerformanceMetrics:
    def __init__(self, ticker, risk_free_rate=0.04/252):  # Daily risk-free rate (4% annual / 252 trading days)
        self.ticker = ticker
        self.risk_free_rate = risk_free_rate
        
        # Get ticker data
        self.price_data = self._get_ticker_data(ticker)
        self.returns_calculator = CalculateTickerReturns(self.price_data)
        self.returns = self.returns_calculator.calculate_daily_total_returns()
        
        # Get SPY data for market returns
        spy_data = self._get_ticker_data('SPY')
        if spy_data is not None:
            spy_calculator = CalculateTickerReturns(spy_data)
            self.market_returns = spy_calculator.calculate_daily_total_returns()
            self.benchmark_returns = self.market_returns  # Use SPY as default benchmark
        else:
            self.market_returns = None
            self.benchmark_returns = None
    
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Convert dates to ISO format strings for caching (hashable)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Use the cached function
        data = get_cached_ticker_data(
            ticker=ticker,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d"
        )
        
        if data is None:
            return None

        return data
    
    # Helper methods needed by the performance metrics
    def annualized_return(self):
        """Calculate annualized return."""
        if len(self.returns) == 0:
            return 0.0
        total_return = (1 + self.returns).prod() - 1
        days = len(self.returns)
        return (1 + total_return) ** (252/days) - 1
    
    def max_drawdown(self):
        """Calculate maximum drawdown."""
        cumulative = (1 + self.returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def beta(self):
        """Calculate beta against market returns."""
        if self.market_returns is None:
            raise ValueError("Market returns required for beta calculation")
        
        min_len = min(len(self.returns), len(self.market_returns))
        returns = self.returns[:min_len]
        market_returns = self.market_returns[:min_len]
        
        covariance = np.cov(returns, market_returns)[0, 1]
        market_variance = np.var(market_returns, ddof=1)
        return covariance / market_variance if market_variance != 0 else np.nan
    
    def pain_index(self):
        """Calculate pain index."""
        cumulative = (1 + self.returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        return np.mean(drawdowns**2)
    
    # Performance metric methods
    def sharpe_ratio(self, trading_days=252):
        """Calculate annualized Sharpe Ratio."""
        excess_returns = self.returns - self.risk_free_rate
        daily_sharpe = np.mean(excess_returns) / np.std(excess_returns, ddof=1) if np.std(excess_returns, ddof=1) != 0 else np.nan
        return daily_sharpe * np.sqrt(trading_days)

    def sortino_ratio(self, target_return=None):
        """Calculate Sortino Ratio."""
        if target_return is None:
            target_return = self.risk_free_rate

        excess_returns = self.returns - self.risk_free_rate
        downside_returns = self.returns[self.returns < target_return] - target_return

        if len(downside_returns) == 0:
            return np.inf

        downside_deviation = np.sqrt(np.mean(downside_returns**2))
        return np.mean(excess_returns) / downside_deviation if downside_deviation != 0 else np.nan

    def calmar_ratio(self):
        """Calculate Calmar Ratio."""
        ann_return = self.annualized_return()
        max_dd = abs(self.max_drawdown())
        return ann_return / max_dd if max_dd != 0 else np.inf

    def treynor_ratio(self, trading_days=252):
        """Calculate annualized Treynor Ratio."""
        if self.market_returns is None:
            raise ValueError("Market returns required for Treynor ratio calculation")

        ann_portfolio_return = self.annualized_return()
        ann_risk_free_rate = self.risk_free_rate * trading_days
        portfolio_beta = self.beta()
        
        excess_return = ann_portfolio_return - ann_risk_free_rate
        return excess_return / portfolio_beta if portfolio_beta != 0 else np.nan

    def information_ratio(self):
        """Calculate Information Ratio (requires benchmark returns)."""
        if self.benchmark_returns is None:
            raise ValueError("Benchmark returns required for Information ratio calculation")

        min_len = min(len(self.returns), len(self.benchmark_returns))
        returns = self.returns[:min_len]
        benchmark_returns = self.benchmark_returns[:min_len]

        excess_returns = returns - benchmark_returns
        tracking_error = np.std(excess_returns, ddof=1)
        return np.mean(excess_returns) / tracking_error if tracking_error != 0 else np.nan

    def omega_ratio(self, threshold=None):
        """Calculate Omega Ratio."""
        if threshold is None:
            threshold = self.risk_free_rate

        gains = self.returns[self.returns > threshold] - threshold
        losses = threshold - self.returns[self.returns <= threshold]

        if len(losses) == 0:
            return np.inf
        if len(gains) == 0:
            return 0

        return np.sum(gains) / np.sum(losses)

    def sterling_ratio(self):
        """Calculate Sterling Ratio."""
        ann_return = self.annualized_return()
        max_dd = abs(self.max_drawdown())
        adjusted_drawdown = max_dd * 1.1  # Sterling ratio adjustment
        return ann_return / adjusted_drawdown if adjusted_drawdown != 0 else np.inf

    def burke_ratio(self):
        """Calculate Burke Ratio."""
        ann_return = self.annualized_return()
        cumulative = (1 + self.returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        sum_squared_drawdowns = np.sum(drawdowns**2)
        return ann_return / np.sqrt(sum_squared_drawdowns) if sum_squared_drawdowns != 0 else np.inf

    def martin_ratio(self):
        """Calculate Martin Ratio (Ulcer Performance Index)."""
        ann_return = self.annualized_return()
        ulcer_index = np.sqrt(self.pain_index())
        return ann_return / ulcer_index if ulcer_index != 0 else np.inf

    def kappa_ratio(self, target_return=None, moment=3):
        """Calculate Kappa Ratio."""
        if target_return is None:
            target_return = self.risk_free_rate

        excess_returns = self.returns - target_return
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return np.inf

        lpm = np.mean(np.abs(downside_returns)**moment)**(1/moment)
        return np.mean(excess_returns) / lpm if lpm != 0 else np.nan

    # ALPHA AND CAPTURE METRICS
    def alpha(self):
        """Calculate Jensen's Alpha (requires market returns)."""
        if self.market_returns is None:
            raise ValueError("Market returns required for alpha calculation")

        min_len = min(len(self.returns), len(self.market_returns))
        returns = self.returns[:min_len]
        market_returns = self.market_returns[:min_len]

        portfolio_return = np.mean(returns)
        market_return = np.mean(market_returns)
        portfolio_beta = self.beta()

        expected_return = self.risk_free_rate + portfolio_beta * (market_return - self.risk_free_rate)
        return portfolio_return - expected_return

    def upside_capture(self):
        """Calculate Upside Capture Ratio (requires benchmark returns)."""
        if self.benchmark_returns is None:
            raise ValueError("Benchmark returns required for upside capture calculation")

        min_len = min(len(self.returns), len(self.benchmark_returns))
        returns = self.returns[:min_len]
        benchmark_returns = self.benchmark_returns[:min_len]

        positive_periods = benchmark_returns > 0
        if not np.any(positive_periods):
            return np.nan

        portfolio_up_returns = returns[positive_periods]
        benchmark_up_returns = benchmark_returns[positive_periods]

        portfolio_up_return = (1 + portfolio_up_returns).prod()**(1/len(portfolio_up_returns)) - 1
        benchmark_up_return = (1 + benchmark_up_returns).prod()**(1/len(benchmark_up_returns)) - 1

        return (portfolio_up_return / benchmark_up_return) * 100 if benchmark_up_return != 0 else np.nan

    def downside_capture(self):
        """Calculate Downside Capture Ratio (requires benchmark returns)."""
        if self.benchmark_returns is None:
            raise ValueError("Benchmark returns required for downside capture calculation")

        min_len = min(len(self.returns), len(self.benchmark_returns))
        returns = self.returns[:min_len]
        benchmark_returns = self.benchmark_returns[:min_len]

        negative_periods = benchmark_returns < 0
        if not np.any(negative_periods):
            return np.nan

        portfolio_down_returns = returns[negative_periods]
        benchmark_down_returns = benchmark_returns[negative_periods]

        portfolio_down_return = (1 + portfolio_down_returns).prod()**(1/len(portfolio_down_returns)) - 1
        benchmark_down_return = (1 + benchmark_down_returns).prod()**(1/len(benchmark_down_returns)) - 1

        return (portfolio_down_return / benchmark_down_return) * 100 if benchmark_down_return != 0 else np.nan

    def gain_loss_ratio(self):
        """Calculate Gain-Loss Ratio."""
        gains = self.returns[self.returns > 0]
        losses = self.returns[self.returns < 0]

        if len(gains) == 0 or len(losses) == 0:
            return np.nan

        avg_gain = np.mean(gains)
        avg_loss = abs(np.mean(losses))
        return avg_gain / avg_loss if avg_loss != 0 else np.inf
    
    def win_rate(self):
        """Calculate the Win Rate (Hit Rate)."""
        if len(self.returns) == 0:
            return 0.0
        win_rate = (np.sum(self.returns > 0) / len(self.returns)) * 100
        return win_rate

    def profit_factor(self):
        """Calculate the Profit Factor."""
        if len(self.returns) == 0:
            return 0.0
        
        gross_profits = np.sum(self.returns[self.returns > 0])
        gross_losses = np.abs(np.sum(self.returns[self.returns < 0]))
        
        if gross_losses == 0:
            return np.inf
        
        profit_factor = gross_profits / gross_losses
        return profit_factor

    def tail_ratio(self, percentile: float = 0.05):
        """Calculate the Tail Ratio."""
        if len(self.returns) == 0:
            return 1.0
        
        upper_tail = np.percentile(self.returns, (1 - percentile) * 100)
        lower_tail = np.abs(np.percentile(self.returns, percentile * 100))
        
        if lower_tail == 0:
            return np.inf
        
        tail_ratio = upper_tail / lower_tail
        return tail_ratio
    
    def calc_all(self) -> PerformanceMetrics:
        """Calculate all performance metrics and return them as a Pydantic model."""
        return PerformanceMetrics(
            annualized_return=self.annualized_return(),
            max_drawdown=self.max_drawdown(),
            sharpe_ratio=self.sharpe_ratio(),
            sortino_ratio=self.sortino_ratio(),
            calmar_ratio=self.calmar_ratio(),
            treynor_ratio=self.treynor_ratio(),
            information_ratio=self.information_ratio(),
            omega_ratio=self.omega_ratio(),
            sterling_ratio=self.sterling_ratio(),
            burke_ratio=self.burke_ratio(),
            martin_ratio=self.martin_ratio(),
            kappa_ratio=self.kappa_ratio(),
            beta=self.beta(),
            alpha=self.alpha(),
            upside_capture=self.upside_capture(),
            downside_capture=self.downside_capture(),
            gain_loss_ratio=self.gain_loss_ratio(),
            pain_index=self.pain_index(),
            win_rate=self.win_rate(),
            profit_factor=self.profit_factor(),
            tail_ratio=self.tail_ratio()
        )

if __name__ == "__main__":
    # Test the performance metrics
    ticker = 'nvda'
    print(f"\nPerformance Metrics for {ticker}")
    print("=" * 50)
    
    metrics_calculator = TickerPerformanceMetrics(ticker)
    all_metrics = metrics_calculator.calc_all()
    
    print(all_metrics.model_dump_json(indent=4))

