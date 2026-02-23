"""User funding repository — bank linking, deposits, withdrawals, and transfers."""

import os
from typing import List, Dict
from app.brokers.alpaca_broker.broker import ProphitBroker
from app.repositories.user.broker import get_broker, resolve_broker_account


# ════════════════════════════════════════════════════════════
# --> ACH Relationships
# ════════════════════════════════════════════════════════════

def link_bank_account(clerk_id: str, bank_data: Dict) -> Dict:
    """Link a bank account via ACH."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().link_bank_account(account_id, bank_data)


def get_ach_relationships(clerk_id: str) -> List[Dict]:
    """Get all linked bank accounts for a user."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_ach_relationships(account_id)


def delete_ach_relationship(clerk_id: str, relationship_id: str) -> None:
    """Remove a bank connection."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    get_broker().delete_ach_relationship(account_id, relationship_id)


# ════════════════════════════════════════════════════════════
# --> Transfers
# ════════════════════════════════════════════════════════════

def deposit(clerk_id: str, relationship_id: str, amount: float) -> Dict:
    """Deposit money from linked bank into brokerage account."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().deposit(account_id, relationship_id, amount)


def withdraw(clerk_id: str, relationship_id: str, amount: float) -> Dict:
    """Withdraw money from brokerage account to linked bank."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().withdraw(account_id, relationship_id, amount)


def get_transfers(clerk_id: str) -> List[Dict]:
    """Get all transfers for a user."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_transfers(account_id)


def cancel_transfer(clerk_id: str, transfer_id: str) -> None:
    """Cancel a pending transfer."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    get_broker().cancel_transfer(account_id, transfer_id)


# ════════════════════════════════════════════════════════════
# --> Instant Transfers (Firm Journal)
# ════════════════════════════════════════════════════════════

def instant_deposit(clerk_id: str, amount: float) -> Dict:
    """Journal cash from the firm funding account to a user's brokerage account."""
    user_account_id = resolve_broker_account(clerk_id=clerk_id)
    firm_account_id = os.environ["ALPACA_BROKER_FUNDING_ACCOUNT_ID"]
    return get_broker().journal_cash(
        from_account=firm_account_id,
        to_account=user_account_id,
        amount=amount,
        description="Instant deposit",
    )


