"""
Alpaca Broker Account Management
Handles user onboarding (KYC/AML), account creation, options approval, and queries.

NEW — no equivalent in Trading API. The Trading API only has one account (yours).
"""

from alpaca.broker.client import BrokerClient
from alpaca.broker.models import Contact, Identity, Disclosures, Agreement
from alpaca.broker.requests import (
    CreateAccountRequest,
    ListAccountsRequest,
    GetAccountActivitiesRequest,
    UpdateAccountRequest,
)
from alpaca.trading.enums import ActivityType
from alpaca.broker.enums import (
    TaxIdType,
    FundingSource,
    AgreementType,
    AccountEntities,
)
from typing import Optional, List, Dict
from datetime import datetime
import httpx

from app.utils.time_utils import get_current_utc_time


class BrokerAccounts:
    """Handles account creation, KYC, options approval, and account queries."""

    def __init__(
        self,
        client: BrokerClient,
        api_key: str,
        secret_key: str,
        sandbox: bool = True,
    ):
        self.client = client
        self.api_key = api_key
        self.secret_key = secret_key
        self.sandbox = sandbox
        self._base_url = (
            "https://broker-api.sandbox.alpaca.markets"
            if sandbox
            else "https://broker-api.alpaca.markets"
        )

    # ── Account Creation (KYC/AML) ────────────────────────────────

    def create_account(self, user_data: Dict) -> Dict:
        """
        Create a brokerage account for a new end user.
        Alpaca runs KYC/AML verification automatically.

        Args:
            user_data: Dict with required fields:
                - first_name, last_name, email, phone
                - address, city, state, zip
                - dob (YYYY-MM-DD), ssn
                - ip_address (optional, for agreement records)
                - country_of_citizenship (optional, defaults to 'USA')
                - funding_source (optional, defaults to 'employment_income')

        Returns:
            Dict with account_id, status, and identity info
        """
        contact = Contact(
            email_address=user_data["email"],
            phone_number=user_data["phone"],
            street_address=[user_data["address"]],
            city=user_data["city"],
            state=user_data["state"],
            postal_code=user_data["zip"],
            country=user_data.get("country", "USA"),
        )

        funding = user_data.get("funding_source", "employment_income")
        funding_map = {
            "employment_income": FundingSource.EMPLOYMENT_INCOME,
            "investments": FundingSource.INVESTMENTS,
            "inheritance": FundingSource.INHERITANCE,
            "business_income": FundingSource.BUSINESS_INCOME,
            "savings": FundingSource.SAVINGS,
            "family": FundingSource.FAMILY,
        }

        identity = Identity(
            given_name=user_data["first_name"],
            family_name=user_data["last_name"],
            date_of_birth=user_data["dob"],
            tax_id=user_data["ssn"],
            tax_id_type=TaxIdType.USA_SSN,
            country_of_citizenship=user_data.get("country_of_citizenship", "USA"),
            country_of_birth=user_data.get("country_of_birth", "USA"),
            country_of_tax_residence=user_data.get("country_of_tax_residence", "USA"),
            funding_source=[funding_map.get(funding, FundingSource.EMPLOYMENT_INCOME)],
        )

        disclosures = Disclosures(
            is_control_person=user_data.get("is_control_person", False),
            is_affiliated_exchange_or_finra=user_data.get("is_affiliated", False),
            is_politically_exposed=user_data.get("is_politically_exposed", False),
            immediate_family_exposed=user_data.get("immediate_family_exposed", False),
        )

        now = get_current_utc_time().isoformat() + "Z"
        ip = user_data.get("ip_address", "127.0.0.1")

        agreements = [
            Agreement(agreement=AgreementType.ACCOUNT, signed_at=now, ip_address=ip),
            Agreement(agreement=AgreementType.CUSTOMER, signed_at=now, ip_address=ip),
            Agreement(agreement=AgreementType.MARGIN, signed_at=now, ip_address=ip),
        ]

        request = CreateAccountRequest(
            contact=contact,
            identity=identity,
            disclosures=disclosures,
            agreements=agreements,
        )

        try:
            account = self.client.create_account(request)
            return {
                "account_id": str(account.id),
                "status": str(account.status),
                "name": f"{account.identity.given_name} {account.identity.family_name}",
                "email": account.contact.email_address,
                "created_at": str(account.created_at) if account.created_at else None,
            }
        except Exception as e:
            raise Exception(f"Failed to create account: {str(e)}")

    # ── Account Queries ───────────────────────────────────────────

    def get_account(self, account_id: str) -> Dict:
        """
        Get full account details including trading info.

        Uses get_trade_account_by_id which returns cash, equity, buying_power, etc.
        The base get_account_by_id only returns identity/contact/KYC data.
        """
        try:
            account = self.client.get_trade_account_by_id(account_id=account_id)
            return {
                "account_id": str(account.id),
                "status": str(account.status),
                "cash": float(account.cash) if account.cash else 0,
                "equity": float(account.equity) if account.equity else 0,
                "buying_power": float(account.buying_power) if account.buying_power else 0,
                "portfolio_value": float(account.portfolio_value) if account.portfolio_value else 0,
                "pattern_day_trader": account.pattern_day_trader,
                "currency": account.currency,
                "account_number": getattr(account, "account_number", None),
                "options_trading_level": getattr(account, "options_trading_level", None),
            }
        except Exception as e:
            raise Exception(f"Failed to get account {account_id}: {str(e)}")

    def list_accounts(
        self,
        created_after: Optional[str] = None,
        entities: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        List all brokerage accounts under management.

        Args:
            created_after: ISO date string to filter by creation date
            entities: List of entity types to include: 'contact', 'identity'
        """
        entity_map = {
            "contact": AccountEntities.CONTACT,
            "identity": AccountEntities.IDENTITY,
        }

        filter_params = ListAccountsRequest()
        if created_after:
            filter_params.created_after = datetime.fromisoformat(created_after)
        if entities:
            filter_params.entities = [entity_map[e] for e in entities if e in entity_map]

        try:
            accounts = self.client.list_accounts(search_parameters=filter_params)
            return [
                {
                    "account_id": str(acc.id),
                    "status": str(acc.status),
                    "created_at": str(acc.created_at) if acc.created_at else None,
                }
                for acc in accounts
            ]
        except Exception as e:
            raise Exception(f"Failed to list accounts: {str(e)}")

    # ── Options Approval (NEW — Broker API only) ──────────────────

    def request_options_approval(self, account_id: str, level: int = 1) -> Dict:
        """
        Request options trading approval for an account.

        Args:
            account_id: The user's Alpaca account ID
            level: Options level to request (1, 2, or 3)
                Level 1: Covered calls, cash-secured puts
                Level 2: Long calls/puts, spreads
                Level 3: Uncovered options (requires margin)

        Returns:
            Dict with approval status
        """
        # The alpaca-py SDK may not have this method yet, so we use REST directly
        try:
            url = f"{self._base_url}/v1/accounts/{account_id}/options-approvals"
            auth = httpx.BasicAuth(self.api_key, self.secret_key)
            response = httpx.post(
                url,
                json={"requested_level": level},
                auth=auth,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "approval_id": data.get("id"),
                "account_id": data.get("account_id"),
                "requested_level": data.get("requested_level"),
                "status": data.get("status"),
            }
        except Exception as e:
            raise Exception(f"Failed to request options approval for {account_id}: {str(e)}")

    def get_options_approval(self, account_id: str) -> Optional[Dict]:
        """Get current options approval status for an account."""
        try:
            url = f"{self._base_url}/v1/accounts/{account_id}/options-approvals"
            auth = httpx.BasicAuth(self.api_key, self.secret_key)
            response = httpx.get(url, auth=auth)
            response.raise_for_status()
            data = response.json()
            return {
                "approval_id": data.get("id"),
                "account_id": data.get("account_id"),
                "approved_level": data.get("approved_level"),
                "status": data.get("status"),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise Exception(f"Failed to get options approval for {account_id}: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to get options approval for {account_id}: {str(e)}")

    # ── Account Updates ───────────────────────────────────────────

    def close_account(self, account_id: str) -> None:
        """Close/deactivate an account. This is irreversible."""
        try:
            self.client.close_account(account_id=account_id)
        except Exception as e:
            raise Exception(f"Failed to close account {account_id}: {str(e)}")

    # ── Account Activities ─────────────────────────────────────

    def get_account_activities(
        self,
        account_id: str,
        activity_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get account activities (fills, dividends, transfers, etc.).

        Args:
            account_id: User's Alpaca account ID
            activity_type: Filter by type (e.g., 'FILL', 'DIV', 'TRANS', 'CSD')
        """
        try:
            request = GetAccountActivitiesRequest(
                account_id=account_id,
                activity_types=[ActivityType(activity_type)] if activity_type else None,
            )

            activities = self.client.get_account_activities(activity_filter=request)
            results = []
            for a in activities:
                qty = getattr(a, "qty", None)
                price = getattr(a, "price", None)
                notional = str(float(qty) * float(price)) if qty and price else None
                results.append({
                    "id": str(getattr(a, "id", None)),
                    "activity_type": str(getattr(a, "activity_type", None)),
                    "date": str(getattr(a, "date", None)),
                    "qty": str(qty),
                    "price": str(price),
                    "notional": notional,
                    "symbol": getattr(a, "symbol", None),
                    "side": str(getattr(a, "side", None)),
                    "net_amount": str(getattr(a, "net_amount", None)),
                })
            return results
        except Exception as e:
            raise Exception(f"Failed to get activities for {account_id}: {str(e)}")

    def update_account(self, account_id: str, updates: Dict) -> Dict:
        """
        Update account information (contact, identity, disclosures).

        Args:
            account_id: User's Alpaca account ID
            updates: Dict of fields to update. Supports nested 'contact', 'identity',
                     'disclosures' dicts matching the Alpaca Account model.

        Returns:
            Updated account dict
        """
        try:
            request = UpdateAccountRequest(**updates)
            account = self.client.update_account(
                account_id=account_id,
                update_data=request,
            )
            return {
                "account_id": str(account.id),
                "status": str(account.status),
            }
        except Exception as e:
            raise Exception(f"Failed to update account {account_id}: {str(e)}")
