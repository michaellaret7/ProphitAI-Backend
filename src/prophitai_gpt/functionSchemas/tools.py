tools = [{
    "type": "function",
    "function": {
        "name": "get_portfolio_data",
        "description": """
        Retrieve current portfolio positions from Interactive Brokers.

        Examples:
        - Show my current portfolio holdings
        - What positions do I currently own?
        - Display my investment holdings
        - List active positions
        - Show portfolio breakdown
        - Current market positions
        - Portfolio status
        - Investment allocation
        - Open positions summary
        - Active trades overview
        """,
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "place_bracket_order_long",
        "description": """
        The user will give you a stock symbol, quantity, entry price, take profit price, and stop loss price.
        If the user does not give you a quantity, then the quantity is 100.
        If the user uses the name of the stock instead of the ticker symbol, then you must convert the name of the stock into its ticker symbol.
        
        Activate for ANY stock purchase expressions:
        - General: "buy a stock", "purchase stock", "invest in", "want to buy", "add to portfolio"
        - Specific: "buy", "go long", "long", "purchase", "enter position", "initiate position"
        - Action: "place an order", "execute trade", "make a purchase"
        - With stock: "buy shares of", "invest in", "purchase some"
        
        Trigger this for both general buying statements AND specific purchase requests.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The stock symbol of the data to push to excel"},
                "quantity": {"type": "number", "description": "The quantity of the stock to trade, this is in number of shares not dollar amount"},
                "entry_price": {"type": "number", "description": "The price at which to enter the position"},
                "take_profit_price": {"type": "number", "description": "The price at which to take profit"},
                "stop_loss_price": {"type": "number", "description": "The price at which to stop loss"}
            },
            "required": ["symbol", "quantity", "entry_price", "take_profit_price", "stop_loss_price"],
            "additionalProperties": False
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "prompt_exit_position",
        "description": """
        Exit/sell an existing position in a specified stock at market price.
        
        Activate for ANY selling/exit expressions:
        - General: "exit position", "sell my shares", "close position", "liquidate position", "get out of", "exit my position", "close my position", "sell my position", "sell my shares of", "exit my position in", "close out of", "get out of my position in", "exit {stock name}", "close {stock name}", "sell {stock name}", "sell my shares of {stock name}", "exit my position in {stock name}", "close out of {stock name}", "get out of my position in {stock name}"
        - Specific: "sell", "exit", "close", "dump", "get rid of", "unload"
        - Action: "sell all shares", "exit my position", "close my position"
        - With stock: "sell my shares of", "exit my position in", "close out of", "get out of my position in"
        
        Trigger this whenever the user wants to sell or exit a position in a stock.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The stock symbol to exit/sell"}
            },
            "required": ["symbol"],
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
        = market_cap
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
