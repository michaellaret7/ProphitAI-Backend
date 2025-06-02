from typing import List, Dict, Any, Optional

from ib_insync import IB, PortfolioItem

from backend.src.utils.ib_utils import get_ib
from backend.src.utils.logging_config import init_logger

logger = init_logger(__name__)

def fetch_ibkr_portfolio_positions() -> Optional[List[Dict[str, Any]]]:
    """
    Fetches portfolio positions from Interactive Brokers.

    Returns:
        A list of dictionaries, where each dictionary represents a position,
        or None if the connection to IBKR fails or no data is retrieved.
    """
    ib: Optional[IB] = get_ib()
    if not ib or not ib.isConnected():
        logger.error("❌ Failed to connect to Interactive Brokers.")
        return None

    try:
        logger.info("Attempting to retrieve portfolio positions from IBKR...")
        portfolio: List[PortfolioItem] = ib.portfolio()
        logger.info(f"📊 Retrieved {len(portfolio)} portfolio positions.")

        positions_data: List[Dict[str, Any]] = []
        for item in portfolio:
            contract = item.contract
            position_details = {
                'symbol': contract.symbol,
                'secType': contract.secType,
                'exchange': contract.exchange,
                'currency': contract.currency,
                'position': item.position,
                'marketPrice': item.marketPrice,
                'marketValue': item.marketValue,
                'averageCost': item.averageCost,
                'unrealizedPNL': item.unrealizedPNL,
                'realizedPNL': item.realizedPNL,
                'account': item.account
            }
            if contract.secType == "OPT": # Option specific details
                position_details['right'] = contract.right
                position_details['strike'] = contract.strike
                position_details['lastTradeDateOrContractMonth'] = contract.lastTradeDateOrContractMonth
                position_details['multiplier'] = contract.multiplier

            positions_data.append(position_details)
        
        logger.info(f"Formatted {len(positions_data)} positions.")

        return positions_data

    except Exception as e:
        logger.error(f"🚨 Error fetching portfolio positions from IBKR: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # This is for testing purposes
    from backend.src.utils.logging_config import patch_print_for_logging
    patch_print_for_logging() # Redirect print to logging
    
    logger.info("🚀 Starting IBKR portfolio positions fetch test...")
    positions = fetch_ibkr_portfolio_positions()

    if positions is not None:
        logger.info(f"Successfully fetched {len(positions)} positions.")
        
        logger.info(f"\n--- Positions ({len(positions)}) ---")
        for pos in positions:
            logger.info(
                f"Account: {pos.get('account', 'N/A')}, "
                f"Symbol: {pos.get('symbol', 'N/A')}, "
                f"Type: {pos.get('secType', 'N/A')}, "
                f"Exchange: {pos.get('exchange', 'N/A')}, "
                f"Currency: {pos.get('currency', 'N/A')}, "
                f"Position: {pos.get('position', 0)}, "
                f"Market Price: {pos.get('marketPrice', 0.0):.2f}, "
                f"Market Value: {pos.get('marketValue', 0.0):.2f}, "
                f"Average Cost: {pos.get('averageCost', 0.0):.2f}, "
                f"Unrealized PNL: {pos.get('unrealizedPNL', 0.0):.2f}, "
                f"Realized PNL: {pos.get('realizedPNL', 0.0):.2f}"
                + (f", Right: {pos.get('right', 'N/A')}" if pos.get('secType') == "OPT" else "")
                + (f", Strike: {pos.get('strike', 'N/A')}" if pos.get('secType') == "OPT" else "")
                + (f", Expiry: {pos.get('lastTradeDateOrContractMonth', 'N/A')}" if pos.get('secType') == "OPT" else "")
                + (f", Multiplier: {pos.get('multiplier', 'N/A')}" if pos.get('secType') == "OPT" else ""),
                
            )
    else:
        logger.error("❌ Failed to fetch portfolio positions.")

    # Ensure IB connection is closed if get_ib() was called, 
    # atexit in ib_utils should handle this, but being explicit can be good for scripts
    ib_instance = get_ib() # Get the instance (might be None)
    if ib_instance and ib_instance.isConnected():
        logger.info("Ensuring IBKR disconnection for script.")
        ib_instance.disconnect()
    logger.info("Test finished.") 