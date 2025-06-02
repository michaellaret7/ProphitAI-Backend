from backend.src.utils.ib_utils import connect_to_ib, disconnect_from_ib, get_ib
from ib_insync import Stock, MarketOrder
from backend.src.utils.ticker_utils import name_to_ticker

def exit_position(symbol):
    """
    Exits a position by selling all shares of the specified stock at market price.
    
    Args:
        symbol (str): The stock symbol to sell
        
    Returns:
        dict: Result of the order or None if no position found/order failed
    """
    ib = get_ib()
    
    if ib is None:
        return None  # Return None if connection failed
    
    # Convert company name to ticker if needed
    ticker = name_to_ticker(symbol)
    
    # Get portfolio data
    portfolio = ib.portfolio()
    
    # Find position for the specified symbol
    position_found = False
    for position in portfolio:
        if position.contract.symbol == ticker:
            position_found = True
            quantity = abs(position.position)
            
            if quantity <= 0:
                print(f"No position found for {ticker}.")
                return None
                
            print(f"Found position: {quantity} shares of {ticker}")
            
            # Create contract
            contract = Stock(ticker, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # Create market sell order
            sell_order = MarketOrder('SELL', quantity)
            sell_order.tif = 'GTC'
            
            # Place the order
            trade = ib.placeOrder(contract, sell_order)
            print(f"Market sell order placed for {quantity} shares of {ticker}")
            
            # Wait for order to be acknowledged
            while trade.orderStatus.status == 'PendingSubmit':
                ib.sleep(0.1)
                
            print(f"Order status: {trade.orderStatus.status}")
            
            return trade
    
    if not position_found:
        print(f"No position found for {ticker}.")
        return None

def prompt_exit_position(symbol):
    """
    Interactive user flow for exiting positions. Prompts user to confirm
    selling all shares of the specified stock at market price.
    
    Args:
        symbol (str): The stock symbol to sell
        
    Returns:
        dict: Result of the order or None if canceled/no position
    """
    ib = get_ib()
    
    if ib is None:
        return None  # Return None if connection failed
    
    # Convert company name to ticker if needed
    ticker = name_to_ticker(symbol)
    
    print(f"\n--- Exit Position for {ticker} ---")
    
    # Get portfolio data
    portfolio = ib.portfolio()
    
    # Find position for the specified symbol
    position_found = False
    for position in portfolio:
        if position.contract.symbol == ticker:
            position_found = True
            quantity = abs(position.position)
            market_value = position.marketValue
            market_price = position.marketPrice
            
            if quantity <= 0:
                print(f"No position found for {ticker}.")
                return None
            
            # Display position details
            print(f"\nCurrent position:")
            print(f"Symbol: {ticker}")
            print(f"Quantity: {quantity} shares")
            print(f"Current price: ${market_price:.2f}")
            print(f"Market value: ${market_value:.2f}")
            
            # Confirm exit
            confirmation = input(f"\nAre you sure you want to sell all {quantity} shares of {ticker} at market price? (y/n): ").lower()
            
            if confirmation == 'y' or confirmation == 'yes':
                print(f"\nPlacing market sell order for {quantity} shares of {ticker}...")
                result = exit_position(ticker)
                if result:
                    print(f"✅ Exit order submitted successfully!")
                return result
            else:
                print("Order cancelled.")
                return None
    
    if not position_found:
        print(f"No position found for {ticker}.")
        return None