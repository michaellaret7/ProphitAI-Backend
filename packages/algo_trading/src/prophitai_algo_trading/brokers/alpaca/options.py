"""Alpaca options service — chains, contracts, expirations, bars, and quotes.

OSI symbol format: ``{ROOT}{YY}{MM}{DD}{C|P}{STRIKE*1000:08d}``.

Trading API ``GetOptionContracts`` is the primary source for contract
metadata (expiration, strike, type) and is paginated. The Option Chain
data API supplies the live snapshots (quote, last trade, greeks). When
metadata is missing on snapshot we fall back first to the contract map,
then to OSI decoding as a last-resort.
"""

from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import (
    OptionBarsRequest,
    OptionChainRequest,
    OptionLatestQuoteRequest,
    OptionSnapshotRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import GetOptionContractsRequest

from prophitai_algo_trading.brokers.alpaca.client import AlpacaClient


_OSI_PATTERN = re.compile(r"^([A-Z0-9.\-]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")

_DEFAULT_PAGE_SIZE = 1000
_DEFAULT_CHAIN_LIMIT = 5000

_TIMEFRAME_MAP = {
    "1min": TimeFrame.Minute,
    "1h": TimeFrame.Hour,
    "1d": TimeFrame.Day,
    "1w": TimeFrame.Week,
    "1m": TimeFrame.Month,
}


#     ================================
# --> Helper funcs
#     ================================

def decode_osi(
    symbol: str,
) -> tuple[str | None, str | None, str | None, float | None]:
    """Decode an OSI option symbol into ``(root, expiration, type, strike)``.

    Returns a tuple of ``None`` values if the symbol does not match the
    OSI grammar.
    """
    match = _OSI_PATTERN.match(symbol)

    if not match:
        return None, None, None, None

    root, yy, mm, dd, cp, strike8 = match.groups()
    yyyy = 2000 + int(yy)
    expiration = date(yyyy, int(mm), int(dd)).isoformat()
    strike = int(strike8) / 1000.0
    opt_type = "call" if cp == "C" else "put"

    return root, expiration, opt_type, strike


def _norm_exp_str(exp) -> str | None:
    """Render a date / datetime / str expiration as ``YYYY-MM-DD``."""
    if exp is None:
        return None

    if isinstance(exp, date) and not isinstance(exp, datetime):
        return exp.isoformat()

    if isinstance(exp, datetime):
        return exp.date().isoformat()

    s = str(exp)

    return s[:10] if len(s) >= 10 else s


def _enum_value_lower(obj) -> str | None:
    """Lower-cased ``.value`` from an SDK enum (or fallback ``str``)."""
    if obj is None:
        return None

    return getattr(obj, "value", str(obj)).lower()


#     ================================
# --> Public service
#     ================================

class OptionsService:
    """Options data + contract discovery on top of the Alpaca SDK."""

    def __init__(self, alpaca: AlpacaClient, feed: str = "indicative"):
        self.alpaca = alpaca
        self.trading = alpaca.get_client()
        self.data = OptionHistoricalDataClient(alpaca.api_key, alpaca.secret_key)
        self.feed = "opra" if str(feed).lower().startswith("opra") else "indicative"

    def _build_contract_map(
        self,
        underlying: str,
        exp_gte: str | None = None,
        exp_lte: str | None = None,
        status: str | None = "active",
    ) -> dict[str, tuple[str | None, float | None, str | None]]:
        """Map ``symbol → (expiration, strike, contract_type)`` for ``underlying``."""
        req = GetOptionContractsRequest(underlying_symbols=[underlying])

        if exp_gte:
            req.expiration_date_gte = exp_gte
        if exp_lte:
            req.expiration_date_lte = exp_lte
        if status:
            req.status = status

        req.limit = _DEFAULT_PAGE_SIZE

        contracts = self._iter_contract_pages(req)

        cmap: dict[str, tuple[str | None, float | None, str | None]] = {}

        for c in contracts:
            sym = getattr(c, "symbol", None)

            if not sym:
                continue

            exp = _norm_exp_str(getattr(c, "expiration_date", None))
            strike = getattr(c, "strike_price", None)
            ctype = getattr(c, "type", None) or getattr(c, "contract_type", None)

            cmap[sym] = (exp, strike, _enum_value_lower(ctype))

        return cmap

    def _iter_contract_pages(self, req: GetOptionContractsRequest) -> list:
        """Walk every page of an option-contracts request, accumulating results."""
        all_contracts: list = []

        resp = self.trading.get_option_contracts(req)

        while True:
            all_contracts.extend(getattr(resp, "option_contracts", []) or [])

            nxt = getattr(resp, "next_page_token", None)

            if not nxt:
                break

            req.page_token = nxt

            resp = self.trading.get_option_contracts(req)

        return all_contracts

    def get_available_dates(
        self,
        underlying: str,
        start: str | None = None,
        end: str | None = None,
        include_expired: bool = False,
        use_chain_fallback: bool = True,
    ) -> list[str]:
        """Sorted unique ``YYYY-MM-DD`` expirations available for ``underlying``.

        Pulls from ``GetOptionContracts`` first; on empty result, optionally
        falls back to scraping expirations from the Option Chain by
        decoding OSI symbols.
        """
        exp_set: set[str] = set()

        req = GetOptionContractsRequest(underlying_symbols=[underlying])

        if not include_expired:
            req.status = "active"
        if start:
            req.expiration_date_gte = start
        if end:
            req.expiration_date_lte = end

        req.limit = _DEFAULT_PAGE_SIZE

        for c in self._iter_contract_pages(req):
            exp = _norm_exp_str(getattr(c, "expiration_date", None))

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
                    limit=_DEFAULT_CHAIN_LIMIT,
                ),
            )

            items = chain_resp.items() if isinstance(chain_resp, dict) else []

            for sym, _snap in items:
                _, exp2, _typ, _strike = decode_osi(sym)

                if not exp2:
                    continue
                if start and exp2 < start:
                    continue
                if end and exp2 > end:
                    continue

                exp_set.add(exp2)

        return sorted(exp_set)

    def get_available_contracts(
        self,
        underlying: str,
        expiration: str | None = None,
        contract_type: str | None = None,
        strike_range: tuple[float, float] | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[str]:
        """List of OSI symbols matching the requested filters."""
        req = GetOptionContractsRequest(underlying_symbols=[underlying])

        if expiration:
            req.expiration_date_gte = expiration
            req.expiration_date_lte = expiration
        if status:
            req.status = status

        req.limit = _DEFAULT_PAGE_SIZE

        contracts = self._iter_contract_pages(req)

        out = self._filter_contracts(
            contracts=contracts,
            underlying=underlying,
            expiration=expiration,
            contract_type=contract_type,
            strike_range=strike_range,
            status=status,
            limit=limit,
        )

        if not out:
            out = self._chain_contract_fallback(
                underlying=underlying,
                expiration=expiration,
                contract_type=contract_type,
                strike_range=strike_range,
                limit=limit,
            )

        return out

    def _filter_contracts(
        self,
        contracts: list,
        underlying: str,
        expiration: str | None,
        contract_type: str | None,
        strike_range: tuple[float, float] | None,
        status: str | None,
        limit: int | None,
    ) -> list[str]:
        out: list[str] = []

        for c in contracts:
            sym = getattr(c, "symbol", None)

            if not sym:
                continue

            u_sym = getattr(c, "underlying_symbol", None)

            if u_sym and u_sym != underlying:
                continue

            exp = _norm_exp_str(getattr(c, "expiration_date", None))

            if expiration and exp != expiration:
                continue

            ctype = getattr(c, "type", None) or getattr(c, "contract_type", None)

            if contract_type:
                ctype_val = _enum_value_lower(ctype) or ""

                if ctype_val != contract_type.lower():
                    continue

            cstatus = getattr(c, "status", None)

            if status:
                status_val = _enum_value_lower(cstatus) or ""

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

        return out

    def _chain_contract_fallback(
        self,
        underlying: str,
        expiration: str | None,
        contract_type: str | None,
        strike_range: tuple[float, float] | None,
        limit: int | None,
    ) -> list[str]:
        chain_resp = self.data.get_option_chain(
            OptionChainRequest(
                underlying_symbol=underlying,
                expiration_date=expiration,
                feed=self.feed,
                limit=limit,
            ),
        )

        items = chain_resp.items() if isinstance(chain_resp, dict) else []

        out: list[str] = []

        for sym, _snap in items:
            _, exp2, typ2, strike2 = decode_osi(sym)

            if expiration and exp2 != expiration:
                continue
            if contract_type and (typ2 or "").lower() != contract_type.lower():
                continue
            if strike_range and strike2 is not None:
                lo, hi = strike_range

                if not (lo <= float(strike2) <= hi):
                    continue

            out.append(sym)

            if limit and len(out) >= limit:
                break

        return out

    def get_options_chain(
        self,
        underlying: str,
        expiration: str | None = None,
        limit: int | None = None,
        return_df: bool | None = None,
        use_contract_join: bool = True,
    ) -> pd.DataFrame | list[dict]:
        """Live options chain — quote + last trade + greeks per contract.

        Joins against the Trading API contract map (when ``use_contract_join``)
        to backfill metadata that the snapshot stream omits, with OSI
        decoding as a final fallback.
        """
        if return_df is None:
            return_df = True

        cmap: dict[str, tuple[str | None, float | None, str | None]] = {}

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
            ),
        )

        items = resp.items() if isinstance(resp, dict) else []

        rows = [
            self._chain_row(sym, snap, underlying, cmap)
            for sym, snap in items
        ]

        if return_df:
            df = pd.DataFrame(rows)
            sort_cols = [c for c in ["expiration", "strike", "type"] if c in df.columns]

            return df.sort_values(sort_cols) if not df.empty and sort_cols else df

        return rows

    @staticmethod
    def _chain_row(
        sym: str,
        snap,
        underlying: str,
        cmap: dict[str, tuple[str | None, float | None, str | None]],
    ) -> dict:
        strike = getattr(snap, "strike_price", None)
        exp = _norm_exp_str(getattr(snap, "expiration_date", None))
        ctype = getattr(snap, "contract_type", None)
        ctype_val = _enum_value_lower(ctype)

        if sym in cmap:
            exp = exp or cmap[sym][0]
            strike = strike if strike is not None else cmap[sym][1]
            ctype_val = ctype_val or cmap[sym][2]

        if strike is None or exp is None or ctype_val is None:
            _, exp2, type2, strike2 = decode_osi(sym)
            exp = exp or exp2
            ctype_val = ctype_val or type2

            if strike is None:
                strike = strike2

        q = getattr(snap, "latest_quote", None)
        t = getattr(snap, "latest_trade", None)
        g = getattr(snap, "greeks", None)

        bid = getattr(q, "bid_price", None) if q else None
        ask = getattr(q, "ask_price", None) if q else None
        mid = (
            (float(bid) + float(ask)) / 2.0
            if (bid is not None and ask is not None)
            else None
        )

        return {
            "symbol": sym,
            "underlying": underlying,
            "expiration": exp,
            "strike": float(strike) if strike is not None else None,
            "type": ctype_val,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "last": getattr(t, "price", None) if t else None,
            "delta": getattr(g, "delta", None) if g else None,
            "gamma": getattr(g, "gamma", None) if g else None,
            "theta": getattr(g, "theta", None) if g else None,
            "vega": getattr(g, "vega", None) if g else None,
            "iv": getattr(g, "implied_volatility", None) if g else None,
        }

    def get_option_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """OHLCV bars for an OSI option contract."""
        tf = _TIMEFRAME_MAP.get(timeframe.lower(), TimeFrame.Day)
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

        # Reason: BarSet.__contains__ misbehaves on alpaca-py — subscript
        # raises if the symbol has no bars rather than returning empty.
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

    def get_option_latest_quote(self, symbol: str) -> dict:
        """Latest bid / ask quote for an OSI option contract."""
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

    def get_option_snapshot(self, symbol: str) -> dict:
        """Full snapshot — quote + trade + greeks — for an OSI option contract."""
        request = OptionSnapshotRequest(symbol_or_symbols=symbol)
        snapshots = self.data.get_option_snapshot(request)

        if symbol not in snapshots:
            raise ValueError(f"No snapshot data returned for {symbol}")

        snap = snapshots[symbol]
        result: dict = {"symbol": symbol}

        if snap.latest_quote:
            q = snap.latest_quote
            result["quote"] = {
                "bid_price": float(q.bid_price) if q.bid_price is not None else None,
                "bid_size": float(q.bid_size) if q.bid_size is not None else None,
                "ask_price": float(q.ask_price) if q.ask_price is not None else None,
                "ask_size": float(q.ask_size) if q.ask_size is not None else None,
                "timestamp": str(q.timestamp),
            }

        if snap.latest_trade:
            t = snap.latest_trade
            result["trade"] = {
                "price": float(t.price) if t.price is not None else None,
                "size": float(t.size) if t.size is not None else None,
                "timestamp": str(t.timestamp),
            }

        if snap.greeks:
            g = snap.greeks
            result["greeks"] = {
                "delta": g.delta,
                "gamma": g.gamma,
                "theta": g.theta,
                "vega": g.vega,
                "rho": g.rho,
            }

        return result
