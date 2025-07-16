from backend.src.repositories.portfolio_data import retrieve_portfolio
from backend.src.calculations.returns_calculations.portfolio_returns_calculations import CalculatePortfolioReturns
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from backend.src.utils.logging_config import init_logger
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import PortfolioPerformanceCalculations
from backend.src.calculations.risk_calculations.portfolio_risk_calculations import PortfolioRiskCalculations

logger = init_logger(__name__)

class PhaseOneFormatting:
    def __init__(self, email: str):
        self.email = email
        self.portfolio = retrieve_portfolio(email=email, is_current=True)
        self.start_date = datetime.now() - timedelta(days=365*4)
        self.end_date = datetime.now()

        portfolio_positions = []
        for position in self.portfolio:
            portfolio_positions.append({
                'ticker': position['ticker'],
                'allocation': position['allocation'],
                'sector': position.get('sector', 'Unknown'),
                'industry': position.get('industry', 'Unknown'),
                'sub_industry': position.get('sub_industry', 'Unknown')
            })
        
        self.total_output = {
            'portfolio_positions': portfolio_positions,
        }
        
    def calculate_portfolio_returns(self):
        """
        Calculate portfolio returns using the CalculatePortfolioReturns class.
        """
        # Convert portfolio list to dictionary format {ticker: weight}
        tickers_weights = {}
        for position in self.portfolio:
            # Convert allocation percentage to decimal weight
            tickers_weights[position['ticker']] = float(position['allocation']) / 100.0
        
        portfolio_calculator = CalculatePortfolioReturns(
            tickers_weights=tickers_weights,
            start_date=self.start_date.strftime('%Y-%m-%d'),
            end_date=self.end_date.strftime('%Y-%m-%d')
        )

        portfolio_returns = {
            'Annualized Price Return (%)': str(round(portfolio_calculator.calculate_annualized_price_return()*100, 2)),
            'Annualized Total Return (%)': str(round(portfolio_calculator.calculate_annualized_total_return()*100, 2)),
            'Holding Period Return (%)': str(round(portfolio_calculator.calculate_holding_period_return()*100, 2)),
        }
        
        self.total_output['portfolio_returns'] = portfolio_returns

        return self.total_output
    
    def sector_breakdown(self):
        """
        Calculate sector breakdown of portfolio.
        """
        
        # Initialize dictionaries to store aggregated allocations
        sector_breakdown = {}
        industry_breakdown = {}
        sub_industry_breakdown = {}
        
        # Aggregate allocations
        for position in self.portfolio:
            # Convert allocation to float
            allocation = float(position['allocation'])
            
            # Aggregate by sector
            sector = position.get('sector', 'Unknown')
            if sector in sector_breakdown:
                sector_breakdown[sector] += allocation
            else:
                sector_breakdown[sector] = allocation
            
            # Aggregate by industry
            industry = position.get('industry', 'Unknown')
            if industry in industry_breakdown:
                industry_breakdown[industry] += allocation
            else:
                industry_breakdown[industry] = allocation
            
            # Aggregate by sub_industry
            sub_industry = position.get('sub_industry', 'Unknown')
            if sub_industry in sub_industry_breakdown:
                sub_industry_breakdown[sub_industry] += allocation
            else:
                sub_industry_breakdown[sub_industry] = allocation
        
        # Round all values to 2 decimal places and sort by allocation
        sector_breakdown = {k: round(v, 2) for k, v in sorted(sector_breakdown.items(), key=lambda x: x[1], reverse=True)}
        industry_breakdown = {k: round(v, 2) for k, v in sorted(industry_breakdown.items(), key=lambda x: x[1], reverse=True)}
        sub_industry_breakdown = {k: round(v, 2) for k, v in sorted(sub_industry_breakdown.items(), key=lambda x: x[1], reverse=True)}
        
        # Calculate totals for verification
        total_allocation = round(sum(float(p['allocation']) for p in self.portfolio), 2)
        
        result = {
            'total_allocation': total_allocation,
            'sector_breakdown': sector_breakdown,
            'industry_breakdown': industry_breakdown,
            'sub_industry_breakdown': sub_industry_breakdown
        }

        self.total_output['sector_breakdown'] = result

        return self.total_output

    def performance_metrics(self):
        """
        Calculate performance metrics for the portfolio.
        """
        # Convert portfolio list to dictionary format {ticker: weight}
        tickers_weights = {}
        for position in self.portfolio:
            # Convert allocation percentage to decimal weight
            tickers_weights[position['ticker']] = float(position['allocation']) / 100.0
        
        # Initialize performance calculator with required parameters
        performance_calculator = PortfolioPerformanceCalculations(
            tickers_weights=tickers_weights,
            start_date=self.start_date.strftime('%Y-%m-%d'),
            end_date=self.end_date.strftime('%Y-%m-%d')
        )
        
        # Calculate performance metrics
        performance_metrics = {
            'Sharpe Ratio': str(round(float(performance_calculator.sharpe_ratio()), 4)),
            'Sortino Ratio': str(round(float(performance_calculator.sortino_ratio()), 4)),
            'Calmar Ratio': str(round(float(performance_calculator.calmar_ratio()), 4)),
            'Max Drawdown': str(round(float(performance_calculator.calculate_max_drawdown())*100, 4)),
        }
        
        self.total_output['performance_metrics'] = performance_metrics

        return self.total_output
    
    def risk_metrics(self):
        """
        Calculate risk metrics for the portfolio using PortfolioRiskCalculations.
        """
        # Extract tickers and weights
        tickers = []
        weights_dict = {}

        for position in self.portfolio:
            ticker = position['ticker'].upper()
            tickers.append(ticker)
            weights_dict[ticker] = float(position['allocation']) / 100.0
        
        # Initialize risk calculator with tickers
        risk_calculator = PortfolioRiskCalculations(
            confidence_level=0.99,  # 99% confidence for VaR
            trading_days=252,
            tickers=tickers
        )
        
        # Create weights array in same order as tickers
        weights = np.array([weights_dict[ticker] for ticker in tickers])
        
        # Calculate risk metrics
        risk_metrics = {}
        
        # 1. Value at Risk (VaR) - Multiple Methods
        parametric_var = risk_calculator.calculate_parametric_var(weights)
        historical_var = risk_calculator.calculate_historical_var(weights)
        monte_carlo_var = risk_calculator.calculate_monte_carlo_var(weights)
        
        risk_metrics['VaR (1-day, 99% - Parametric)'] = str(round(float(parametric_var['var_1day']) * 100, 4)) + '%'
        risk_metrics['VaR (1-day, 99% - Historical)'] = str(round(float(historical_var['var_1day']) * 100, 4)) + '%'
        risk_metrics['VaR (1-day, 99% - Monte Carlo)'] = str(round(float(monte_carlo_var['var_1day']) * 100, 4)) + '%'
        risk_metrics['Annual Volatility'] = str(round(float(parametric_var['portfolio_vol_annual']) * 100, 4)) + '%'
        
        # 2. Expected Shortfall (CVaR) - Multiple Methods
        expected_shortfall_hist = risk_calculator.calculate_expected_shortfall(weights, method='historical')
        expected_shortfall_param = risk_calculator.calculate_expected_shortfall(weights, method='parametric')
        risk_metrics['Expected Shortfall (Historical)'] = str(round(float(expected_shortfall_hist) * 100, 4)) + '%'
        risk_metrics['Expected Shortfall (Parametric)'] = str(round(float(expected_shortfall_param) * 100, 4)) + '%'
        
        # 3. Diversification Analysis
        div_analysis = risk_calculator.calculate_diversified_vs_undiversified_var(weights)
        risk_metrics['Diversification Benefit'] = str(round(float(div_analysis['diversification_benefit']) * 100, 4)) + '%'
        risk_metrics['Diversified VaR'] = str(round(float(div_analysis['diversified_var']) * 100, 4)) + '%'
        risk_metrics['Undiversified VaR'] = str(round(float(div_analysis['undiversified_var']) * 100, 4)) + '%'
        
        # 4. Marginal VaR Analysis
        marginal_var, component_var = risk_calculator.calculate_marginal_var(weights)
        
        # Top 3 risk contributors
        top_contributors = component_var.abs().nlargest(3)
        risk_contributors = []
        for ticker, contrib in top_contributors.items():
            risk_contributors.append({
                'ticker': ticker,
                'component_var': str(round(float(contrib) * 100, 4)) + '%',
                'marginal_var': str(round(float(marginal_var[ticker]) * 100, 4)) + '%'
            })
        risk_metrics['Top Risk Contributors'] = risk_contributors
        
        # 5. Correlation Matrix (top 5 correlations)
        corr_matrix = pd.DataFrame(
            risk_calculator.correlation_matrix,
            index=tickers,
            columns=tickers
        )
        
        # Get unique pairs with highest absolute correlations
        corr_pairs = []
        for i in range(len(tickers)):
            for j in range(i+1, len(tickers)):
                corr_pairs.append({
                    'pair': f"{tickers[i]}-{tickers[j]}",
                    'correlation': str(round(float(corr_matrix.iloc[i, j]), 4))
                })
        
        # Sort by absolute correlation and take top 5
        corr_pairs.sort(key=lambda x: abs(float(x['correlation'])), reverse=True)
        risk_metrics['Top Correlations'] = corr_pairs[:5]
        
        # 6. Portfolio Volatility Decomposition
        individual_vols = np.sqrt(np.diag(risk_calculator.covariance_matrix.values)) / np.sqrt(252)
        weighted_individual_vols = weights * individual_vols
        vol_contributions = []
        for i, ticker in enumerate(tickers):
            vol_contributions.append({
                'ticker': ticker,
                'individual_vol': str(round(float(individual_vols[i]) * 100, 4)) + '%',
                'weighted_contribution': str(round(float(weighted_individual_vols[i]) * 100, 4)) + '%'
            })
        
        # Sort by weighted contribution
        vol_contributions.sort(key=lambda x: abs(float(x['weighted_contribution'].replace('%', ''))), reverse=True)
        risk_metrics['Volatility Contributors'] = vol_contributions[:5]
        
        self.total_output['risk_metrics'] = risk_metrics
        
        return self.total_output
    
    def format_portfolio_to_json(self):
        """
        Format the portfolio to a JSON object.
        """
        self.calculate_portfolio_returns()
        self.sector_breakdown()
        self.performance_metrics()
        self.risk_metrics()
        return self.total_output

        

    

    