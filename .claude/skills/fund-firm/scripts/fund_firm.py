"""
Fund the Alpaca Broker sandbox firm account with $1M via ACH deposit.

Usage:
    python .claude/skills/fund-firm/scripts/fund_firm.py check     # Show current balance
    python .claude/skills/fund-firm/scripts/fund_firm.py deposit   # Deposit $1M
"""

import sys
import os

# Reason: Ensure the project root is on sys.path so imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from app.brokers.alpaca_broker import ProphitBroker

FIRM_ACCOUNT_ID = "37dd29d5-e94f-3251-bbfc-31db312c09e1"
ACH_RELATIONSHIP_ID = "2bebdee2-033f-4679-ab72-6752f5e8706c"
DEPOSIT_AMOUNT = 1_000_000


def check_balance() -> None:
    """Print the firm account's current balance."""
    broker = ProphitBroker(sandbox=True)
    acct = broker.get_account(FIRM_ACCOUNT_ID)
    print(f"cash: {acct['cash']:,.2f}")
    print(f"equity: {acct['equity']:,.2f}")
    print(f"buying_power: {acct['buying_power']:,.2f}")


def deposit() -> None:
    """Deposit $1M into the firm account via ACH."""
    broker = ProphitBroker(sandbox=True)

    acct_before = broker.get_account(FIRM_ACCOUNT_ID)
    cash_before = acct_before["cash"]

    try:
        result = broker.deposit(
            account_id=FIRM_ACCOUNT_ID,
            relationship_id=ACH_RELATIONSHIP_ID,
            amount=DEPOSIT_AMOUNT,
        )
    except Exception as e:
        if "maximum total daily transfer" in str(e):
            print(f"error: Daily $1M transfer limit already reached. Try again tomorrow.")
            print(f"current_cash: ${cash_before:,.2f}")
            sys.exit(1)
        raise

    expected_after = cash_before + DEPOSIT_AMOUNT

    print(f"before: ${cash_before:,.2f}")
    print(f"deposit: ${DEPOSIT_AMOUNT:,.2f}")
    print(f"expected_after: ${expected_after:,.2f}")
    print(f"transfer_id: {result['transfer_id']}")
    print(f"status: {result['status']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fund_firm.py [check|deposit]")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "check":
        check_balance()
    elif command == "deposit":
        deposit()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
