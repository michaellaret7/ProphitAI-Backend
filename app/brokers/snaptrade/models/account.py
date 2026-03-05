"""
SnapTrade Account Info Model
Flattens the deeply nested SnapTrade account details + balances responses into a clean Pydantic model.
"""

from typing import Any, Dict, List

from pydantic import BaseModel


class AccountInfo(BaseModel):
    """Flattened account info from SnapTrade's account details and balances responses."""

    model_config = {"frozen": True}

    name: str
    margin_status: str
    balance: float
    is_paper: bool
    cash: float
    buying_power: float

    @staticmethod
    def from_raw(details: Dict[str, Any], balances: List[Dict[str, Any]]) -> "AccountInfo":
        """Create an AccountInfo from raw SnapTrade account details and balances dicts."""
        return _parse_account_info(details, balances)


# ================================
# --> Helper funcs
# ================================

def _parse_account_info(details: Dict[str, Any], balances: List[Dict[str, Any]]) -> AccountInfo:
    """Parse raw SnapTrade account details and balances into an AccountInfo model."""
    meta = details.get("meta", {})
    balance_data = details.get("balance", {}).get("total", {})
    first_balance = balances[0] if balances else {}

    return AccountInfo(
        name=details.get("name", ""),
        margin_status=meta.get("type", ""),
        balance=balance_data.get("amount", 0.0),
        is_paper=details.get("is_paper", False),
        cash=first_balance.get("cash", 0.0),
        buying_power=first_balance.get("buying_power", 0.0),
    )
