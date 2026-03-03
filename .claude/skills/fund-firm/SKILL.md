---
name: fund-firm
description: Deposit $1,000,000 into the Alpaca Broker sandbox firm account via ACH transfer. Use when the user asks to fund the firm account, add money to the firm, or top up the broker funding account.
---

## Overview

Deposit $1M into the ProphitAI Alpaca Broker sandbox firm account (`37dd29d5-e94f-3251-bbfc-31db312c09e1`) using the existing ACH relationship. This is the firm sweep account used to journal cash to user brokerage accounts.

## Workflow

### Step 1: Check current firm balance

```bash
source .venv/bin/activate && python .claude/skills/fund-firm/scripts/fund_firm.py check
```

This prints the firm account's current cash, equity, and buying power.

### Step 2: Deposit $1M

```bash
source .venv/bin/activate && python .claude/skills/fund-firm/scripts/fund_firm.py deposit
```

This deposits $1,000,000 via the existing ACH relationship and prints the transfer ID, status, and expected post-settlement balance.

### Step 3: Report to user

Present a summary:

```
Firm Account Fund Summary
─────────────────────────
Before:    $X,XXX,XXX.XX
Deposit:   $1,000,000.00
Expected:  $X,XXX,XXX.XX (after settlement)
Transfer:  <transfer_id>
Status:    <status>
```

Sandbox ACH deposits settle within ~10-30 minutes.

## Key References

| File | Purpose |
|------|---------|
| `app/brokers/alpaca_broker/broker.py` | `ProphitBroker` unified broker interface |
| `app/brokers/alpaca_broker/funding.py` | `BrokerFunding.deposit()` for ACH transfers |
| `app/repositories/user/funding.py` | `instant_deposit()` for journaling to users |

## Constants

| Value | Description |
|-------|-------------|
| `37dd29d5-e94f-3251-bbfc-31db312c09e1` | Firm sweep account ID |
| `2bebdee2-033f-4679-ab72-6752f5e8706c` | ACH relationship ID (G4ep Firm Bank) |
