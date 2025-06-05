tools = [{
    "type": "function",
    "function": {
        "name": "get_portfolio_data",
        "description": """
        Retrieve the current portfolio positions for the (currently fixed) demo user.

        NOTE: Authentication is not implemented yet. The backend will always return
        the holdings for the demo user 'test_user_beta', so no parameters are
        necessary right now.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "user_name": {
                    "type": "string",
                    "description": "The username of the user whose portfolio data is to be retrieved (e.g., 'test_user_beta')."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "retrieve_financial_metric",
        "description": """
        Retrieves the historical time series of a specified financial metric for a given stock ticker.
        It fetches the metric values along with the corresponding date, ordered by date.
        This is the list of all of the metrics that you can retrieve:
        - market_cap
        - enterprise_value
        - price_to_earnings_ratio
        - price_to_book_ratio
        - price_to_sales_ratio
        - enterprise_value_to_ebitda_ratio
        - enterprise_value_to_revenue_ratio
        - free_cash_flow_yield
        - peg_ratio
        - gross_margin
        - operating_margin
        - net_margin
        - return_on_equity
        - return_on_assets
        - return_on_invested_capital
        - asset_turnover
        - inventory_turnover
        - receivables_turnover
        - days_sales_outstanding
        - operating_cycle
        - working_capital_turnover
        - current_ratio
        - quick_ratio
        - cash_ratio
        - operating_cash_flow_ratio
        - debt_to_equity
        - debt_to_assets
        - interest_coverage
        - revenue_growth
        - earnings_growth
        - book_value_growth
        - earnings_per_share_growth
        - free_cash_flow_growth
        - operating_income_growth
        - ebitda_growth
        - payout_ratio
        - earnings_per_share
        - book_value_per_share
        - free_cash_flow_per_share
        
        Example queries for retrieving financial metric history:
        - "What is the historical Revenue for [ticker]?"
        - "Show me the Net Income trend for [stock name]."
        - "Get the P/E ratio time series for [ticker]."
        - "What were the Total Assets for [ticker] over time?"

        Important:
        - If the user asks for data please put it in an organized table format.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., 'AAPL') for which to retrieve the metric history."
                },
                "metric_name": {
                    "type": "string",
                    "description": "The name of the financial metric to retrieve (e.g., 'Price to Earnings Ratio', 'Revenue', 'Net Income', 'Free cash flow growth', 'Operating Income Growth')."
                }
            },
            "required": ["ticker", "metric_name"],
            "additionalProperties": False
        }
    }
}]
