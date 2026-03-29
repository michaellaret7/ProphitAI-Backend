"""
Portfolio monitoring alert messages.

This module provides functions to send consolidated alert messages to users
when portfolio risk conditions are detected. One message per portfolio.
"""
from uuid import UUID

from prophitai_data.jobs.portfolio.models import (
    DriftResult,
    DrawdownResult,
    PortfolioCorrelationResult,
)
from prophitai_data.repositories.messaging.conversations import get_or_create_conversation
from prophitai_data.repositories.messaging.messages import create_message

PROPHITAI_SYSTEM_USER_ID = UUID("e7ab723f-a415-4f3c-8445-4eaf08cf605e")

def _build_allocation_drift_section(result: DriftResult) -> str:
    """Build the allocation drift section of the alert message."""
    drift_lines = []
    for sector, details in result.flagged_sectors.items():
        direction = "over" if details.drift > 0 else "under"
        drift_lines.append(
            f"  - {sector.title()}: {details.current_allocation:.1%} "
            f"(target: {details.target_allocation:.1%}, {direction} by {abs(details.drift):.1%})"
        )

    sectors_text = "\n".join(drift_lines)

    return f"""Allocation Drift

Your portfolio has drifted from target allocations:

{sectors_text}

Consider rebalancing to align with your investment preferences."""


def _build_drawdown_section(result: DrawdownResult) -> str:
    """Build the drawdown section of the alert message."""
    drawdown_lines = []
    for ticker, details in result.flagged_positions.items():
        drawdown_lines.append(
            f"  - {ticker}: {details.current_drawdown:.1%} drawdown "
            f"(max: {details.max_drawdown:.1%}, peak: {details.peak_date})"
        )

    positions_text = "\n".join(drawdown_lines)

    return f"""Drawdown Alert

The following positions are experiencing significant drawdowns:

{positions_text}

Review these positions and consider whether action is needed."""


def _build_correlation_section(result: PortfolioCorrelationResult) -> str:
    """Build the correlation risk section of the alert message."""
    if result.recent_avg > 0.5:
        risk_description = "High average correlation indicates positions are moving together."
    else:
        risk_description = "Correlation spike detected - diversification may be compromised."

    return f"""Correlation Risk

{risk_description}

Metrics:
  - Recent avg correlation: {result.recent_avg:.2f}
  - Baseline avg correlation: {result.baseline_avg:.2f}
  - Change: {result.change:+.2f}
  - Trend: {result.trend}
  - Z-Score: {result.z_score:.1f}

High correlation means your positions may all decline together during market stress."""


def send_portfolio_alert(
    user_id: UUID,
    portfolio_id: UUID,
    portfolio_name: str,
    drift_result: DriftResult | None = None,
    drawdown_result: DrawdownResult | None = None,
    correlation_result: PortfolioCorrelationResult | None = None
) -> bool:
    """
    Send a consolidated alert message for a portfolio.

    Combines all triggered alerts into one message with a portfolio header.
    Only sends if at least one alert is triggered.

    Args:
        user_id: The portfolio owner's user ID.
        portfolio_id: The portfolio's UUID.
        portfolio_name: Name of the portfolio.
        drift_result: Optional DriftResult from detection.
        drawdown_result: Optional DrawdownResult from detection.
        correlation_result: Optional PortfolioCorrelationResult from detection.

    Returns:
        True if message sent successfully, False if no alerts or send failed.
    """
    sections = []

    if drift_result and drift_result.triggered:
        sections.append(_build_allocation_drift_section(drift_result))

    if drawdown_result and drawdown_result.triggered:
        sections.append(_build_drawdown_section(drawdown_result))

    if correlation_result and correlation_result.triggered:
        sections.append(_build_correlation_section(correlation_result))

    # No alerts triggered
    if not sections:
        return False

    # Build the full message with portfolio header
    header = f"[@{portfolio_name}](portfolio:{portfolio_id})"
    body = "\n\n---\n\n".join(sections)
    message = f"{header}\n\n{body}"

    return _send_system_message(user_id, message)


def _send_system_message(user_id: UUID, content: str) -> bool:
    """
    Send a message from the ProphitAI system user to a user.

    Args:
        user_id: The recipient user's ID.
        content: Message content.

    Returns:
        True if message sent successfully, False otherwise.
    """
    conversation = get_or_create_conversation(PROPHITAI_SYSTEM_USER_ID, user_id)
    if not conversation:
        return False

    message = create_message(
        conversation_id=conversation.id,
        sender_id=PROPHITAI_SYSTEM_USER_ID,
        content=content,
        message_type="alert"
    )

    return message is not None
