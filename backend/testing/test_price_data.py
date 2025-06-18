from ib_insync import IB, Stock, util
from backend.src.utils.ib_utils import get_ib
import pandas as pd

def get_last_day_price_data(ticker: str):
    """
    Queries data from the last day for the given ticker from IB-insync.

    Args:
        ticker (str): The stock ticker symbol.

    Returns:
        pd.DataFrame: A pandas DataFrame with the historical data, or None.
    """
    ib = get_ib()
    if not ib:
        print("Could not connect to IB.")
        return None

    contract = Stock(ticker, 'SMART', 'USD')
    ib.qualifyContracts(contract)

    # Request historical data for the last day
    # '1 D' means one day, '1 min' is the bar size.
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr='1 D',
        barSizeSetting='1 min',
        whatToShow='TRADES',
        useRTH=True
    )

    if bars:
        # Convert to pandas DataFrame
        df = util.df(bars)
        return df
    else:
        print(f"No historical data found for {ticker}")
        return None

if __name__ == '__main__':

    # fixed_income_etfs = ["EMLC", "HYXU", "HYD", "BKLN", "SJB", "BNDX", "BAB", "LTPZ", "EDV", "TMF", "TBT"]
    # equity_etfs = ["SKYY", "CLOU", "HACK", "TAN", "LIT", "NOBL", "COWZ", "SYLD", "BTAL", "IPO", "FPX", "FTLS", "RSP", "SSO", "SPXU", "TQQQ", "SQQQ"]
    # alts_etfs = ["HFND", "ARB", "DBMF", "KMLM", "CTA", "BTAL", "FTLS", "PSH", "IEP", "GLRE"]
    clo_etfs = ["JAAA", "JBBB", "CLOI", "PAAA", "ICLO", "CLOA", "TRPA", "BCLO", "NCLO"]
    abs_etfs = ["VABS", "FUSI", "NBSD", "JPLD", "USTB", "TUSI"]
    # pe_funds = ["PEX", "PEVC", "LBO", "BDCZ", "BDCX", "ALTY", "IPRV"]
    for etf in abs_etfs:
        price_data = get_last_day_price_data(etf)
        print(price_data)
        print("--------------------------------")

    # print(get_last_day_price_data("TYA"))


