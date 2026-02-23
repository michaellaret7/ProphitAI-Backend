"""
Alpaca Broker API - Unified Interface
Complete one-stop shop for all multi-user brokerage operations.

Sub-components accessible directly:
    broker.accounts    — account creation, KYC, options approval, activities
    broker.trading     — order execution, positions, order management
    broker.portfolio   — portfolio history, assets
    broker.funding     — ACH, transfers, journaling
    broker.options     — chains, quotes, snapshots, bars
    broker.documents   — statements, confirmations, tax forms
"""

from typing import Optional, List, Dict, Tuple
from app.brokers.alpaca_broker.client import AlpacaBrokerClient
from app.brokers.alpaca_broker.accounts import BrokerAccounts
from app.brokers.alpaca_broker.trading import BrokerTrading
from app.brokers.alpaca_broker.portfolio import BrokerPortfolio
from app.brokers.alpaca_broker.funding import BrokerFunding
from app.brokers.alpaca_broker.options import BrokerOptionsService
from app.brokers.alpaca_broker.documents import BrokerDocuments


class ProphitBroker:
    """Unified interface for all Broker API operations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        sandbox: bool = True,
        options_feed: str = "indicative",
    ):
        self.client = AlpacaBrokerClient(
            api_key=api_key, secret_key=secret_key, sandbox=sandbox,
        )
        broker_client = self.client.get_client()
        _api_key = self.client.api_key
        _secret_key = self.client.secret_key

        self.accounts = BrokerAccounts(
            broker_client, api_key=_api_key, secret_key=_secret_key, sandbox=sandbox,
        )
        self.trading = BrokerTrading(broker_client)
        self.portfolio = BrokerPortfolio(broker_client)
        self.funding = BrokerFunding(broker_client)
        self.options = BrokerOptionsService(
            trading_client=self.client.get_trading_client(),
            option_data_client=self.client.get_option_data_client(),
            feed=options_feed,
        )
        self.documents = BrokerDocuments(
            broker_client, api_key=_api_key, secret_key=_secret_key, sandbox=sandbox,
        )

    # ══════════════════════════════════════════════════════════════
    # ACCOUNTS
    # ══════════════════════════════════════════════════════════════

    def create_account(self, user_data: Dict) -> Dict:
        """Create a brokerage account for a new user (KYC/AML)."""
        return self.accounts.create_account(user_data)

    def get_account(self, account_id: str) -> Dict:
        """Get account info (cash, equity, buying_power, etc.)."""
        return self.accounts.get_account(account_id)

    def list_accounts(self, **kwargs) -> List[Dict]:
        """List all accounts under management."""
        return self.accounts.list_accounts(**kwargs)

    def close_account(self, account_id: str) -> None:
        """Close/deactivate an account (irreversible)."""
        self.accounts.close_account(account_id)

    def request_options_approval(self, account_id: str, level: int = 1) -> Dict:
        """Request options trading approval (Level 1/2/3) for an account."""
        return self.accounts.request_options_approval(account_id, level)

    def get_options_approval(self, account_id: str) -> Optional[Dict]:
        """Get current options approval status for an account."""
        return self.accounts.get_options_approval(account_id)

    def get_account_activities(
        self, account_id: str, activity_type: Optional[str] = None,
    ) -> List[Dict]:
        """Get account activities (fills, dividends, transfers, etc.)."""
        return self.accounts.get_account_activities(account_id, activity_type)

    def update_account(self, account_id: str, updates: Dict) -> Dict:
        """Update account information (contact, identity, disclosures)."""
        return self.accounts.update_account(account_id, updates)

    # ══════════════════════════════════════════════════════════════
    # FUNDING
    # ══════════════════════════════════════════════════════════════

    def link_bank_account(self, account_id: str, bank_data: Dict) -> Dict:
        """Link a bank account via ACH."""
        return self.funding.link_bank_account(account_id, bank_data)

    def get_ach_relationships(self, account_id: str) -> List[Dict]:
        """Get all linked bank accounts for a user."""
        return self.funding.get_ach_relationships(account_id)

    def delete_ach_relationship(self, account_id: str, relationship_id: str) -> None:
        """Remove a bank connection."""
        self.funding.delete_ach_relationship(account_id, relationship_id)

    def deposit(self, account_id: str, relationship_id: str, amount: float) -> Dict:
        """Deposit money from linked bank into brokerage account."""
        return self.funding.deposit(account_id, relationship_id, amount)

    def withdraw(self, account_id: str, relationship_id: str, amount: float) -> Dict:
        """Withdraw money from brokerage account to linked bank."""
        return self.funding.withdraw(account_id, relationship_id, amount)

    def get_transfers(self, account_id: str) -> List[Dict]:
        """Get all transfers for an account."""
        return self.funding.get_transfers(account_id)

    def cancel_transfer(self, account_id: str, transfer_id: str) -> None:
        """Cancel a pending transfer."""
        self.funding.cancel_transfer(account_id, transfer_id)

    # ── Journaling ────────────────────────────────────────────

    def journal_cash(
        self, from_account: str, to_account: str, amount: float,
        description: Optional[str] = None,
    ) -> Dict:
        """Transfer cash between accounts."""
        return self.funding.journal_cash(from_account, to_account, amount, description)

    def journal_security(
        self, from_account: str, to_account: str, symbol: str, qty: float,
        description: Optional[str] = None,
    ) -> Dict:
        """Transfer securities between accounts."""
        return self.funding.journal_security(from_account, to_account, symbol, qty, description)

    def batch_journal_cash(self, from_account: str, entries: List[Dict]) -> List[Dict]:
        """Journal cash from one account to many."""
        return self.funding.batch_journal_cash(from_account, entries)

    def get_journals(
        self, entry_type: Optional[str] = None,
        from_account: Optional[str] = None, to_account: Optional[str] = None,
    ) -> List[Dict]:
        """Get journal entries, optionally filtered."""
        return self.funding.get_journals(entry_type, from_account, to_account)

    def cancel_journal(self, journal_id: str) -> None:
        """Cancel a pending journal entry."""
        self.funding.cancel_journal(journal_id)

    # ══════════════════════════════════════════════════════════════
    # TRADING
    # ══════════════════════════════════════════════════════════════

    def buy(
        self, account_id: str, symbol: str,
        qty: Optional[float] = None, notional: Optional[float] = None,
        limit_price: Optional[float] = None, stop_price: Optional[float] = None,
        trail_price: Optional[float] = None, trail_percent: Optional[float] = None,
        take_profit: Optional[float] = None, stop_loss: Optional[float] = None,
        stop_loss_limit: Optional[float] = None, order_class: Optional[str] = None,
        time_in_force: str = "day",
    ) -> Dict:
        """Buy an asset for a user. Order type inferred from parameters."""
        return self.trading.buy(
            account_id=account_id, symbol=symbol, qty=qty, notional=notional,
            limit_price=limit_price, stop_price=stop_price,
            trail_price=trail_price, trail_percent=trail_percent,
            take_profit=take_profit, stop_loss=stop_loss,
            stop_loss_limit=stop_loss_limit, order_class=order_class,
            time_in_force=time_in_force,
        )

    def sell(
        self, account_id: str, symbol: str,
        qty: Optional[float] = None, notional: Optional[float] = None,
        limit_price: Optional[float] = None, stop_price: Optional[float] = None,
        trail_price: Optional[float] = None, trail_percent: Optional[float] = None,
        take_profit: Optional[float] = None, stop_loss: Optional[float] = None,
        stop_loss_limit: Optional[float] = None, order_class: Optional[str] = None,
        time_in_force: str = "day",
    ) -> Dict:
        """Sell an asset for a user. Order type inferred from parameters."""
        return self.trading.sell(
            account_id=account_id, symbol=symbol, qty=qty, notional=notional,
            limit_price=limit_price, stop_price=stop_price,
            trail_price=trail_price, trail_percent=trail_percent,
            take_profit=take_profit, stop_loss=stop_loss,
            stop_loss_limit=stop_loss_limit, order_class=order_class,
            time_in_force=time_in_force,
        )

    def replace_order(
        self, account_id: str, order_id: str,
        qty: Optional[int] = None, limit_price: Optional[float] = None,
        stop_price: Optional[float] = None, trail: Optional[float] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict:
        """Modify an existing open order."""
        return self.trading.replace_order(
            account_id=account_id, order_id=order_id, qty=qty,
            limit_price=limit_price, stop_price=stop_price,
            trail=trail, time_in_force=time_in_force,
        )

    def get_order_by_id(self, account_id: str, order_id: str, nested: bool = True) -> Dict:
        """Retrieve a specific order by UUID."""
        return self.trading.get_order_by_id(account_id, order_id, nested=nested)

    def get_orders(self, account_id: str, status: str = "open") -> List[Dict]:
        """Get orders for a user."""
        return self.trading.get_orders(account_id, status)

    def cancel_order(self, account_id: str, order_id: str) -> None:
        """Cancel a specific order."""
        self.trading.cancel_order(account_id, order_id)

    def cancel_all_orders(self, account_id: str) -> None:
        """Cancel all open orders."""
        self.trading.cancel_all_orders(account_id)

    # ── Positions ─────────────────────────────────────────────

    def get_positions(self, account_id: str) -> List[Dict]:
        """Get all positions for a user."""
        return self.trading.get_positions(account_id)

    def get_position(self, account_id: str, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol."""
        return self.trading.get_position(account_id, symbol)

    def close_position(
        self, account_id: str, symbol: str,
        qty: Optional[float] = None, percentage: Optional[float] = None,
    ) -> Dict:
        """Close a position fully or partially."""
        return self.trading.close_position(account_id, symbol, qty=qty, percentage=percentage)

    def close_all_positions(self, account_id: str, cancel_orders: bool = True) -> List[Dict]:
        """Close all positions for a user."""
        return self.trading.close_all_positions(account_id, cancel_orders)

    # ══════════════════════════════════════════════════════════════
    # PORTFOLIO
    # ══════════════════════════════════════════════════════════════

    def get_buying_power(self, account_id: str) -> float:
        return self.accounts.get_account(account_id)["buying_power"]

    def get_cash(self, account_id: str) -> float:
        return self.accounts.get_account(account_id)["cash"]

    def get_equity(self, account_id: str) -> float:
        return self.accounts.get_account(account_id)["equity"]

    def get_portfolio_history(
        self, account_id: str, period: Optional[str] = None,
        timeframe: Optional[str] = None, extended_hours: Optional[bool] = None,
    ) -> Dict:
        """Get historical portfolio equity and P&L over time."""
        return self.portfolio.get_portfolio_history(
            account_id, period=period, timeframe=timeframe,
            extended_hours=extended_hours,
        )

    def get_asset(self, symbol: str) -> Dict:
        """Get detailed info for a single asset."""
        return self.portfolio.get_asset(symbol)

    def get_all_assets(
        self, status: Optional[str] = None, asset_class: Optional[str] = None,
    ) -> List[Dict]:
        """Get all assets, optionally filtered."""
        return self.portfolio.get_all_assets(status=status, asset_class=asset_class)

    # ══════════════════════════════════════════════════════════════
    # OPTIONS
    # ══════════════════════════════════════════════════════════════

    def get_options_chain(
        self, underlying: str, expiration: Optional[str] = None,
        limit: Optional[int] = None, return_df: Optional[bool] = None,
    ):
        """Get options chain with quotes and greeks."""
        return self.options.get_options_chain(
            underlying=underlying, expiration=expiration,
            limit=limit, return_df=return_df,
        )

    def get_option_expirations(
        self, underlying: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[str]:
        """Get available expiration dates for an underlying."""
        return self.options.get_available_dates(underlying=underlying, start=start, end=end)

    def get_option_contracts(
        self, underlying: str, expiration: Optional[str] = None,
        contract_type: Optional[str] = None,
        strike_range: Optional[Tuple[float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Get available option contracts (OSI symbols)."""
        return self.options.get_available_contracts(
            underlying=underlying, expiration=expiration,
            contract_type=contract_type, strike_range=strike_range, limit=limit,
        )

    def get_option_bars(
        self, symbol: str, timeframe: str = "1d",
        start: Optional[str] = None, end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Get OHLCV bars for an option contract."""
        return self.options.get_option_bars(
            symbol=symbol, timeframe=timeframe, start=start, end=end, limit=limit,
        )

    def get_option_latest_quote(self, symbol: str) -> Dict:
        """Get latest bid/ask quote for an option contract."""
        return self.options.get_option_latest_quote(symbol)

    def get_option_snapshot(self, symbol: str) -> Dict:
        """Get full snapshot (quote + trade + greeks) for an option contract."""
        return self.options.get_option_snapshot(symbol)

    def buy_option(
        self, account_id: str, symbol: str, qty: int = 1,
        limit_price: Optional[float] = None, time_in_force: str = "day",
    ) -> Dict:
        """Buy an option contract for a user."""
        return self.trading.buy(
            account_id=account_id, symbol=symbol, qty=qty,
            limit_price=limit_price, time_in_force=time_in_force,
        )

    def sell_option(
        self, account_id: str, symbol: str, qty: int = 1,
        limit_price: Optional[float] = None, time_in_force: str = "day",
    ) -> Dict:
        """Sell an option contract for a user."""
        return self.trading.sell(
            account_id=account_id, symbol=symbol, qty=qty,
            limit_price=limit_price, time_in_force=time_in_force,
        )

    def exercise_options_position(self, account_id: str, symbol_or_contract_id: str) -> None:
        """Exercise a held options position for a user."""
        self.trading.exercise_options_position(account_id, symbol_or_contract_id)

    def submit_multi_leg_order(
        self, account_id: str, legs: List[Dict], qty: int,
        limit_price: Optional[float] = None, time_in_force: str = "day",
    ) -> Dict:
        """Submit a multi-leg option order (spreads, straddles, etc.)."""
        return self.trading.submit_multi_leg_order(
            account_id=account_id, legs=legs, qty=qty,
            limit_price=limit_price, time_in_force=time_in_force,
        )

    # ══════════════════════════════════════════════════════════════
    # DOCUMENTS
    # ══════════════════════════════════════════════════════════════

    def get_documents(
        self, account_id: str, doc_type: Optional[str] = None,
        start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get all documents for an account."""
        return self.documents.get_documents(account_id, doc_type=doc_type, start=start, end=end)

    def get_statements(
        self, account_id: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get monthly account statements."""
        return self.documents.get_statements(account_id, start=start, end=end)

    def get_trade_confirmations(
        self, account_id: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get trade confirmations."""
        return self.documents.get_trade_confirmations(account_id, start=start, end=end)

    def get_tax_documents(
        self, account_id: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get tax documents (1099s, etc.)."""
        return self.documents.get_tax_documents(account_id, start=start, end=end)

    def get_document_download_url(self, account_id: str, document_id: str) -> str:
        """Get a pre-signed download URL for a document (PDF)."""
        return self.documents.get_download_url(account_id, document_id)

    # ── Utilities ─────────────────────────────────────────────

    def is_sandbox(self) -> bool:
        return self.client.is_sandbox()
