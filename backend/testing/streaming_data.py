#!/usr/bin/env python3
"""
FMP WebSocket Real-Time Stock Streamer
Streams real-time stock data using WebSocket connection
"""

import asyncio
import json
import os
import websockets
import ssl
import certifi
import math
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from backend.src.calculations_v2.core.helpers import pct_change

load_dotenv()

# Create an SSL context using certifi's CA bundle to avoid macOS cert issues
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

class FMPWebSocketStreamer:
    def __init__(self, api_key: str):
        """Initialize the WebSocket streamer
        
        Args:
            api_key: Your FMP API key
        """
        self.api_key = api_key
        self.ws_url = "wss://websockets.financialmodelingprep.com"
        self.last_update = {}
        self.update_interval = 1  # Display updates every 5 seconds
        self.changed_symbols = set()
        # Alerts config: {SYMBOL: {"threshold_pct": float, "baseline": Optional[float], "triggered": bool}}
        self.alerts: Dict[str, Dict[str, Any]] = {}
        
    @staticmethod
    def _normalize_message(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize incoming websocket payloads to a list of flat quote dicts.
        Handles variations in FMP payload structure.
        """
        def to_list(payload: Any) -> List[Dict[str, Any]]:
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                return [payload]
            return []

        # Many FMP messages wrap data under 'data' or 'd'
        payload = raw.get('data', raw.get('d', raw))
        items = to_list(payload)
        return items

    @staticmethod
    def _extract_fields(message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract symbol, price, bid/ask and sizes from a single message variant."""
        # Symbol keys variants
        symbol = (
            message.get('s')
            or message.get('symbol')
            or message.get('ticker')
        )

        # Price variants
        price = (
            message.get('p')
            or message.get('price')
            or message.get('lp')
            or message.get('last')
            or message.get('lastPrice')
            or message.get('c')
        )

        # Bid/Ask variants
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

        # Sizes variants
        bid_size = (
            message.get('bs')
            or message.get('bidSize')
            or message.get('bSize')
        )
        ask_size = (
            message.get('as')
            or message.get('askSize')
            or message.get('aSize')
        )

        def to_float(value: Any) -> float:
            try:
                if value is None:
                    return 0.0
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        def to_int(value: Any) -> int:
            try:
                if value is None:
                    return 0
                return int(value)
            except (TypeError, ValueError):
                return 0

        result = {
            'symbol': symbol.upper() if isinstance(symbol, str) else None,
            'price': to_float(price),
            'bid': to_float(bid),
            'ask': to_float(ask),
            'bid_size': to_int(bid_size),
            'ask_size': to_int(ask_size)
        }
        return result

    async def connect_and_stream(self, symbols: List[str]):
        """Connect to WebSocket and stream data
        
        Args:
            symbols: List of stock symbols to track
        """
        async with websockets.connect(self.ws_url, ssl=SSL_CONTEXT) as websocket:
            # Login with API key
            login_msg = {
                "event": "login",
                "data": {
                    "apiKey": self.api_key
                }
            }
            await websocket.send(json.dumps(login_msg))
            
            # Wait for login confirmation
            response = await websocket.recv()
            print(f"Login response: {response}")
            
            # Subscribe to symbols
            subscribe_msg = {
                "event": "subscribe",
                "data": {
                    "ticker": [s.lower() for s in symbols]
                }
            }
            await websocket.send(json.dumps(subscribe_msg))
            print(f"Subscribed to: {', '.join(symbols)}")
            print("-" * 80)
            
            # Create task for periodic display
            display_task = asyncio.create_task(self.periodic_display())
            
            try:
                # Receive and process messages
                async for message in websocket:
                    data = json.loads(message)
                    # Handle possibly wrapped/array payloads
                    for msg in self._normalize_message(data):
                        self.process_message(msg)
                    
            except KeyboardInterrupt:
                print("\nStream stopped by user")
            finally:
                display_task.cancel()
                # Unsubscribe before closing
                unsubscribe_msg = {
                    "event": "unsubscribe",
                    "data": {
                        "ticker": [s.lower() for s in symbols]
                    }
                }
                await websocket.send(json.dumps(unsubscribe_msg))
    
    def process_message(self, data: Dict[str, Any]):
        """Process incoming WebSocket message
        
        Args:
            data: Message data from WebSocket
        """
        fields = self._extract_fields(data)
        symbol = fields.get('symbol')
        if symbol:
            # Merge with existing to preserve values when some fields are missing
            existing = self.last_update.get(symbol, {})
            merged = {
                'price': fields['price'] or existing.get('price', 0.0),
                'bid': fields['bid'] or existing.get('bid', 0.0),
                'ask': fields['ask'] or existing.get('ask', 0.0),
                'bid_size': fields['bid_size'] or existing.get('bid_size', 0),
                'ask_size': fields['ask_size'] or existing.get('ask_size', 0),
                'timestamp': datetime.now()
            }
            self.last_update[symbol] = merged
            self.changed_symbols.add(symbol)
            # Check any registered alerts for this symbol
            if symbol in self.alerts and merged['price'] > 0:
                self._check_price_alert(symbol, merged['price'])

    def set_percent_above_alert(self, symbol: str, percent_decimal: float):
        """Register an alert to print a trade when price rises percent above baseline.
        Baseline is set on first seen non-zero price after registration.
        """
        sym = str(symbol).upper()
        self.alerts[sym] = {
            "threshold_pct": float(percent_decimal),
            "baseline": None,
            "triggered": False,
        }

    def _check_price_alert(self, symbol: str, current_price: float):
        cfg = self.alerts.get(symbol)
        if not cfg:
            return
        baseline = cfg.get("baseline")
        if baseline is None:
            cfg["baseline"] = float(current_price)
            print(f"Baseline set for {symbol}: ${current_price:.2f}")
            return
        change = pct_change(current_price, baseline, scale=1.0)
        if change is None or (isinstance(change, float) and math.isnan(change)):
            return
        if not cfg.get("triggered") and change >= float(cfg.get("threshold_pct", 0.0)):
            pct_str = change * 100.0
            print(f"TRADE: {symbol} +{pct_str:.2f}% from ${baseline:.2f} → ${current_price:.2f}")
            cfg["triggered"] = True
    
    async def periodic_display(self):
        """Periodically display the latest data"""
        while True:
            await asyncio.sleep(self.update_interval)
            
            if self.changed_symbols:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Latest Updates:")
                
                for symbol in sorted(self.changed_symbols):
                    data = self.last_update.get(symbol, {})
                    print(f"{symbol:6} | "
                          f"Price: ${data['price']:8.2f} | "
                          f"Bid: ${data['bid']:7.2f} ({data['bid_size']:5}) | "
                          f"Ask: ${data['ask']:7.2f} ({data['ask_size']:5})")
                self.changed_symbols.clear()
    
    def run(self, symbols: List[str]):
        """Run the WebSocket streamer
        
        Args:
            symbols: List of stock symbols to track
        """
        print(f"Starting WebSocket real-time stream...")
        print(f"Tracking symbols: {', '.join(symbols)}")
        print(f"Display interval: {self.update_interval} seconds")
        
        try:
            asyncio.run(self.connect_and_stream(symbols))
        except Exception as e:
            print(f"Error in WebSocket stream: {e}")

def main():
    # Configuration
    API_KEY = os.getenv("FMP_API_KEY")
    SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]  # Symbols to track
    
    # Validate API key
    if not API_KEY:
        print("Error: Missing FMP_API_KEY environment variable.")
        print("Set it in your environment or a .env file, e.g., FMP_API_KEY=your_key")
        print("Get your API key at: https://site.financialmodelingprep.com/developer/docs/pricing")
        return
    
    # Use the class-based WebSocket streamer (preferred for robustness)
    streamer = FMPWebSocketStreamer(API_KEY)
    # Example: alert when AAPL hits 1% above the initial seen price
    streamer.set_percent_above_alert("AAPL", 0.01)
    streamer.run(SYMBOLS)

if __name__ == "__main__":
    main()