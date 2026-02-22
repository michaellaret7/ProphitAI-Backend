"""
Alpaca Broker Options Service
Handles options chains, quotes, snapshots, bars, contract discovery.

Mirrors: app/brokers/alpaca/options.py
Key difference: Market data is global (no account_id needed). The option
data client is shared across all accounts. Trading options uses the
BrokerTrading module (which requires account_id).
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
import re

from alpaca.broker.client import BrokerClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.requests import (
    OptionChainRequest,
    OptionBarsRequest,
    OptionLatestQuoteRequest,
    OptionSnapshotRequest,
)
from alpaca.data.timeframe import TimeFrame

try:
    import pandas as pd
except ImportError:
    pd = None


# ---------- OSI decode helpers ----------
_OSI = re.compile(r"^([A-Z0-9.\-]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")


def decode_osi(symbol: str):
    """
    Return (root, expiration 'YYYY-MM-DD', 'call'|'put', strike_float) from OSI;
    (None, None, None, None) if not parseable.
    """
    m = _OSI.match(symbol)
    if not m:
        return None, None, None, None
    root, yy, mm, dd, cp, strike8 = m.groups()
    yyyy = 2000 + int(yy)
    exp = date(yyyy, int(mm), int(dd)).isoformat()
    strike = int(strike8) / 1000.0
    opt_type = "call" if cp == "C" else "put"
    return root, exp, opt_type, strike


class BrokerOptionsService:
    """
    Options helper for Broker API.
    Market data methods (chains, bars, quotes, snapshots) are account-agnostic.
    Contract queries use the BrokerClient.
    """

    def __init__(
        self,
        broker_client: BrokerClient,
        option_data_client: OptionHistoricalDataClient,
        feed: str = "indicative",
    ):
        self.broker_client = broker_client
        self.data = option_data_client
        self.feed = "opra" if str(feed).lower().startswith("opra") else "indicative"

    @staticmethod
    def _norm_exp_str(exp) -> Optional[str]:
        """Return YYYY-MM-DD for date/datetime/str inputs; None if missing."""
        if exp is None:
            return None
        if isinstance(exp, date) and not isinstance(exp, datetime):
            return exp.isoformat()
        if isinstance(exp, datetime):
            return exp.date().isoformat()
        s = str(exp)
        return s[:10] if len(s) >= 10 else s

    # ---------- Contract pagination ----------

    def _iter_contract_pages(self, req) -> list:
        """Yield all option_contracts across pages."""
        all_contracts = []
        resp = self.broker_client.get_option_contracts(req)
        while True:
            all_contracts.extend(getattr(resp, "option_contracts", []) or [])
            nxt = getattr(resp, "next_page_token", None)
            if not nxt:
                break
            if hasattr(req, "page_token"):
                req.page_token = nxt
            else:
                break
            resp = self.broker_client.get_option_contracts(req)
        return all_contracts

    def _build_contract_map(
        self,
        underlying: str,
        exp_gte: Optional[str] = None,
        exp_lte: Optional[str] = None,
        status: Optional[str] = "active",
    ):
        """Returns dict: { symbol: (expiration 'YYYY-MM-DD', strike, 'call'|'put') }"""
        req = GetOptionContractsRequest(underlying_symbols=[underlying])
        if exp_gte and hasattr(req, "expiration_date_gte"):
            req.expiration_date_gte = exp_gte
        if exp_lte and hasattr(req, "expiration_date_lte"):
            req.expiration_date_lte = exp_lte
        if status and hasattr(req, "status"):
            req.status = status
        if hasattr(req, "limit"):
            req.limit = 1000

        contracts = self._iter_contract_pages(req)
        cmap = {}
        for c in contracts:
            sym = getattr(c, "symbol", None)
            if not sym:
                continue
            exp = self._norm_exp_str(getattr(c, "expiration_date", None))
            strike = getattr(c, "strike_price", None)
            ctype = getattr(c, "type", None) or getattr(c, "contract_type", None)
            ctype_val = getattr(ctype, "value", str(ctype)).lower() if ctype else None
            cmap[sym] = (exp, strike, ctype_val)
        return cmap

    # ── Available Expiration Dates ────────────────────────────────

    def get_available_dates(
        self,
        underlying: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        include_expired: bool = False,
        use_chain_fallback: bool = True,
    ) -> List[str]:
        """
        Returns sorted list of unique expiration dates (YYYY-MM-DD) for the given underlying.
        """
        exp_set: set = set()

        req = GetOptionContractsRequest(underlying_symbols=[underlying])
        if not include_expired and hasattr(req, "status"):
            req.status = "active"
        if start and hasattr(req, "expiration_date_gte"):
            req.expiration_date_gte = start
        if end and hasattr(req, "expiration_date_lte"):
            req.expiration_date_lte = end
        if hasattr(req, "limit"):
            req.limit = 1000

        contracts = self._iter_contract_pages(req)

        for c in contracts:
            exp = self._norm_exp_str(getattr(c, "expiration_date", None))
            if not exp:
                continue
            if start and exp < start:
                continue
            if end and exp > end:
                continue
            exp_set.add(exp)

        if not exp_set and use_chain_fallback:
            chain_resp = self.data.get_option_chain(
                OptionChainRequest(
                    underlying_symbol=underlying,
                    feed=self.feed,
                    limit=5000,
                )
            )
            items = chain_resp.items() if isinstance(chain_resp, dict) else []
            for sym, _snap in items:
                _, exp2, _typ2, _k2 = decode_osi(sym)
                if not exp2:
                    continue
                if start and exp2 < start:
                    continue
                if end and exp2 > end:
                    continue
                exp_set.add(exp2)

        return sorted(exp_set)

    # ── Available Contracts ───────────────────────────────────────

    def get_available_contracts(
        self,
        underlying: str,
        expiration: Optional[str] = None,
        contract_type: Optional[str] = None,
        strike_range: Optional[Tuple[float, float]] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """
        Discover available option contracts (OSI symbols).

        Args:
            underlying: Root symbol (e.g. 'AAPL')
            expiration: Filter to a specific expiration (YYYY-MM-DD)
            contract_type: 'call' or 'put'
            strike_range: (min_strike, max_strike) tuple
            status: 'active' or None
            limit: Max number of contracts to return
        """
        req = GetOptionContractsRequest(underlying_symbols=[underlying])
        if expiration:
            if hasattr(req, "expiration_date_gte"):
                req.expiration_date_gte = expiration
            if hasattr(req, "expiration_date_lte"):
                req.expiration_date_lte = expiration
        if status and hasattr(req, "status"):
            req.status = status
        if hasattr(req, "limit"):
            req.limit = 1000

        contracts = self._iter_contract_pages(req)

        out: List[str] = []
        for c in contracts:
            sym = getattr(c, "symbol", None)
            if not sym:
                continue
            u_sym = getattr(c, "underlying_symbol", None)
            if u_sym and u_sym != underlying:
                continue
            exp = self._norm_exp_str(getattr(c, "expiration_date", None))
            if expiration and exp != expiration:
                continue
            ctype = getattr(c, "type", None) or getattr(c, "contract_type", None)
            if contract_type:
                ctype_val = getattr(ctype, "value", str(ctype)).lower() if ctype else ""
                if ctype_val != contract_type.lower():
                    continue
            cstatus = getattr(c, "status", None)
            if status:
                status_val = getattr(cstatus, "value", str(cstatus)).lower() if cstatus else ""
                if status_val != status.lower():
                    continue
            strike = getattr(c, "strike_price", None)
            if strike_range and strike is not None:
                lo, hi = strike_range
                if not (lo <= float(strike) <= hi):
                    continue
            out.append(sym)
            if limit and len(out) >= limit:
                break

        # Fallback: derive from Option Chain
        if not out:
            chain_resp = self.data.get_option_chain(
                OptionChainRequest(
                    underlying_symbol=underlying,
                    expiration_date=expiration,
                    feed=self.feed,
                    limit=limit,
                )
            )
            for sym, _snap in (chain_resp.items() if isinstance(chain_resp, dict) else []):
                _, exp2, typ2, k2 = decode_osi(sym)
                if expiration and exp2 != expiration:
                    continue
                if contract_type and (typ2 or "").lower() != contract_type.lower():
                    continue
                if strike_range and k2 is not None:
                    lo, hi = strike_range
                    if not (lo <= float(k2) <= hi):
                        continue
                out.append(sym)
                if limit and len(out) >= limit:
                    break

        return out

    # ── Options Chain (quotes + greeks) ───────────────────────────

    def get_options_chain(
        self,
        underlying: str,
        expiration: Optional[str] = None,
        limit: Optional[int] = None,
        return_df: Optional[bool] = None,
        use_contract_join: bool = True,
    ):
        """
        Fetch options chain with quotes and greeks.

        Args:
            underlying: Root symbol
            expiration: Filter to specific expiration (YYYY-MM-DD)
            limit: Max contracts to return
            return_df: Return pandas DataFrame (default True if pandas available)
            use_contract_join: Enrich snapshots with contract metadata
        """
        if return_df is None:
            return_df = pd is not None

        cmap = {}
        if use_contract_join:
            cmap = self._build_contract_map(
                underlying,
                exp_gte=expiration,
                exp_lte=expiration,
                status="active",
            )

        resp = self.data.get_option_chain(
            OptionChainRequest(
                underlying_symbol=underlying,
                expiration_date=expiration,
                feed=self.feed,
                limit=limit,
            )
        )

        items = resp.items() if isinstance(resp, dict) else []

        rows = []
        for sym, snap in items:
            strike = getattr(snap, "strike_price", None)
            exp_raw = getattr(snap, "expiration_date", None)
            exp = self._norm_exp_str(exp_raw)
            ctype = getattr(snap, "contract_type", None)
            ctype_val = getattr(ctype, "value", str(ctype)).lower() if ctype else None

            if sym in cmap:
                exp = exp or cmap[sym][0]
                strike = strike if strike is not None else cmap[sym][1]
                ctype_val = ctype_val or cmap[sym][2]

            if strike is None or exp is None or ctype_val is None:
                _, exp2, t2, k2 = decode_osi(sym)
                exp = exp or exp2
                ctype_val = ctype_val or t2
                if strike is None:
                    strike = k2

            q = getattr(snap, "latest_quote", None)
            t = getattr(snap, "latest_trade", None)
            g = getattr(snap, "greeks", None)

            bid = getattr(q, "bid_price", None) if q else None
            ask = getattr(q, "ask_price", None) if q else None
            mid = (float(bid) + float(ask)) / 2.0 if (bid is not None and ask is not None) else None

            rows.append({
                "symbol": sym,
                "underlying": underlying,
                "expiration": exp,
                "strike": float(strike) if strike is not None else None,
                "type": ctype_val,
                "bid": bid, "ask": ask, "mid": mid,
                "last": getattr(t, "price", None) if t else None,
                "delta": getattr(g, "delta", None) if g else None,
                "gamma": getattr(g, "gamma", None) if g else None,
                "theta": getattr(g, "theta", None) if g else None,
                "vega": getattr(g, "vega", None) if g else None,
                "iv": getattr(g, "implied_volatility", None) if g else None,
            })

        if return_df and pd is not None:
            df = pd.DataFrame(rows)
            sort_cols = [c for c in ["expiration", "strike", "type"] if c in df.columns]
            return df.sort_values(sort_cols) if not df.empty and sort_cols else df
        return rows

    # ── Option Bars (OHLCV history) ───────────────────────────────

    _TIMEFRAME_MAP = {
        "1min": TimeFrame.Minute,
        "1h": TimeFrame.Hour,
        "1d": TimeFrame.Day,
        "1w": TimeFrame.Week,
        "1m": TimeFrame.Month,
    }

    def get_option_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get OHLCV bars for an option contract.

        Args:
            symbol: OSI option symbol (e.g., 'SPY260320C00580000')
            timeframe: '1min', '1h', '1d', '1w', '1m'
            start: Start date/datetime ISO string
            end: End date/datetime ISO string
            limit: Max bars to return
        """
        tf = self._TIMEFRAME_MAP.get(timeframe.lower(), TimeFrame.Day)
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None

        request = OptionBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start_dt,
            end=end_dt,
            limit=limit,
        )

        bars = self.data.get_option_bars(request)
        try:
            symbol_bars = bars[symbol]
        except (KeyError, IndexError):
            symbol_bars = []

        return [
            {
                "timestamp": str(bar.timestamp),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
                "vwap": float(bar.vwap) if bar.vwap else None,
                "trade_count": int(bar.trade_count) if bar.trade_count else None,
            }
            for bar in symbol_bars
        ]

    # ── Option Latest Quote ───────────────────────────────────────

    def get_option_latest_quote(self, symbol: str) -> Dict:
        """Get the latest bid/ask quote for an option contract (OSI symbol)."""
        request = OptionLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = self.data.get_option_latest_quote(request)

        if symbol not in quotes:
            raise ValueError(f"No quote data returned for {symbol}")

        q = quotes[symbol]
        return {
            "symbol": symbol,
            "bid_price": float(q.bid_price) if q.bid_price is not None else None,
            "bid_size": float(q.bid_size) if q.bid_size is not None else None,
            "ask_price": float(q.ask_price) if q.ask_price is not None else None,
            "ask_size": float(q.ask_size) if q.ask_size is not None else None,
            "timestamp": str(q.timestamp),
        }

    # ── Option Snapshot (quote + trade + greeks) ──────────────────

    def get_option_snapshot(self, symbol: str) -> Dict:
        """Get a full snapshot (quote + trade + greeks) for an option contract."""
        request = OptionSnapshotRequest(symbol_or_symbols=symbol)
        snapshots = self.data.get_option_snapshot(request)

        if symbol not in snapshots:
            raise ValueError(f"No snapshot data returned for {symbol}")

        snap = snapshots[symbol]
        result: Dict = {"symbol": symbol}

        if hasattr(snap, "latest_quote") and snap.latest_quote:
            q = snap.latest_quote
            result["quote"] = {
                "bid_price": float(q.bid_price) if q.bid_price is not None else None,
                "bid_size": float(q.bid_size) if q.bid_size is not None else None,
                "ask_price": float(q.ask_price) if q.ask_price is not None else None,
                "ask_size": float(q.ask_size) if q.ask_size is not None else None,
                "timestamp": str(q.timestamp),
            }

        if hasattr(snap, "latest_trade") and snap.latest_trade:
            t = snap.latest_trade
            result["trade"] = {
                "price": float(t.price) if t.price is not None else None,
                "size": float(t.size) if t.size is not None else None,
                "timestamp": str(t.timestamp),
            }

        if hasattr(snap, "greeks") and snap.greeks:
            g = snap.greeks
            result["greeks"] = {
                "delta": g.delta,
                "gamma": g.gamma,
                "theta": g.theta,
                "vega": g.vega,
                "rho": g.rho,
            }

        return result
