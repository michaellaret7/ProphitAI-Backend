from backend.src.repositories.price_data import get_price_data_daily
from datetime import datetime, timedelta
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
import numpy as np
import pandas as pd
from backend.src.data_models.performance_models import PerformanceMetrics

lookback_years = 1.5

class TickerPerformanceMetrics:
    def __init__(self, ticker, price_data=None, market_returns=None, risk_free_rate=0.04/252):  # Daily risk-free rate (4% annual / 252 trading days)
        self.ticker = ticker
        self.risk_free_rate = risk_free_rate
        
        # Accept pre-fetched data or fetch if not provided
        if price_data is not None and not price_data.empty:
            self.price_data = price_data
        else:
            # Get ticker data
            self.price_data = self._get_ticker_data(ticker)

        if self.price_data is None or self.price_data.empty:
            raise ValueError(f"Price data for {ticker} could not be fetched or is empty.")
            
        self.returns_calculator = CalculateTickerReturns(self.price_data)
        self.returns = self.returns_calculator.calculate_daily_total_returns()
        
        # Accept pre-calculated market returns or calculate if not provided
        if market_returns is not None and not market_returns.empty:
            self.market_returns = market_returns
            self.benchmark_returns = self.market_returns  # Use SPY as default benchmark
        else:
            # Get SPY data for market returns
            spy_data = self._get_ticker_data('SPY')
            if spy_data is not None and not spy_data.empty:
                spy_calculator = CalculateTickerReturns(spy_data)
                self.market_returns = spy_calculator.calculate_daily_total_returns()
                self.benchmark_returns = self.market_returns  # Use SPY as default benchmark
            else:
                self.market_returns = None
                self.benchmark_returns = None
    
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Use the function from price_data.py
        data = get_price_data_daily(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
        )
        
        if data is None or data.empty:
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
        if self.returns.empty:
            return 0.0
        cumulative = (1 + self.returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        safe_running_max = np.where(running_max == 0, np.nan, running_max)
        drawdown = (cumulative - safe_running_max) / safe_running_max
        return np.nanmin(drawdown) if not np.all(np.isnan(drawdown)) else 0.0
    
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
        """Calculate annualized Sortino Ratio."""
        if target_return is None:
            target_return = self.risk_free_rate

        excess_returns = self.returns - self.risk_free_rate
        downside_returns = self.returns[self.returns < target_return] - target_return

        if len(downside_returns) == 0:
            return np.inf

        # Annualize the components
        ann_excess_return = np.mean(excess_returns) * 252
        downside_deviation = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)
        
        return ann_excess_return / downside_deviation if downside_deviation != 0 else np.nan

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
        
        # Treynor ratio = (Portfolio Return - Risk-free Rate) / Beta
        excess_return = ann_portfolio_return - ann_risk_free_rate
        return excess_return / portfolio_beta if portfolio_beta != 0 else np.nan

    def information_ratio(self):
        """Calculate Information Ratio (annualized) (requires benchmark returns)."""
        if self.benchmark_returns is None:
            raise ValueError("Benchmark returns required for Information ratio calculation")

        min_len = min(len(self.returns), len(self.benchmark_returns))
        returns = self.returns[:min_len]
        benchmark_returns = self.benchmark_returns[:min_len]

        excess_returns = returns - benchmark_returns
        tracking_error = np.std(excess_returns, ddof=1)
        
        # Annualize both components
        ann_excess_return = np.mean(excess_returns) * 252
        ann_tracking_error = tracking_error * np.sqrt(252)
        
        return ann_excess_return / ann_tracking_error if ann_tracking_error != 0 else np.nan

    def omega_ratio(self, threshold=None):
        """Calculate Omega Ratio."""
        if threshold is None:
            threshold = self.risk_free_rate

        gains = self.returns[self.returns > threshold] - threshold
        losses = threshold - self.returns[self.returns <= threshold]

        if len(losses) == 0:
            return np.inf
        
        sum_losses = np.sum(losses)
        if sum_losses == 0:
            return np.inf # If losses sum to zero, it is infinite gain

        if len(gains) == 0:
            return 0

        return np.sum(gains) / sum_losses

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
        """Calculate Jensen's Alpha (annualized) (requires market returns)."""
        if self.market_returns is None:
            raise ValueError("Market returns required for alpha calculation")

        # Use annualized returns for proper alpha calculation
        ann_portfolio_return = self.annualized_return()
        
        # Calculate annualized market return
        market_total_return = (1 + self.market_returns).prod() - 1
        days = len(self.market_returns)
        ann_market_return = (1 + market_total_return) ** (252/days) - 1 if days > 0 else 0
        
        portfolio_beta = self.beta()
        ann_risk_free_rate = self.risk_free_rate * 252

        expected_return = ann_risk_free_rate + portfolio_beta * (ann_market_return - ann_risk_free_rate)
        return ann_portfolio_return - expected_return

    def upside_capture(self):
        """Calculate Upside Capture Ratio (requires benchmark returns)."""
        if self.benchmark_returns is None:
            raise ValueError("Benchmark returns required for upside capture calculation")

        min_len = min(len(self.returns), len(self.benchmark_returns))
        returns = self.returns[:min_len].reset_index(drop=True)
        benchmark_returns = self.benchmark_returns[:min_len].reset_index(drop=True)

        positive_periods = benchmark_returns > 0
        if not np.any(positive_periods):
            return np.nan

        portfolio_up_returns = returns[positive_periods]
        benchmark_up_returns = benchmark_returns[positive_periods]

        if len(portfolio_up_returns) == 0:
            return 0.0

        portfolio_up_return = (1 + portfolio_up_returns).prod()**(1/len(portfolio_up_returns)) - 1
        benchmark_up_return = (1 + benchmark_up_returns).prod()**(1/len(benchmark_up_returns)) - 1

        return (portfolio_up_return / benchmark_up_return) * 100 if benchmark_up_return != 0 else np.nan

    def downside_capture(self):
        """Calculate Downside Capture Ratio (requires benchmark returns)."""
        if self.benchmark_returns is None:
            raise ValueError("Benchmark returns required for downside capture calculation")

        min_len = min(len(self.returns), len(self.benchmark_returns))
        returns = self.returns[:min_len].reset_index(drop=True)
        benchmark_returns = self.benchmark_returns[:min_len].reset_index(drop=True)

        negative_periods = benchmark_returns < 0
        if not np.any(negative_periods):
            return np.nan

        portfolio_down_returns = returns[negative_periods]
        benchmark_down_returns = benchmark_returns[negative_periods]

        if len(portfolio_down_returns) == 0:
            return 0.0

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
    
    @staticmethod
    def calculate_ticker_capture_ratios(ticker_returns_df: pd.DataFrame, benchmark_ticker: str = 'SPY'):
        """
        Calculate upside/downside capture ratios for all tickers against a benchmark.
        
        :param ticker_returns_df: DataFrame with ticker returns as columns
        :param benchmark_ticker: Ticker to use as benchmark (default: 'SPY')
        :return: Dictionary with capture metrics for each ticker
        """
        if ticker_returns_df.empty:
            return "No ticker data available"
        
        # Determine benchmark
        if benchmark_ticker and benchmark_ticker.upper() in ticker_returns_df.columns:
            benchmark_returns = ticker_returns_df[benchmark_ticker.upper()]
        elif 'SPY' in ticker_returns_df.columns:
            benchmark_returns = ticker_returns_df['SPY']
        else:
            return "No benchmark data available"
        
        if benchmark_returns.empty:
            return "No benchmark data available"
        
        # Calculate capture ratios for each ticker
        ticker_capture_results = {}
        
        for ticker in ticker_returns_df.columns:
            ticker_returns = ticker_returns_df[ticker]
            
            # Align the series and remove NaN values
            aligned_data = pd.DataFrame({
                'fund': ticker_returns,
                'benchmark': benchmark_returns
            }).dropna()
            
            if aligned_data.empty:
                capture_metrics = {
                    'upside_capture': np.nan,
                    'downside_capture': np.nan,
                    'capture_ratio': np.nan,
                    'capture_spread': np.nan
                }
            else:
                fund_aligned = aligned_data['fund']
                benchmark_aligned = aligned_data['benchmark']
                
                # Separate up and down periods based on benchmark performance
                up_periods = benchmark_aligned >= 0
                down_periods = benchmark_aligned < 0
                
                # Calculate upside capture ratio
                if up_periods.sum() > 0:
                    fund_up_returns = fund_aligned[up_periods]
                    benchmark_up_returns = benchmark_aligned[up_periods]
                    
                    fund_up_compound = (1 + fund_up_returns).prod() - 1
                    benchmark_up_compound = (1 + benchmark_up_returns).prod() - 1
                    
                    upside_capture = fund_up_compound / benchmark_up_compound if benchmark_up_compound != 0 else np.nan
                else:
                    upside_capture = np.nan
                    
                # Calculate downside capture ratio
                if down_periods.sum() > 0:
                    fund_down_returns = fund_aligned[down_periods]
                    benchmark_down_returns = benchmark_aligned[down_periods]
                    
                    fund_down_compound = (1 + fund_down_returns).prod() - 1
                    benchmark_down_compound = (1 + benchmark_down_returns).prod() - 1
                    
                    downside_capture = fund_down_compound / benchmark_down_compound if benchmark_down_compound != 0 else np.nan
                else:
                    downside_capture = np.nan
                    
                # Calculate overall capture ratio and spread
                capture_ratio = upside_capture / downside_capture if (downside_capture != 0 and not np.isnan(downside_capture)) else np.nan
                capture_spread = upside_capture - downside_capture if (not np.isnan(upside_capture) and not np.isnan(downside_capture)) else np.nan
                
                capture_metrics = {
                    'upside_capture': upside_capture,
                    'downside_capture': downside_capture,
                    'capture_ratio': capture_ratio,
                    'capture_spread': capture_spread
                }
            
            ticker_capture_results[ticker] = capture_metrics
        
        return ticker_capture_results
    
    def calc_all(self) -> PerformanceMetrics:
        """Calculate all performance metrics and return them as a Pydantic model."""

        def safe_round(value, decimals=4):
            """Safely round a value, returning None if value is None"""
            return round(value, decimals) if value is not None else None

        return PerformanceMetrics(
            annualized_return=safe_round(self.annualized_return()),
            max_drawdown=safe_round(self.max_drawdown()),
            sharpe_ratio=safe_round(self.sharpe_ratio()),
            sortino_ratio=safe_round(self.sortino_ratio()),
            calmar_ratio=safe_round(self.calmar_ratio()),
            treynor_ratio=safe_round(self.treynor_ratio()),
            information_ratio=safe_round(self.information_ratio()),
            omega_ratio=safe_round(self.omega_ratio()),
            sterling_ratio=safe_round(self.sterling_ratio()),
            burke_ratio=safe_round(self.burke_ratio()),
            martin_ratio=safe_round(self.martin_ratio()),
            kappa_ratio=safe_round(self.kappa_ratio()),
            beta=safe_round(self.beta()),
            alpha=safe_round(self.alpha()),
            upside_capture=safe_round(self.upside_capture()),
            downside_capture=safe_round(self.downside_capture()),
            gain_loss_ratio=safe_round(self.gain_loss_ratio()),
            pain_index=safe_round(self.pain_index()),
            win_rate=safe_round(self.win_rate()),
            profit_factor=safe_round(self.profit_factor()),
            tail_ratio=safe_round(self.tail_ratio())
        )

if __name__ == "__main__":
    # Test the performance metrics
    ticker = 'NVDA'  # Use uppercase
    print(f"\nPerformance Metrics for {ticker}")
    print("=" * 50)
    
    metrics_calculator = TickerPerformanceMetrics(ticker)
    all_metrics = metrics_calculator.calc_all()
    
    print(all_metrics.model_dump_json(indent=4))

