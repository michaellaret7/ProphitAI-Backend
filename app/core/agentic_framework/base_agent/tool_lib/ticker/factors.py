from app.core.calculations.factors.growth import GrowthFactors
from app.core.calculations.factors.value import ValueFactors
from app.core.calculations.factors.quality import QualityFactors
from app.core.calculations.factors.momentum import MomentumFactors
from app.core.calculations.factors.volatility import VolatilityFactors
from app.core.calculations.core import DataService
from datetime import datetime, timedelta

def calculate_ticker_factors(ticker: str, factor: str):
    """Calculate all factor metrics for a given ticker and factor type."""
    # Growth, Value, and Quality factors take ticker string directly
    if factor in ["growth", "value", "quality"]:
        if factor == "growth":
            return GrowthFactors(ticker).calc_all()
        elif factor == "value":
            return ValueFactors(ticker).calc_all()
        else:  # quality
            return QualityFactors(ticker).calc_all()
    
    # Momentum and Volatility factors need price series
    elif factor in ["momentum", "volatility"]:
        ds = DataService()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=504)  # ~2 years of data
        
        # Get price data for ticker (and SPY for market-relative metrics)
        price_data = ds.get_price_data(ticker, start_date, end_date)
        if price_data is None or price_data.frame.empty:
            return {"error": f"No price data available for {ticker}"}
        
        price_series = price_data.frame['close']
        
        # Get SPY data for both momentum and volatility
        spy_data = ds.get_price_data("SPY", start_date, end_date)
        spy_prices = spy_data.frame['close'] if spy_data and not spy_data.frame.empty else None
        
        if factor == "momentum":
            # Get additional data for momentum calculations
            volume_series = price_data.frame.get('volume', None)
            
            # Get dividends if available
            try:
                divs = ds.get_dividends(ticker, start_date, end_date).series
                divs = divs.reindex(price_series.index).fillna(0.0)
            except Exception:
                divs = None
            
            return MomentumFactors(
                price_series=price_series,
                volume_series=volume_series,
                market_price_series=spy_prices,
                dividends_series=divs
            ).calc_all()
        else:  # volatility
            return VolatilityFactors(price_series, spy_price_series=spy_prices).calc_all()
    
    else:
        raise ValueError(f"Unknown factor: {factor}")