"""
Alpaca Broker Funding
Handles bank linking (ACH/Plaid), money transfers (deposits/withdrawals),
and journaling (moving cash/securities between accounts).

NEW — no equivalent in Trading API.
"""

from alpaca.broker.client import BrokerClient
from alpaca.broker.requests import (
    CreateACHRelationshipRequest,
    CreateACHTransferRequest,
    CreateJournalRequest,
    CreateBatchJournalRequest,
    BatchJournalRequestEntry,
    GetJournalsRequest,
)
from alpaca.broker.enums import (
    BankAccountType,
    TransferDirection,
    TransferTiming,
    JournalEntryType,
)
from typing import Optional, List, Dict


class BrokerFunding:
    """Handles bank linking, money transfers, and journaling for end user accounts."""

    def __init__(self, client: BrokerClient):
        self.client = client

    # ══════════════════════════════════════════════════════════════
    # ACH RELATIONSHIPS (Bank Linking)
    # ══════════════════════════════════════════════════════════════

    def link_bank_account(self, account_id: str, bank_data: Dict) -> Dict:
        """
        Link a bank account via ACH routing/account numbers.

        For production, consider using Plaid — pass a processor_token
        to Alpaca's Plaid-specific endpoint for a smoother UX.

        Args:
            account_id: The user's Alpaca account ID
            bank_data: Dict with:
                - account_owner_name: Name on the bank account
                - account_number: Bank account number
                - routing_number: Bank routing number
                - account_type: 'checking' or 'savings' (default: 'checking')

        Returns:
            Dict with relationship_id and status
        """
        acct_type_map = {
            "checking": BankAccountType.CHECKING,
            "savings": BankAccountType.SAVINGS,
        }

        request = CreateACHRelationshipRequest(
            account_owner_name=bank_data["account_owner_name"],
            bank_account_type=acct_type_map.get(
                bank_data.get("account_type", "checking"), BankAccountType.CHECKING
            ),
            bank_account_number=bank_data["account_number"],
            bank_routing_number=bank_data["routing_number"],
        )

        try:
            relationship = self.client.create_ach_relationship_for_account(
                account_id=account_id,
                ach_data=request,
            )
            return {
                "relationship_id": str(relationship.id),
                "status": str(relationship.status),
                "account_owner_name": relationship.account_owner_name,
            }
        except Exception as e:
            # Reason: Alpaca allows only one active ACH relationship per account.
            # If one already exists, return it instead of failing.
            if "40910000" in str(e):
                existing = self.get_ach_relationships(account_id)
                if existing:
                    return existing[0]
            raise Exception(f"Failed to link bank for account {account_id}: {str(e)}")

    def get_ach_relationships(self, account_id: str) -> List[Dict]:
        """Get all ACH relationships for an account."""
        try:
            relationships = self.client.get_ach_relationships_for_account(account_id=account_id)
            return [
                {
                    "relationship_id": str(r.id),
                    "status": str(r.status),
                    "account_owner_name": r.account_owner_name,
                }
                for r in relationships
            ]
        except Exception as e:
            raise Exception(f"Failed to get ACH relationships for {account_id}: {str(e)}")

    def delete_ach_relationship(self, account_id: str, relationship_id: str) -> None:
        """Remove a bank connection."""
        try:
            self.client.delete_ach_relationship_for_account(
                account_id=account_id,
                ach_relationship_id=relationship_id,
            )
        except Exception as e:
            raise Exception(f"Failed to delete ACH relationship: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # TRANSFERS (Deposits & Withdrawals)
    # ══════════════════════════════════════════════════════════════

    def deposit(
        self,
        account_id: str,
        relationship_id: str,
        amount: float,
        timing: str = "immediate",
    ) -> Dict:
        """
        Deposit money from linked bank into the brokerage account.

        Args:
            account_id: User's Alpaca account ID
            relationship_id: ACH relationship ID from link_bank_account
            amount: Dollar amount to deposit
            timing: 'immediate' (sandbox only — real ACH takes 1-3 days)
        """
        return self._create_transfer(
            account_id=account_id,
            relationship_id=relationship_id,
            amount=amount,
            direction=TransferDirection.INCOMING,
            timing=timing,
        )

    def withdraw(
        self,
        account_id: str,
        relationship_id: str,
        amount: float,
        timing: str = "immediate",
    ) -> Dict:
        """
        Withdraw money from brokerage account to linked bank.

        Args:
            account_id: User's Alpaca account ID
            relationship_id: ACH relationship ID
            amount: Dollar amount to withdraw
            timing: 'immediate' (sandbox only)
        """
        return self._create_transfer(
            account_id=account_id,
            relationship_id=relationship_id,
            amount=amount,
            direction=TransferDirection.OUTGOING,
            timing=timing,
        )

    def get_transfers(self, account_id: str) -> List[Dict]:
        """Get all transfers for an account."""
        try:
            transfers = self.client.get_transfers_for_account(account_id=account_id)
            return [
                {
                    "transfer_id": str(t.id),
                    "direction": str(t.direction),
                    "amount": str(t.amount),
                    "status": str(t.status),
                    "created_at": str(t.created_at) if t.created_at else None,
                }
                for t in transfers
            ]
        except Exception as e:
            raise Exception(f"Failed to get transfers for {account_id}: {str(e)}")

    def _create_transfer(
        self,
        account_id: str,
        relationship_id: str,
        amount: float,
        direction: TransferDirection,
        timing: str = "immediate",
    ) -> Dict:
        """Internal: create an ACH transfer."""
        timing_map = {
            "immediate": TransferTiming.IMMEDIATE,
        }
        timing_enum = timing_map.get(timing, TransferTiming.IMMEDIATE)

        request = CreateACHTransferRequest(
            amount=str(amount),
            direction=direction,
            timing=timing_enum,
            relationship_id=relationship_id,
        )

        try:
            transfer = self.client.create_transfer_for_account(
                account_id=account_id,
                transfer_data=request,
            )
            return {
                "transfer_id": str(transfer.id),
                "status": str(transfer.status),
                "amount": amount,
                "direction": str(direction),
            }
        except Exception as e:
            action = "deposit" if direction == TransferDirection.INCOMING else "withdrawal"
            raise Exception(f"Failed {action} for account {account_id}: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # JOURNALING (Move cash/securities between accounts)
    # ══════════════════════════════════════════════════════════════

    def journal_cash(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Transfer cash between two accounts under your management.

        Use cases: signup bonuses, rewards, instant funding from firm account,
        referral credits, rebalancing across accounts.

        Args:
            from_account: Source account ID (cash leaves here)
            to_account: Destination account ID (cash arrives here)
            amount: Dollar amount to transfer
            description: Optional description/memo
        """
        try:
            journal_data = CreateJournalRequest(
                from_account=from_account,
                to_account=to_account,
                entry_type=JournalEntryType.CASH,
                amount=amount,
                description=description,
            )
            journal = self.client.create_journal(journal_data=journal_data)
            return {
                "journal_id": str(journal.id),
                "from_account": str(journal.from_account),
                "to_account": str(journal.to_account),
                "amount": str(journal.net_amount) if journal.net_amount else str(amount),
                "status": str(journal.status),
                "entry_type": "cash",
            }
        except Exception as e:
            raise Exception(f"Failed cash journal: {str(e)}")

    def journal_security(
        self,
        from_account: str,
        to_account: str,
        symbol: str,
        qty: float,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Transfer securities (shares) between two accounts.

        Args:
            from_account: Source account (shares leave here)
            to_account: Destination account (shares arrive here)
            symbol: Ticker symbol to transfer
            qty: Number of shares
            description: Optional description
        """
        try:
            journal_data = CreateJournalRequest(
                from_account=from_account,
                to_account=to_account,
                entry_type=JournalEntryType.SECURITY,
                symbol=symbol,
                qty=qty,
                description=description,
            )
            journal = self.client.create_journal(journal_data=journal_data)
            return {
                "journal_id": str(journal.id),
                "from_account": str(journal.from_account),
                "to_account": str(journal.to_account),
                "symbol": symbol,
                "qty": qty,
                "status": str(journal.status),
                "entry_type": "security",
            }
        except Exception as e:
            raise Exception(f"Failed security journal: {str(e)}")

    def batch_journal_cash(
        self,
        from_account: str,
        entries: List[Dict],
    ) -> List[Dict]:
        """
        Journal cash from one account to many accounts at once.

        Use cases: distributing rewards, signup bonuses at scale.

        Args:
            from_account: Source account ID
            entries: List of dicts with 'to_account' and 'amount'
                [{'to_account': '...', 'amount': 50}, ...]
        """
        try:
            batch_entries = [
                BatchJournalRequestEntry(
                    to_account=e["to_account"],
                    amount=e["amount"],
                )
                for e in entries
            ]

            batch_data = CreateBatchJournalRequest(
                entry_type=JournalEntryType.CASH,
                from_account=from_account,
                entries=batch_entries,
            )

            results = self.client.create_batch_journal(batch_data=batch_data)
            return [
                {
                    "journal_id": str(j.id),
                    "to_account": str(j.to_account),
                    "amount": str(j.net_amount) if j.net_amount else None,
                    "status": str(j.status),
                }
                for j in results
            ]
        except Exception as e:
            raise Exception(f"Failed batch journal: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # CANCEL TRANSFER
    # ══════════════════════════════════════════════════════════════

    def cancel_transfer(self, account_id: str, transfer_id: str) -> None:
        """
        Cancel a pending transfer.

        Args:
            account_id: User's Alpaca account ID
            transfer_id: Transfer UUID to cancel
        """
        try:
            self.client.cancel_transfer_for_account(
                account_id=account_id,
                transfer_id=transfer_id,
            )
        except Exception as e:
            raise Exception(f"Failed to cancel transfer {transfer_id}: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # JOURNAL QUERIES
    # ══════════════════════════════════════════════════════════════

    def get_journals(
        self,
        entry_type: Optional[str] = None,
        from_account: Optional[str] = None,
        to_account: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get journal entries, optionally filtered.

        Args:
            entry_type: 'cash' or 'security'
            from_account: Filter by source account ID
            to_account: Filter by destination account ID
        """
        try:
            request = GetJournalsRequest()
            if entry_type:
                type_map = {
                    "cash": JournalEntryType.CASH,
                    "security": JournalEntryType.SECURITY,
                }
                request.entry_type = type_map.get(entry_type.lower(), JournalEntryType.CASH)
            if from_account:
                request.from_account = from_account
            if to_account:
                request.to_account = to_account

            journals = self.client.get_journals(journal_filter=request)
            return [
                {
                    "journal_id": str(j.id),
                    "from_account": str(j.from_account),
                    "to_account": str(j.to_account),
                    "entry_type": str(j.entry_type),
                    "amount": str(j.net_amount) if j.net_amount else None,
                    "status": str(j.status),
                }
                for j in journals
            ]
        except Exception as e:
            raise Exception(f"Failed to get journals: {str(e)}")

    def cancel_journal(self, journal_id: str) -> None:
        """
        Cancel a pending journal entry.

        Args:
            journal_id: Journal UUID to cancel
        """
        try:
            self.client.cancel_journal_by_id(journal_id=journal_id)
        except Exception as e:
            raise Exception(f"Failed to cancel journal {journal_id}: {str(e)}")
