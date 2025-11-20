"""Analyst estimates tools.

This module provides tools for fetching analyst earnings estimates and forecasts
for companies, enabling forward-looking fundamental analysis.
"""

from typing import Optional
from datetime import datetime
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.db.core.pull_fmp_data import FMP_API_DATA
import pandas as pd
from app.utils.time_utils import get_current_utc_time
from app.utils.token_count import get_token_count

@log_simulation_data_range()
def get_analyst_estimates(ticker: str, periods_back: int = 4, period: str = 'quarter', outlook: str = 'all', _simulation_date: Optional[datetime] = None) -> str:
    """Get analyst earnings estimates for a ticker for a given period.

    Args:
        ticker: Stock ticker symbol
        periods_back: Number of periods of historical estimates to retrieve. Default is 4.
        period: Period type - 'quarter' or 'annual'. Default is 'quarter'.
        outlook: Outlook type - 'future_estimates' or 'past_estimates' or 'all'. Default is 'all'.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        YAML formatted string with analyst estimates data including:
        - Estimated EPS (earnings per share)
        - Estimated revenue
        - Number of analysts
        - Fiscal period information
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.require_numeric('periods_back', periods_back, min_val=1, max_val=12)
    v.require_enum('period', period, ['quarter', 'annual'])
    v.require_enum('outlook', outlook, ['past_estimates', 'future_estimates', 'all'])

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    periods_back = v.get('periods_back')
    period = v.get('period')

    current_date = _simulation_date if _simulation_date else get_current_utc_time()

    try:
        fmp = FMP_API_DATA()

        income_statements = fmp.get_income_statements(ticker, period=period)
        income_statements = pd.DataFrame(income_statements)
        income_statements = income_statements[['date', 'revenue', 'ebitda', 'netIncome', 'eps', 'operatingIncome', 'sellingGeneralAndAdministrativeExpenses']]
        income_statements.rename(columns={'operatingIncome': 'ebit', 'sellingGeneralAndAdministrativeExpenses': 'sga'}, inplace=True)

        data = fmp.get_analyst_estimates(ticker, period=period)
        df = pd.DataFrame(data)

        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            
            if outlook == 'past_estimates':
                # Sort descending by date to get the most recent past periods
                df = df.sort_values('date', ascending=False)
                df = df[df['date'] < current_date]
                # Take the most recent N periods
                df = df.head(periods_back)
                # Sort back to ascending for display
                df = df.sort_values('date', ascending=True)
            elif outlook == 'future_estimates':
                # Sort ascending by date to get the next future periods
                df = df.sort_values('date', ascending=True)
                df = df[df['date'] > current_date]
                # Take the next N periods
                df = df.head(periods_back)
                
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            # Merge past estimates into estimates df
            if outlook == 'past_estimates' or outlook == 'all':
                income_statements['date'] = pd.to_datetime(income_statements['date'])
                
                # Rename income statement columns to match estimates format (suffix with 'Actual')
                rename_map = {
                    'revenue': 'revenueActual',
                    'ebitda': 'ebitdaActual',
                    'netIncome': 'netIncomeActual',
                    'eps': 'epsActual',
                    'ebit': 'ebitActual',
                    'sga': 'sgaExpenseActual'
                }
                income_statements.rename(columns=rename_map, inplace=True)
                
                # Use merge_asof to handle date mismatches (within 7 days tolerance)
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

                # If simulation date is set, remove actual data for dates after the simulation date
                if _simulation_date:
                    # Create a mask for rows that are after the simulation date
                    future_mask = df['date'] > _simulation_date
                    # Get the list of actual columns to null out
                    actual_cols = list(rename_map.values())
                    # Null out the actuals for future dates
                    df.loc[future_mask, actual_cols] = None
                
                # Calculate actual vs estimated revenue
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

        return success_response(df.to_dict(orient='records'))
    except Exception as e:
        return error_response(f"Failed to retrieve analyst estimates: {str(e)}")



# Tool Schema Constants
GET_ANALYST_ESTIMATES_DESCRIPTION = (
    "Get analyst earnings estimates for a ticker including estimated EPS, revenue, and number of analysts.\n\n"
    "This tool provides forward-looking fundamental data based on Wall Street analyst consensus estimates. "
    "Use this to understand market expectations for future earnings and revenue.\n\n"
    "**Note:** Actual values (e.g., revenueActual, epsActual) are the actual results from the company's "
    "income statement for the respective period.\n\n"
    "**Use Cases:**\n"
    "  - Valuation analysis: Compare current valuation to expected future earnings\n"
    "  - Growth expectations: Understand market consensus on growth trajectory\n"
    "  - Earnings surprises: Compare actual results to estimates (beat/miss)\n"
    "  - Investment thesis validation: Verify if your analysis aligns with consensus\n\n"
    "**Example:** get_analyst_estimates(ticker='AAPL', periods_back=4)"
)

GET_ANALYST_ESTIMATES_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ticker symbol to get analyst estimates for. For example, 'AAPL', 'MSFT', 'GOOGL', etc.",
        },
        "periods_back": {
            "type": "integer",
            "description": "Number of periods of historical estimates to retrieve. Default is 4 (one year of quarterly estimates or 4 years of annual estimates).",
            "default": 4,
            "minimum": 1,
            "maximum": 12
        },
        "period": {
            "type": "string",
            "description": "Period type for estimates. 'quarter' for quarterly estimates or 'annual' for annual estimates. Default is 'quarter'.",
            "enum": ["quarter", "annual"],
            "default": "quarter"
        },
        "outlook": {
            "type": "string",
            "description": "Outlook type. 'past_estimates' for historical data, 'future_estimates' for future data, or 'all' for both. Default is 'all'.",
            "enum": ["past_estimates", "future_estimates", "all"],
            "default": "all"
        },
    },
    "required": ["ticker"],
}

GET_ANALYST_ESTIMATES_TOOL = {
    "name": "get_analyst_estimates",
    "description": GET_ANALYST_ESTIMATES_DESCRIPTION,
    "parameters": GET_ANALYST_ESTIMATES_PARAMETERS,
    "function": get_analyst_estimates,
}
