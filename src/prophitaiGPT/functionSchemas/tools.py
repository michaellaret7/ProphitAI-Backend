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
}]
