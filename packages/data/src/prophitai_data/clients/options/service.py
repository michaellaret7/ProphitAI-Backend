# prophitai_data/clients/options/service.py

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
import re
from prophitai_data.clients.options.client import AlpacaClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
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

# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

# Format: {UNDERLYING}{YY}{MM}{DD}{C|P}{STRIKE*1000 8-digits}
_OSI = re.compile(r"^([A-Z0-9.\-]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")


def decode_osi(symbol: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[float]]:
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

# ════════════════════════════════════════════════════════════
# --> OptionsService
# ════════════════════════════════════════════════════════════

class OptionsService:
    """Options helper that reuses AlpacaClient for contracts, chains, bars, quotes, and snapshots."""

    def __init__(self, alpaca: AlpacaClient, feed: str = "indicative"):
        self.alpaca = alpaca
        self.trading = alpaca.get_client()  # trading client from client.py
        self.data = OptionHistoricalDataClient(alpaca.api_key, alpaca.secret_key)
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

    # ---------- optional: build a symbol -> (exp, strike, type) map from Trading API ----------
    def _build_contract_map(
        self,
        underlying: str,
        exp_gte: Optional[str] = None,
        exp_lte: Optional[str] = None,
        status: Optional[str] = "active",
    ):
        """
        Returns dict: { symbol: (expiration 'YYYY-MM-DD', strike, 'call'|'put') }
        """
        req = GetOptionContractsRequest(underlying_symbols=[underlying])
        # set filters if available on current SDK version
        if exp_gte and hasattr(req, "expiration_date_gte"):
            req.expiration_date_gte = exp_gte
        if exp_lte and hasattr(req, "expiration_date_lte"):
            req.expiration_date_lte = exp_lte
        if status and hasattr(req, "status"):
            req.status = status
        if hasattr(req, "limit"):
            req.limit = 1000  # bigger page size; we still paginate

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

    def _iter_contract_pages(self, req) -> list:
        """Yield all option_contracts across pages."""
        all_contracts = []
        resp = self.trading.get_option_contracts(req)
        while True:
            all_contracts.extend(getattr(resp, "option_contracts", []) or [])
            nxt = getattr(resp, "next_page_token", None)
            if not nxt:
                break
            # carry the page token forward if supported by the SDK
            if hasattr(req, "page_token"):
                req.page_token = nxt
            else:
                break
            resp = self.trading.get_option_contracts(req)
        return all_contracts

    # ---------------------------
    # List all available expiration dates for an underlying
    # ---------------------------
    def get_available_dates(
        self,
        underlying: str,
        start: Optional[str] = None,       # "YYYY-MM-DD" inclusive (optional)
        end: Optional[str] = None,         # "YYYY-MM-DD" inclusive (optional)
        include_expired: bool = False,     # False -> active only
        use_chain_fallback: bool = True,   # also scrape expiries from option chain if needed
    ) -> List[str]:
        """
        Returns a sorted list of unique expiration dates (YYYY-MM-DD) for the given underlying.
        - Uses Trading API (GetOptionContracts) with pagination.
        - Optionally falls back to the Option Chain by decoding OSI symbols (robust).
        - You can constrain by start/end dates if desired (inclusive).
        """
        exp_set: set[str] = set()

        # ---- 1) Trading API: paginate contracts & collect expirations
        req = GetOptionContractsRequest(underlying_symbols=[underlying])

        # Server-side filters where supported by the SDK
        if not include_expired and hasattr(req, "status"):
            req.status = "active"  # avoid expired contracts
        if start and hasattr(req, "expiration_date_gte"):
            req.expiration_date_gte = start
        if end and hasattr(req, "expiration_date_lte"):
            req.expiration_date_lte = end
        if hasattr(req, "limit"):
            req.limit = 1000  # larger page size; we still paginate

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

        # ---- 2) Fallback: scrape expirations from Option Chain if Trading returned nothing
        if not exp_set and use_chain_fallback:
            # Ask chain for many contracts (no specific expiration)
            chain_resp = self.data.get_option_chain(
                OptionChainRequest(
                    underlying_symbol=underlying,
                    feed=self.feed,
                    # limit is SDK-dependent; passing a big number often works,
                    # but omit if your SDK doesn't accept it.
                    limit=5000,
                )
            )
            items = chain_resp.items() if isinstance(chain_resp, dict) else []
            for sym, _snap in items:
                # Decode OSI to get expiration
                _, exp2, _typ2, _k2 = decode_osi(sym)
                if not exp2:
                    continue
                if start and exp2 < start:
                    continue
                if end and exp2 > end:
                    continue
                exp_set.add(exp2)

        # Return sorted list
        return sorted(exp_set)

    # ---------------------------
    # 1) Discover available contracts (OSI symbols)
    # ---------------------------
    def get_available_contracts(
        self,
        underlying: str,
        expiration: Optional[str] = None,              # "YYYY-MM-DD"
        contract_type: Optional[str] = None,           # "call" | "put"
        strike_range: Optional[Tuple[float, float]] = None,  # (min, max)
        status: Optional[str] = None,                  # "active" or None for any
        limit: Optional[int] = None,
    ) -> List[str]:
        # 1) Build request and push filters server-side where possible
        req = GetOptionContractsRequest(underlying_symbols=[underlying])

        if expiration:
            if hasattr(req, "expiration_date_gte"):
                req.expiration_date_gte = expiration
            if hasattr(req, "expiration_date_lte"):
                req.expiration_date_lte = expiration
        if status and hasattr(req, "status"):
            req.status = status
        if hasattr(req, "limit"):
            req.limit = 1000  # large page size; we'll still paginate

        # 2) Fetch *all* pages
        contracts = self._iter_contract_pages(req)

        # 3) Client-side filtering to be robust across SDK changes
        out: List[str] = []
        want_exp = expiration  # "YYYY-MM-DD"
        for c in contracts:
            sym = getattr(c, "symbol", None)
            if not sym:
                continue

            u_sym = getattr(c, "underlying_symbol", None)
            if u_sym and u_sym != underlying:
                continue

            # expiration
            exp = self._norm_exp_str(getattr(c, "expiration_date", None))
            if want_exp and exp != want_exp:
                continue

            # type
            ctype = getattr(c, "type", None) or getattr(c, "contract_type", None)
            if contract_type:
                ctype_val = getattr(ctype, "value", str(ctype)).lower() if ctype else ""
                if ctype_val != contract_type.lower():
                    continue

            # status
            cstatus = getattr(c, "status", None)
            if status:
                status_val = getattr(cstatus, "value", str(cstatus)).lower() if cstatus else ""
                if status_val != status.lower():
                    continue

            # strike range
            strike = getattr(c, "strike_price", None)
            if strike_range and strike is not None:
                lo, hi = strike_range
                if not (lo <= float(strike) <= hi):
                    continue

            out.append(sym)
            if limit and len(out) >= limit:
                break

        # 4) Fallback: derive from Option Chain if Trading contracts are empty
        if not out:
            chain_resp = self.data.get_option_chain(
                OptionChainRequest(
                    underlying_symbol=underlying,
                    expiration_date=expiration,   # if None, will return many expiries
                    feed=self.feed,
                    limit=limit,
                )
            )
            for sym, _snap in (chain_resp.items() if isinstance(chain_resp, dict) else []):
                _, exp2, typ2, k2 = decode_osi(sym)
                if want_exp and exp2 != want_exp:
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

    # ---------------------------
    # 2) Fetch options chain (quotes + greeks)
    # ---------------------------
    def get_options_chain(
        self,
        underlying: str,
        expiration: str | None = None,  # "YYYY-MM-DD"
        limit: int | None = None,
        return_df: bool | None = None,
        use_contract_join: bool = True,  # join against Trading contracts to fill metadata
    ):
        if return_df is None:
            return_df = pd is not None

        # Optionally build a contracts map to enrich snapshots
        cmap = {}
        if use_contract_join:
            # If a single expiry is passed, limit the join to that date (faster)
            cmap = self._build_contract_map(
                underlying,
                exp_gte=expiration,
                exp_lte=expiration,
                status="active",
            )

        resp = self.data.get_option_chain(
            OptionChainRequest(
                underlying_symbol=underlying,
                expiration_date=expiration,   # exact day (omit for many expiries)
                feed=self.feed,               # "indicative" or "opra"
                limit=limit,
            )
        )

        # resp is dict: { "AAPL251024C00150000": OptionsSnapshot, ... }
        items = resp.items() if isinstance(resp, dict) else []

        rows = []
        for sym, snap in items:
            # --- metadata, as provided by snapshot (often None on indicative)
            strike = getattr(snap, "strike_price", None)
            exp_raw = getattr(snap, "expiration_date", None)
            exp = self._norm_exp_str(exp_raw)
            ctype = getattr(snap, "contract_type", None)
            ctype_val = getattr(ctype, "value", str(ctype)).lower() if ctype else None

            # --- fill from contracts map if missing
            if sym in cmap:
                exp = exp or cmap[sym][0]
                strike = strike if strike is not None else cmap[sym][1]
                ctype_val = ctype_val or cmap[sym][2]

            # --- final backstop: decode from OSI
            if strike is None or exp is None or ctype_val is None:
                _, exp2, t2, k2 = decode_osi(sym)
                exp = exp or exp2
                ctype_val = ctype_val or t2
                if strike is None:
                    strike = k2

            # --- market data
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
                "type": ctype_val,  # "call"/"put"
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

    # ── Option bars (OHLCV history) ──

    _TIMEFRAME_MAP = {
        '1min': TimeFrame.Minute,
        '1h': TimeFrame.Hour,
        '1d': TimeFrame.Day,
        '1w': TimeFrame.Week,
        '1m': TimeFrame.Month,
    }

    def get_option_bars(
        self,
        symbol: str,
        timeframe: str = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get OHLCV bars for an option contract.

        Args:
            symbol: OSI option symbol (e.g., 'SPY260320C00580000')
            timeframe: '1min', '1h', '1d', '1w', '1m'
            start: Start date/datetime ISO string (optional)
            end: End date/datetime ISO string (optional)
            limit: Max number of bars to return
        """
        tf = self._TIMEFRAME_MAP.get(timeframe.lower(), TimeFrame.Day)
        # Reason: SDK types expect datetime but accepts ISO strings at runtime
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
        # Reason: BarSet.__contains__ is broken in alpaca-py — use subscript with fallback
        try:
            symbol_bars = bars[symbol]
        except (KeyError, IndexError):
            symbol_bars = []

        return [
            {
                'timestamp': str(bar.timestamp),
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': float(bar.volume),
                'vwap': float(bar.vwap) if bar.vwap else None,
                'trade_count': int(bar.trade_count) if bar.trade_count else None,
            }
            for bar in symbol_bars
        ]

    # ── Option latest quote (real-time bid/ask) ──
    def get_option_latest_quote(self, symbol: str) -> Dict:
        """Get the latest bid/ask quote for an option contract (OSI symbol)."""
        request = OptionLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = self.data.get_option_latest_quote(request)

        if symbol not in quotes:
            raise ValueError(f"No quote data returned for {symbol}")

        q = quotes[symbol]
        return {
            'symbol': symbol,
            'bid_price': float(q.bid_price) if q.bid_price is not None else None,
            'bid_size': float(q.bid_size) if q.bid_size is not None else None,
            'ask_price': float(q.ask_price) if q.ask_price is not None else None,
            'ask_size': float(q.ask_size) if q.ask_size is not None else None,
            'timestamp': str(q.timestamp),
        }

    # ── Option snapshot (quote + trade + greeks) ──
    def get_option_snapshot(self, symbol: str) -> Dict:
        """Get a full snapshot (quote + trade + greeks) for an option contract (OSI symbol)."""
        request = OptionSnapshotRequest(symbol_or_symbols=symbol)
        snapshots = self.data.get_option_snapshot(request)

        if symbol not in snapshots:
            raise ValueError(f"No snapshot data returned for {symbol}")

        snap = snapshots[symbol]
        result: Dict = {'symbol': symbol}

        if hasattr(snap, 'latest_quote') and snap.latest_quote:
            q = snap.latest_quote
            result['quote'] = {
                'bid_price': float(q.bid_price) if q.bid_price is not None else None,
                'bid_size': float(q.bid_size) if q.bid_size is not None else None,
                'ask_price': float(q.ask_price) if q.ask_price is not None else None,
                'ask_size': float(q.ask_size) if q.ask_size is not None else None,
                'timestamp': str(q.timestamp),
            }

        if hasattr(snap, 'latest_trade') and snap.latest_trade:
            t = snap.latest_trade
            result['trade'] = {
                'price': float(t.price) if t.price is not None else None,
                'size': float(t.size) if t.size is not None else None,
                'timestamp': str(t.timestamp),
            }

        if hasattr(snap, 'greeks') and snap.greeks:
            g = snap.greeks
            result['greeks'] = {
                'delta': g.delta,
                'gamma': g.gamma,
                'theta': g.theta,
                'vega': g.vega,
                'rho': g.rho,
            }

        return result
