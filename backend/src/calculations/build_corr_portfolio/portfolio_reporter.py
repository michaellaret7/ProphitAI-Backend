"""
Portfolio reporting module for correlation-aware portfolio builder.
Handles display and summary generation for portfolio results.
"""

from typing import Dict
import pandas as pd


class PortfolioReporter:
    """Handles portfolio reporting and summary displays."""
    
    def __init__(self, portfolio_value: float, leverage: float = 1.0, max_position_weight: float = 0.10):
        """
        Initialize the portfolio reporter.
        
        Parameters:
        -----------
        portfolio_value : float
            Total portfolio value in dollars
        leverage : float
            Leverage multiplier
        max_position_weight : float
            Maximum weight for any single position
        """
        self.portfolio_value = portfolio_value
        self.leverage = leverage
        self.max_position_weight = max_position_weight
    
    def display_performance_summary(self, metrics: Dict) -> None:
        """
        Display a comprehensive performance summary.
        
        Parameters:
        -----------
        metrics : Dict
            Performance metrics dictionary
        """
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
    
    def display_portfolio_summary(self, weights: Dict[str, float], tickers: Dict[str, Dict],
                                 risk_contributions: Dict[str, float], metrics: Dict,
                                 var_metrics: Dict, price_data: Dict) -> pd.DataFrame:
        """
        Display portfolio allocation summary and return allocation DataFrame.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights
        tickers : Dict[str, Dict]
            Ticker information
        risk_contributions : Dict[str, float]
            Risk contributions by ticker
        metrics : Dict
            Portfolio metrics
        var_metrics : Dict
            VaR metrics
        price_data : Dict
            Price data for volatility calculation
            
        Returns:
        --------
        pd.DataFrame: Allocation details
        """
        from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
        
        portfolio_positions = {}
        total_long_value = 0
        total_short_value = 0
        
        print(f"\nPortfolio Allocation (risk-based):")
        print(f"{'Ticker':<8} {'Position':<8} {'Weight':<10} {'Size':<15} {'Volatility':<10} {'Risk Contrib':<12} {'Note':<8}")
        print("-" * 80)
        
        capped_positions = []
        allocation_data = []
        
        for ticker, weight in weights.items():
            position_size = abs(weight) * self.portfolio_value * self.leverage
            
            # Check if position hit the cap
            is_capped = abs(weight) >= (self.max_position_weight - 0.0001)  # Small tolerance for float comparison
            if is_capped:
                capped_positions.append(ticker)
            
            # Get individual volatility
            if ticker in price_data:
                vol = VolatilityFactors(price_data[ticker]['close']).annualized_volatility(lookback_days=252)
            else:
                vol = 0.0
            
            portfolio_positions[ticker] = {
                'position': tickers[ticker]['position'],
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
            print(f"{ticker:<8} {tickers[ticker]['position']:<8} {weight:>9.2%} ${position_size:>13,.2f} {vol:>9.2%} {risk_contrib:>11.2%} {note:<8}")
            
            # Store data for DataFrame
            allocation_data.append({
                'ticker': ticker,
                'position': tickers[ticker]['position'],
                'weight': weight,
                'position_size': position_size if weight >= 0 else -position_size,
                'volatility': vol,
                'risk_contrib': risk_contrib,
                'capped': is_capped
            })
        
        # Create Portfolio Allocation DataFrame
        allocation_df = pd.DataFrame(allocation_data)
        
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
        
        return allocation_df
