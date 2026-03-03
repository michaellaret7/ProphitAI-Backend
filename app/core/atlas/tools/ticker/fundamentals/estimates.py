"""Analyst estimates tools.

Provides tools for fetching analyst earnings estimates and forecasts
for companies, enabling forward-looking fundamental analysis.
Supports batched multi-ticker calls.
"""

from datetime import datetime
from typing import Annotated, Literal

import pandas as pd

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

def _fetch_estimates_for_ticker(
    fmp: FMP_API_DATA,
    ticker: str,
    periods_back: int,
    period: str,
    outlook: str,
    current_date: datetime,
) -> dict:
    """Fetch and process analyst estimates for a single ticker."""

    data = fmp.get_analyst_estimates(ticker, period=period)
    df = pd.DataFrame(data)

    if df.empty or 'date' not in df.columns:
        raise ValueError(f"No analyst estimates found for {ticker}")

    income_statements = pd.DataFrame(fmp.get_income_statements(ticker, period=period))

    # Reason: guard against empty income statements for tickers with estimates but no filings
    required_cols = ['date', 'revenue', 'ebitda', 'netIncome', 'eps', 'operatingIncome', 'sellingGeneralAndAdministrativeExpenses']
    if income_statements.empty or not all(c in income_statements.columns for c in required_cols):
        income_statements = pd.DataFrame(columns=required_cols)

    income_statements = income_statements[required_cols]
    income_statements.rename(columns={'operatingIncome': 'ebit', 'sellingGeneralAndAdministrativeExpenses': 'sga'}, inplace=True)

    df['date'] = pd.to_datetime(df['date'])

    if outlook == 'past_estimates':
        df = df.sort_values('date', ascending=False)
        df = df[df['date'] < current_date]
        df = df.head(periods_back)
        df = df.sort_values('date', ascending=True)
    elif outlook == 'future_estimates':
        df = df.sort_values('date', ascending=True)
        df = df[df['date'] > current_date]
        df = df.head(periods_back)

    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    # Reason: merge actuals into estimates for beat/miss comparison
    if outlook in ('past_estimates', 'all'):
        income_statements['date'] = pd.to_datetime(income_statements['date'])

        rename_map = {
            'revenue': 'revenueActual',
            'ebitda': 'ebitdaActual',
            'netIncome': 'netIncomeActual',
            'eps': 'epsActual',
            'ebit': 'ebitActual',
            'sga': 'sgaExpenseActual'
        }
        income_statements.rename(columns=rename_map, inplace=True)

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        income_statements = income_statements.sort_values('date')

        df = pd.merge_asof(
            df,
            income_statements,
            on='date',
            direction='nearest',
            tolerance=pd.Timedelta(days=7)
        )

        # Reason: compute beat/miss diffs for each metric
        if 'revenueActual' in df.columns and 'revenueAvg' in df.columns:
            df['revenueDiff'] = df['revenueActual'] - df['revenueAvg']
        if 'ebitdaActual' in df.columns and 'ebitdaAvg' in df.columns:
            df['ebitdaDiff'] = df['ebitdaActual'] - df['ebitdaAvg']
        if 'netIncomeActual' in df.columns and 'netIncomeAvg' in df.columns:
            df['netIncomeDiff'] = df['netIncomeActual'] - df['netIncomeAvg']
        if 'epsActual' in df.columns and 'epsAvg' in df.columns:
            df['epsDiff'] = df['epsActual'] - df['epsAvg']
        if 'ebitActual' in df.columns and 'ebitAvg' in df.columns:
            df['ebitDiff'] = df['ebitActual'] - df['ebitAvg']
        if 'sgaExpenseActual' in df.columns and 'sgaExpenseAvg' in df.columns:
            df['sgaExpenseDiff'] = df['sgaExpenseActual'] - df['sgaExpenseAvg']

        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    return df.to_dict(orient='records')


# ================================
# --> Tools
# ================================

@agent_tool(name="get_analyst_estimates")
def get_analyst_estimates(
    tickers: list[str],
    periods_back: Annotated[int, Param(min_val=1, max_val=12)] = 4,
    period: Literal['quarter', 'annual'] = 'quarter',
    outlook: Literal['past_estimates', 'future_estimates', 'all'] = 'all',
) -> str:
    """
    Get analyst earnings estimates for one or more tickers including estimated EPS,
    revenue, and number of analysts.

    Provides forward-looking fundamental data based on Wall Street analyst consensus
    estimates. Use this to understand market expectations for future earnings and revenue.

    **Note:** Actual values (e.g., revenueActual, epsActual) are the actual results
    from the company's income statement for the respective period.

    **Use Cases:**
    - Valuation analysis: Compare current valuation to expected future earnings
    - Growth expectations: Understand market consensus on growth trajectory
    - Earnings surprises: Compare actual results to estimates (beat/miss)
    - Investment thesis validation: Verify if your analysis aligns with consensus

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        periods_back: Number of periods of historical estimates to retrieve.
            Default is 4 (one year of quarterly or 4 years of annual estimates).
        period: Period type for estimates — 'quarter' or 'annual'
        outlook: Outlook type — 'past_estimates' for historical data,
            'future_estimates' for future data, or 'all' for both

    Returns:
        Analyst estimates data including estimated EPS, revenue, EBITDA,
        net income, and actual vs estimated comparisons when available

    Examples:
        get_analyst_estimates(tickers=['AAPL', 'MSFT'], periods_back=4)
        >>> {"success": True, "data": {"results": {"AAPL": [...], "MSFT": [...]}, "errors": {}}}

    Raises:
        Exception: If data retrieval fails
    """
    tickers = [t.upper().strip() for t in tickers]
    current_date = get_current_utc_time()

    results: dict = {}
    errors: dict = {}

    try:
        fmp = FMP_API_DATA()
    except Exception as e:
        return error_response(f"Failed to initialize FMP API: {str(e)}")

    for t in tickers:
        try:
            results[t] = _fetch_estimates_for_ticker(fmp, t, periods_back, period, outlook, current_date)
        except Exception as e:
            errors[t] = f"Failed to retrieve analyst estimates for {t}: {str(e)}"

    return success_response({"results": results, "errors": errors})


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_analyst_estimates.tool)
