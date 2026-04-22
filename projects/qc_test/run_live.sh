#!/usr/bin/env bash
# Launch the Lean live paper-trading container via Interactive Brokers.
#
# Credentials are loaded from the repo-root .env (which is gitignored).
# Run from anywhere — the script locates its own directory.
#
# Usage:
#   ./projects/qc_test/run_live.sh
set -euo pipefail

#     ================================
# --> Resolve paths + load .env
#     ================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

IB_USER="${IB_USER:?IB_USER missing — add it to $ENV_FILE}"
IB_PASSWORD="${IB_PASSWORD:?IB_PASSWORD missing — add it to $ENV_FILE}"
IB_ACCOUNT="${IB_ACCOUNT:?IB_ACCOUNT missing — add it to $ENV_FILE}"

#     ================================
# --> Launch Lean live container
#     ================================
# Reason: paper vs live is inferred from the account id prefix
# (DU* = paper, U* = live); there's no --ib-trading-mode flag in the CLI.

cd "$SCRIPT_DIR"

lean live deploy intraday_longshort \
    --brokerage "interactive brokers" \
    --ib-user-name "$IB_USER" \
    --ib-password "$IB_PASSWORD" \
    --ib-account "$IB_ACCOUNT" \
    --data-provider-live "interactive brokers" \
    --data-provider-historical "local" \
    --no-update
