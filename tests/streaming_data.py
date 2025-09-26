#!/usr/bin/env python3
"""
FMP WebSocket Real-Time Stock Price Streamer
Streams and returns real-time stock price data in 5-second intervals
"""

import asyncio
import json
import os
import websockets
import ssl
import certifi
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from collections import deque
from dotenv import load_dotenv

load_dotenv()

# Create an SSL context using certifi's CA bundle to avoid macOS cert issues
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class PriceStreamer:
    """Stream real-time stock prices via WebSocket connection"""
    
    def __init__(self, api_key: str, max_history: int = 1000):
        """Initialize the price streamer
        
        Args:
            api_key: FMP API key for authentication
            max_history: Maximum number of price updates to store in history
        """
        self.api_key = api_key
        self.ws_url = "wss://websockets.financialmodelingprep.com"
        self.current_prices: Dict[str, Dict[str, Any]] = {}
        self.price_history: deque = deque(maxlen=max_history)
        self.update_interval = 5  # 5-second intervals
        self._websocket = None
        self._running = False
        
    @staticmethod
    def _normalize_message(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert raw WebSocket message to standardized list format
        
        Args:
            raw: Raw message from WebSocket
            
        Returns:
            List of normalized message dictionaries
        """
        def to_list(payload: Any) -> List[Dict[str, Any]]:
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                return [payload]
            return []

        # Extract payload from common wrapper keys
        payload = raw.get('data', raw.get('d', raw))
        return to_list(payload)

    @staticmethod
    def _extract_price_data(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract price data from a message
        
        Args:
            message: Single message dictionary
            
        Returns:
            Extracted price data or None if symbol not found
        """
        # Extract symbol
        symbol = (
            message.get('s')
            or message.get('symbol')
            or message.get('ticker')
        )
        
        if not symbol:
            return None

        # Extract price
        price = (
            message.get('p')
            or message.get('price')
            or message.get('lp')
            or message.get('last')
            or message.get('lastPrice')
            or message.get('c')
        )

        # Extract bid/ask
        bid = (
            message.get('b')
            or message.get('bid')
            or message.get('bp')
            or message.get('bidPrice')
        )
        ask = (
            message.get('a')
            or message.get('ask')
            or message.get('ap')
            or message.get('askPrice')
        )

        def to_float(value: Any) -> float:
            """Convert value to float safely"""
            try:
                return float(value) if value is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        return {
            'symbol': symbol.upper() if isinstance(symbol, str) else None,
            'price': to_float(price),
            'bid': to_float(bid),
            'ask': to_float(ask),
            'timestamp': datetime.now()
        }

    def update_price_data(self, data: Dict[str, Any]) -> None:
        """Update internal price data store
        
        Args:
            data: Message data from WebSocket
        """
        price_info = self._extract_price_data(data)
        if price_info and price_info['symbol']:
            symbol = price_info['symbol']
            # Update or merge with existing data
            if symbol in self.current_prices:
                # Keep non-zero values from previous update if current is zero
                existing = self.current_prices[symbol]
                self.current_prices[symbol] = {
                    'price': price_info['price'] or existing.get('price', 0.0),
                    'bid': price_info['bid'] or existing.get('bid', 0.0),
                    'ask': price_info['ask'] or existing.get('ask', 0.0),
                    'timestamp': price_info['timestamp']
                }
            else:
                self.current_prices[symbol] = price_info
    
    def get_current_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get current price data
        
        Returns:
            Dictionary of current price data for all tracked symbols
        """
        return self.current_prices.copy()
    
    def get_price_history(self) -> List[Dict[str, Any]]:
        """Get historical price data
        
        Returns:
            List of historical price snapshots
        """
        return list(self.price_history)
    
    async def stream_prices(self, symbols: List[str]) -> AsyncGenerator[Dict[str, Dict[str, Any]], None]:
        """Stream prices as async generator
        
        Args:
            symbols: List of stock symbols to track
            
        Yields:
            Price data dictionary every 5 seconds
        """
        self._running = True
        
        async with websockets.connect(self.ws_url, ssl=SSL_CONTEXT) as websocket:
            self._websocket = websocket
            
            # Authenticate
            login_msg = {
                "event": "login",
                "data": {"apiKey": self.api_key}
            }
            await websocket.send(json.dumps(login_msg))
            
            # Wait for login confirmation
            await websocket.recv()
            
            # Subscribe to symbols
            subscribe_msg = {
                "event": "subscribe",
                "data": {"ticker": [s.lower() for s in symbols]}
            }
            await websocket.send(json.dumps(subscribe_msg))
            
            # Start processing messages in background
            process_task = asyncio.create_task(self._process_messages())
            
            try:
                # Yield price updates at intervals
                while self._running:
                    await asyncio.sleep(self.update_interval)
                    
                    if self.current_prices:
                        snapshot = self.current_prices.copy()
                        # Store in history
                        self.price_history.append({
                            'timestamp': datetime.now(),
                            'data': snapshot
                        })
                        # Yield to consumer
                        yield snapshot
                        
            finally:
                self._running = False
                process_task.cancel()
                # Clean disconnect
                unsubscribe_msg = {
                    "event": "unsubscribe",
                    "data": {"ticker": [s.lower() for s in symbols]}
                }
                await websocket.send(json.dumps(unsubscribe_msg))
    
    async def _process_messages(self) -> None:
        """Process incoming WebSocket messages"""
        while self._running and self._websocket:
            try:
                message = await self._websocket.recv()
                data = json.loads(message)
                for msg in self._normalize_message(data):
                    self.update_price_data(msg)
            except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError):
                break
            except Exception:
                continue
    
    def stop(self) -> None:
        """Stop the price streaming"""
        self._running = False
    
    async def run_with_callback(self, symbols: List[str], callback: callable) -> None:
        """Run streamer with a callback function
        
        Args:
            symbols: List of stock symbols to track
            callback: Function to call with price data
        """
        async for prices in self.stream_prices(symbols):
            callback(prices)


async def example_usage():
    """Example of how to use the PriceStreamer with returns tracking"""
    api_key = os.getenv("FMP_API_KEY")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "CRWD"]
    
    if not api_key:
        return
    
    streamer = PriceStreamer(api_key)
    
    # Initialize DataFrame columns
    columns = ['timestamp'] + [f'{sym}_price' for sym in symbols] + \
              [f'{sym}_return' for sym in symbols] + \
              [f'{sym}_cum_return' for sym in symbols]
    
    returns_df = pd.DataFrame(columns=columns)
    initial_prices = {}
    previous_prices = {}
    
    # Start cumulative returns at 0
    initial_row = {'timestamp': datetime.now()}
    for sym in symbols:
        initial_row[f'{sym}_price'] = 0.0
        initial_row[f'{sym}_return'] = 0.0
        initial_row[f'{sym}_cum_return'] = 0.0
    returns_df = pd.concat([returns_df, pd.DataFrame([initial_row])], ignore_index=True)
    
    # Stream prices and calculate returns
    async for price_data in streamer.stream_prices(symbols):
        row_data = {'timestamp': datetime.now()}
        
        for symbol in symbols:
            if symbol in price_data:
                current_price = price_data[symbol]['price']
                
                # Store current price
                row_data[f'{symbol}_price'] = current_price
                
                # Set initial price on first real data
                if symbol not in initial_prices and current_price > 0:
                    initial_prices[symbol] = current_price
                    previous_prices[symbol] = current_price
                
                # Calculate returns
                if symbol in initial_prices and current_price > 0:
                    # Period return (from previous price)
                    period_return = ((current_price - previous_prices[symbol]) / previous_prices[symbol]) * 100
                    row_data[f'{symbol}_return'] = period_return
                    
                    # Cumulative return (from initial price)
                    cum_return = ((current_price - initial_prices[symbol]) / 
                                initial_prices[symbol]) * 100
                    row_data[f'{symbol}_cum_return'] = cum_return
                    
                    # Update previous price
                    previous_prices[symbol] = current_price
                else:
                    row_data[f'{symbol}_return'] = 0.0
                    row_data[f'{symbol}_cum_return'] = 0.0
            else:
                row_data[f'{symbol}_price'] = 0.0
                row_data[f'{symbol}_return'] = 0.0
                row_data[f'{symbol}_cum_return'] = 0.0
        
        # Add row to DataFrame
        returns_df = pd.concat([returns_df, pd.DataFrame([row_data])], ignore_index=True)
        
        # Display current state
        print(f"\n{'='*80}")
        print(f"Update at {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")
        
        # Show latest returns
        print("\nLatest Returns (%):")
        for symbol in symbols:
            if f'{symbol}_price' in row_data and row_data[f'{symbol}_price'] > 0:
                print(f"  {symbol:6} - Price: ${row_data[f'{symbol}_price']:8.2f} | "
                      f"Return: {row_data[f'{symbol}_return']:+6.3f}% | "
                      f"Cum Return: {row_data[f'{symbol}_cum_return']:+6.3f}%")
        
        # Show DataFrame summary
        print(f"\nDataFrame shape: {returns_df.shape}")
        print("Last 3 rows:")
        display_cols = ['timestamp'] + [f'{sym}_cum_return' for sym in symbols]
        print(returns_df[display_cols].tail(3).to_string())
        
    return returns_df

def main():
    """Main entry point for price streaming"""
    api_key = os.getenv("FMP_API_KEY")
    
    if not api_key:
        print("FMP_API_KEY not found")
        return
    
    # Run the example and get the returns DataFrame
    returns_df = asyncio.run(example_usage())
    
    if returns_df is not None:
        print("\n" + "="*80)
        print("FINAL RETURNS DATAFRAME")
        print("="*80)
        print(f"Total rows collected: {len(returns_df)}")
        print("\nFull DataFrame:")
        print(returns_df.to_string())


if __name__ == "__main__":
    main()