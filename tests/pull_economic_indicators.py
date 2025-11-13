"""
Fetch US Economic Indicators from FMP API.

Retrieves macroeconomic time series data including:
- Labor market (unemployment, payrolls, jobless claims)
- Growth & output (GDP, industrial production, retail sales)
- Inflation & prices (CPI, PCE, inflation rate)
- Housing (starts, sales, prices)
- Credit & rates (Fed funds, mortgage rates, CD rates)
- Consumer metrics (sentiment, confidence, expectations)
- Business (vehicle sales, investment, recession probabilities)
"""
import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# All available economic indicators from FMP (only indicators that return data)
ECONOMIC_INDICATORS = {
    # Labor Market
    "unemploymentRate": "Unemployment Rate",
    "totalNonfarmPayroll": "Total Nonfarm Payroll",
    "initialClaims": "Initial Jobless Claims",

    # Growth & Output
    "GDP": "Gross Domestic Product",
    "realGDP": "Real GDP",
    "nominalPotentialGDP": "Nominal Potential GDP",
    "realGDPPerCapita": "Real GDP Per Capita",
    "industrialProductionTotalIndex": "Industrial Production Total Index",
    "retailSales": "Retail Sales",
    "durableGoods": "Durable Goods Orders",

    # Inflation & Prices
    "CPI": "Consumer Price Index",
    "inflationRate": "Inflation Rate",
    "retailMoneyFunds": "Retail Money Funds",

    # Credit & Rates
    "federalFunds": "Federal Funds Rate",

    # Consumer Metrics
    "consumerSentiment": "Consumer Sentiment (University of Michigan)",

    # Business
    "totalVehicleSales": "Total Vehicle Sales",
}


def get_economic_indicator(indicator_name: str, from_date: str = None, to_date: str = None):
    """
    Fetch a specific economic indicator from FMP API.

    Args:
        indicator_name: The indicator name (e.g., 'GDP', 'CPI', 'unemploymentRate')
        from_date: Start date in YYYY-MM-DD format (optional)
        to_date: End date in YYYY-MM-DD format (optional)

    Returns:
        DataFrame with date and value columns
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("Set FMP_API_KEY environment variable")

    url = f"https://financialmodelingprep.com/api/v4/economic?name={indicator_name}&apikey={api_key}"

    if from_date:
        url += f"&from={from_date}"
    if to_date:
        url += f"&to={to_date}"

    response = requests.get(url)

    if response.status_code != 200:
        print(f"  Error: API returned status {response.status_code}")
        return pd.DataFrame()

    data = response.json()

    if not data or not isinstance(data, list):
        print(f"  No data available")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return df


def fetch_all_economic_indicators(from_date: str = "2000-01-01", to_date: str = None):
    """
    Fetch all available economic indicators.

    Args:
        from_date: Start date in YYYY-MM-DD format (default: 2000-01-01)
        to_date: End date in YYYY-MM-DD format (default: today)

    Returns:
        Dictionary mapping indicator names to DataFrames
    """
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching {len(ECONOMIC_INDICATORS)} economic indicators...")
    print(f"Date range: {from_date} to {to_date}")
    print("=" * 80)

    results = {}
    success_count = 0
    failed_indicators = []

    for indicator_key, indicator_label in ECONOMIC_INDICATORS.items():
        print(f"\n{indicator_label} ({indicator_key})...")

        try:
            df = get_economic_indicator(indicator_key, from_date, to_date)

            if not df.empty:
                results[indicator_key] = df
                print(f"  Success: {len(df)} records")
                success_count += 1
            else:
                failed_indicators.append(indicator_key)

        except Exception as e:
            print(f"  Failed: {e}")
            failed_indicators.append(indicator_key)

    print("\n" + "=" * 80)
    print(f"Summary: {success_count}/{len(ECONOMIC_INDICATORS)} indicators fetched successfully")

    if failed_indicators:
        print(f"\nFailed indicators: {', '.join(failed_indicators)}")

    return results


if __name__ == "__main__":
    # Fetch all indicators from 2000 onwards
    # data = fetch_all_economic_indicators(from_date="2000-01-01")

    import seaborn as sns
    import matplotlib.pyplot as plt

    import seaborn as sns
    import matplotlib.pyplot as plt

    vs = get_economic_indicator("totalVehicleSales", from_date="1990-01-01")
    rgdp = get_economic_indicator("realGDP", from_date="1990-01-01")
    cs = get_economic_indicator("consumerSentiment", from_date="1990-01-01")
    inflationRate = get_economic_indicator("inflationRate", from_date="1990-01-01")
    nfpr = get_economic_indicator("consumerSentiment", from_date="1990-01-01")

    print(nfpr)

