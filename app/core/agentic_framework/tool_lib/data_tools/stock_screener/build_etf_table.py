import csv
import pandas as pd
from datetime import datetime, timedelta
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.core.calculations.factors.momentum import MomentumFactors
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.utils.ticker_utils import get_sector_etf
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.db.core.pull_fmp_data import FMP_API_DATA

def calculate_ebit_cagr(fmp_api: FMP_API_DATA, ticker: str, years: int = 5) -> float | None:
    """
    Calculate EBIT Compound Annual Growth Rate from annual income statements.

    Args:
        fmp_api: FMP API instance
        ticker: Stock ticker symbol
        years: Number of years for CAGR calculation (default 5)

    Returns:
        EBIT CAGR as a decimal (e.g., 0.08 for 8%), or None if insufficient data
    """
    income_statements = fmp_api.get_income_statements(ticker, period='annual')

    if not income_statements or len(income_statements) < years:
        return None

    # Statements are returned newest first, so index 0 is most recent
    ending_ebit = income_statements[0].get('operatingIncome')
    beginning_ebit = income_statements[years - 1].get('operatingIncome')

    if not ending_ebit or not beginning_ebit or beginning_ebit <= 0:
        return None

    # CAGR = (Ending / Beginning)^(1/n) - 1
    cagr = (ending_ebit / beginning_ebit) ** (1 / years) - 1
    return round(cagr, 4)


def build_price_values(ticker: str):
    fmp_api = FMP_API_DATA()
    with MarketSession() as session:
        ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker).first()
        if not ticker_obj or not ticker_obj.sector:
            raise ValueError(f"Ticker {ticker} not found or has no sector")
        sector_etf = get_sector_etf(ticker_obj.sector)
        if not sector_etf:
            raise ValueError(f"Sector ETF for {ticker} (sector: {ticker_obj.sector}) not found")
        
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    price_data = fetch_bulk_ohlcv_data_for_tickers([ticker, 'SPY', sector_etf], start_date_str, end_date_str, frequency='daily', returns=True)
    df = pd.DataFrame(price_data[ticker])
    print(df)
    spy_df = pd.DataFrame(price_data['SPY'])
    sector_df = pd.DataFrame(price_data[sector_etf])

    alpha_vs_spy = round(PerformanceCalculator.alpha_jensen(df['returns'], spy_df['returns']), 4)
    alpha_vs_sector = round(PerformanceCalculator.alpha_jensen(df['returns'], sector_df['returns']), 4)

    mf = MomentumFactors(df['close'])
    momentum_1m = round(mf.one_month_return(), 4) 
    momentum_3m = round(mf.three_month_return(), 4) 
    momentum_6m = round(mf.six_month_return(), 4)

    ann_return = round(ReturnsCalculator.annualized_return(df['returns']), 4)
    ann_vol = round(RiskCalculator.annualized_volatility(df['returns']), 4)
    beta_vs_spy = round(RiskCalculator.beta(df['returns'], spy_df['returns']), 4)
    beta_vs_sector = round(RiskCalculator.beta(df['returns'], sector_df['returns']), 4)

    SELECTED_RATIOS = {
        'dividendYielTTM',
        'peRatioTTM',
        'pegRatioTTM',
        'priceToBookRatioTTM',
        'priceToSalesRatioTTM',
        'priceToFreeCashFlowsRatioTTM',
        'priceToOperatingCashFlowsRatioTTM',
        'enterpriseValueMultipleTTM',
        'payoutRatioTTM',
        'grossProfitMarginTTM',
        'operatingProfitMarginTTM',
        'pretaxProfitMarginTTM',
        'netProfitMarginTTM',
        'returnOnAssetsTTM',
        'returnOnEquityTTM',
        'returnOnCapitalEmployedTTM',
        'operatingCashFlowSalesRatioTTM',
        'freeCashFlowOperatingCashFlowRatioTTM',
        'capitalExpenditureCoverageRatioTTM',
        'dividendPaidAndCapexCoverageRatioTTM',
        'debtRatioTTM',
        'debtEquityRatioTTM',
        'longTermDebtToCapitalizationTTM',
        'totalDebtToCapitalizationTTM',
        'interestCoverageTTM',
        'cashFlowToDebtRatioTTM',
        'shortTermCoverageRatiosTTM',
        'companyEquityMultiplierTTM',
        'quickRatioTTM',
        'cashRatioTTM',
        'cashConversionCycleTTM',
        'receivablesTurnoverTTM',
        'payablesTurnoverTTM',
        'inventoryTurnoverTTM',
        'assetTurnoverTTM',
    }

    raw_ratios = fmp_api.get_ratios_ttm(ticker)[0]
    ratios = {k: v for k, v in raw_ratios.items() if k in SELECTED_RATIOS}

    ebit_cagr_5yr = calculate_ebit_cagr(fmp_api, ticker, years=5)
    ebit_cagr_3yr = calculate_ebit_cagr(fmp_api, ticker, years=3)

    return momentum_1m, momentum_3m, momentum_6m, ann_return, ann_vol, beta_vs_spy, beta_vs_sector, alpha_vs_spy, alpha_vs_sector, ratios, ebit_cagr_5yr, ebit_cagr_3yr


