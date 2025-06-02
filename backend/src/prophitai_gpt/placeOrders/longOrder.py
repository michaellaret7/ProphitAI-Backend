from backend.src.utils.ticker_utils import name_to_ticker
from backend.src.utils.ib_utils import get_ib
from ib_insync import Stock



def place_bracket_order_long(symbol, quantity, entry_price, take_profit_price, stop_loss_price):
    """
    Places a bracket order with a primary order, a take-profit order, and a stop-loss order.
    """
    ib = get_ib()
    
    if ib is None:
        return None  # Return None if connection failed
    
    contract = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(contract)
    
    # Create the bracket order components
    parent = ib.bracketOrder(
        action='BUY',
        quantity=quantity,
        limitPrice=entry_price,
        takeProfitPrice=take_profit_price,
        stopLossPrice=stop_loss_price
    )
    
    # Set GTC for all orders
    for order in parent:
        order.tif = 'GTC'
    
    # Set transmission flags properly for a bracket
    parent[0].transmit = False  # Parent order doesn't transmit yet
    parent[1].transmit = False  # Take profit doesn't transmit yet
    parent[2].transmit = True   # Stop loss transmits all orders
    
    # Place all orders
    trades = []
    for order in parent:
        trade = ib.placeOrder(contract, order)
        trades.append(trade)
        ib.sleep(0.1)  # Small delay between order submissions
    
    # Wait for order acknowledgement
    for trade in trades:
        print(f"Order {trade.order.orderId} status: {trade.orderStatus.status}")
    
    print("✅ Order submitted successfully!")
    return parent[0]  # Return the parent order

def prompt_long_buy_order(symbol):
    """
    Interactive user flow for long buy orders. Prompts user for required parameters,
    confirms the order details, and places the order if confirmed.
    
    Args:
        symbol (str): The stock symbol to buy
        
    Returns:
        dict: Result of the order or None if canceled
    """
    # Convert company name to ticker if needed
    ticker = name_to_ticker(symbol)
    
    print(f"\n--- Long Buy Order for {ticker} ---")
    
    # Prompt for each parameter one at a time with clear instructions
    print("\nPlease enter the following details one by one:")
    
    # Get quantity
    while True:
        quantity = input("📦 How many shares: ")
        try:
            quantity = int(quantity)
            if quantity > 0:
                break
            else:
                print("Quantity must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get entry price
    while True:
        entry_price = input("💲 Entry price: ")
        try:
            entry_price = float(entry_price)
            if entry_price > 0:
                break
            else:
                print("Price must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid price.")
    
    # Get stop loss
    while True:
        stop_loss = input("🛑 Stop loss: ")
        try:
            stop_loss = float(stop_loss)
            if stop_loss > 0:
                break
            else:
                print("Stop loss must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid price.")
    
    # Get take profit
    while True:
        take_profit = input("🎯 Take profit: ")
        try:
            take_profit = float(take_profit)
            if take_profit > 0:
                break
            else:
                print("Take profit must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid price.")
    
    # Confirm order details
    print(f"\nJust to confirm, you want to buy {quantity} shares of {ticker} at ${entry_price:.2f} with a stop loss of ${stop_loss:.2f} and a take profit of ${take_profit:.2f}")
    confirmation = input("Confirm order (y/n): ").lower()
    
    if confirmation == 'y' or confirmation == 'yes':
        # Place the order
        result = place_bracket_order_long(ticker, quantity, entry_price, take_profit, stop_loss)
        print(f"✅ Order submitted successfully!")
        return result
    else:
        print("Order cancelled.")
        return None

