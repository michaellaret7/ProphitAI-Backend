"""Fund the firm account with $1,000,000 via sandbox ACH transfer."""

import time
from app.brokers.alpaca_broker.broker import ProphitBroker

FIRM_ACCOUNT_ID = "37dd29d5-e94f-3251-bbfc-31db312c09e1"
AMOUNT = 1_000_000

broker = ProphitBroker()

# Step 1: Check if firm account already has an ACH relationship
print("Checking existing ACH relationships...")
relationships = broker.get_ach_relationships(FIRM_ACCOUNT_ID)

if relationships:
    rel_id = relationships[0]["relationship_id"]
    print(f"Found existing ACH relationship: {rel_id}")
else:
    # Step 2: Link a fake bank account
    print("Linking fake bank account...")
    result = broker.link_bank_account(FIRM_ACCOUNT_ID, {
        "account_owner_name": "ProphitAI Firm",
        "account_number": "32131231abc",
        "routing_number": "121000358",
        "account_type": "checking",
    })
    rel_id = result["relationship_id"]
    print(f"Created ACH relationship: {rel_id} (status: {result['status']})")
    print("Waiting for ACH approval...")
    time.sleep(5)

# Step 3: Deposit $1M
print(f"\nDepositing ${AMOUNT:,} into firm account...")
deposit = broker.deposit(FIRM_ACCOUNT_ID, rel_id, AMOUNT)
print(f"Transfer created: {deposit}")

# Step 4: Verify balance
print("\nVerifying balance...")
info = broker.get_account(FIRM_ACCOUNT_ID)
print(f"  Cash:         ${info.get('cash', 'N/A')}")
print(f"  Buying Power: ${info.get('buying_power', 'N/A')}")
print(f"  Equity:       ${info.get('equity', 'N/A')}")
