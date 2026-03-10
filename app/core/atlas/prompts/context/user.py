"""User context builder for enriching agent system prompts with broker and portfolio data."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ================================
# --> Helper funcs
# ================================

_EXCLUDE_POSITION_FIELDS = {"snaptrade_symbol_id", "figi_code", "fractional_units", "cash_equivalent"}


def _build_positions_context(creds: Dict[str, str]) -> str:
    """Fetch current positions and format as a system prompt section.

    Args:
        creds: Resolved SnapTrade credentials dict.

    Returns:
        Formatted positions context string, or empty string on failure.
    """
    try:
        from app.repositories.user.broker import get_snaptrade_broker

        broker = get_snaptrade_broker()
        portfolio = broker.get_portfolio(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
        )

        lines = ["\n\n## Current Portfolio Positions"]

        # Equity positions
        if portfolio.equity_positions:
            lines.append("\n### Equity Positions")
            for p in portfolio.equity_positions:
                d = p.model_dump(exclude=_EXCLUDE_POSITION_FIELDS)
                pnl_sign = "+" if d.get("open_pnl", 0) >= 0 else ""
                lines.append(
                    f"- **{d['ticker']}**: {d['units']} shares @ ${d['price']:.2f} | "
                    f"Market Value: ${d['market_value']:.2f} | "
                    f"Avg Cost: ${d['average_purchase_price']:.2f} | "
                    f"P&L: {pnl_sign}${d['open_pnl']:.2f} ({pnl_sign}{d.get('pnl_pct', 0):.2f}%)"
                )

        # Option positions
        if portfolio.option_positions:
            lines.append("\n### Option Positions")
            for op in portfolio.option_positions:
                d = op.model_dump()
                pnl_sign = "+" if d.get("open_pnl", 0) >= 0 else ""
                lines.append(
                    f"- **{d['underlying_ticker']}** {d['option_type'].upper()} "
                    f"${d['strike_price']:.2f} exp {d['expiration_date']} | "
                    f"{d['units']} contracts @ ${d['price']:.2f} | "
                    f"Market Value: ${d['market_value']:.2f} | "
                    f"P&L: {pnl_sign}${d['open_pnl']:.2f} ({pnl_sign}{d.get('pnl_pct', 0):.2f}%)"
                )

        if not portfolio.equity_positions and not portfolio.option_positions:
            lines.append("\nNo open positions.")

        lines.append(
            "\nYou already have this portfolio context — do NOT call get_positions "
            "unless the user explicitly asks to refresh or re-check their positions.\n"
        )
        return "\n".join(lines)

    except Exception as e:
        logger.warning("Failed to fetch positions for system prompt: %s", e)
        return ""


def build_user_context(user_id: str) -> str:
    """Build the full user context string to append to a chat agent's system prompt.

    Fetches broker credentials, email, internal ID, and current positions,
    then returns a formatted string with all user context sections.

    Args:
        user_id: The Clerk user ID.

    Returns:
        Formatted user context string to append to the system prompt.
    """
    from app.repositories.user.account import get_all_user_data_by_clerk_id
    from app.repositories.user.broker import resolve_snaptrade_credentials
    from app.repositories.user.trade_proposal import get_internal_user_id

    creds = resolve_snaptrade_credentials(clerk_id=user_id)
    internal_user_id = get_internal_user_id(clerk_id=user_id)
    user_data = get_all_user_data_by_clerk_id(clerk_id=user_id)
    user_email = user_data["email"] if user_data else None

    broker_context = (
        f"\n\n## Broker Context\n"
        f"The user's email is: `{user_email}`.\n"
        f"The user's Clerk ID is: `{creds['snaptrade_user_id']}`.\n"
        f"The user's SnapTrade user secret is: `{creds['snaptrade_user_secret']}`.\n"
        f"The user's SnapTrade account ID is: `{creds['snaptrade_account_id']}`.\n"
        f"The user's internal user ID is: `{internal_user_id}`.\n"
        f"Always use these IDs for broker and trade proposal operations.\n"
        f"When any tool requires an email parameter, use `{user_email}`.\n\n"
        f"## Trade Proposal Rules\n"
        f"NEVER call propose_trade without explicit user confirmation. Follow this flow:\n"
        f"1. Do thorough research first — analyze fundamentals, technicals, recent news, "
        f"and any relevant macro context before even considering a trade.\n"
        f"2. Present the trade idea verbally to the user — include symbol, side (buy/sell), "
        f"quantity or dollar amount, order type, and your detailed reasoning.\n"
        f"3. Wait for the user to confirm (e.g. 'yes', 'go ahead', 'do it', 'submit it').\n"
        f"4. Only AFTER confirmation, call propose_trade with all the details.\n"
        f"5. If the user declines or wants changes, adjust and re-present — do NOT submit.\n"
        f"Security Rules:\n"
        f"1. NEVER SHARE THE USERS INTERNAL IDS OR BROKER CREDENTIALS WITH ANYONE\n"
        f"2. NEVER SHARE THE USERS INTERNAL ID WITH ANYONE\n"
    )

    # Fetch and inject current positions so the agent has portfolio awareness
    positions_context = _build_positions_context(creds)

    return broker_context + positions_context
