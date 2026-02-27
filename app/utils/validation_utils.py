"""
Validation utilities for ticker symbols and portfolio structures.

This module provides reusable validation functions for ensuring data integrity
across the application, particularly for financial instruments and portfolio data.
"""

from typing import Dict, Any, Tuple, Union

from pydantic import ValidationError
from app.models.portfolio_models import (
    PortfolioInput,
    PortfolioPosition,
    PositionType,
)


def validate_ticker(ticker: str) -> str:
    """
    Validate ticker format and return normalized ticker.
    
    Args:
        ticker: Ticker symbol to validate
        
    Returns:
        str: Normalized ticker symbol (uppercase)
        
    Raises:
        ValueError: If ticker format is invalid
    """
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    
    if not isinstance(ticker, str):
        raise ValueError("Ticker must be a string")
    
    ticker = ticker.strip().upper()
    
    if not ticker.isalpha() or len(ticker) < 1 or len(ticker) > 10:
        raise ValueError("Ticker must be 1-10 alphabetic characters")
    
    return ticker


def normalize_portfolio_input(data: Any) -> PortfolioInput:
    """Normalize various portfolio input shapes to PortfolioInput.

    Accepted legacy formats:
    - {ticker: {allocation, position}}
    - {ticker: {conviction, position}}
    - {ticker: {risk_allocation, position}}
    - {ticker: (weight_or_allocation, position)}
    - {ticker: signed_weight}
    - {ticker: PortfolioPosition}
    - PortfolioInput (returned as-is)
    """
    if isinstance(data, PortfolioInput):
        return data

    if not isinstance(data, dict) or not data:
        raise ValueError("Portfolio input must be a non-empty dictionary or PortfolioInput")

    normalized: Dict[str, PortfolioPosition] = {}

    for raw_ticker, raw_value in data.items():
        ticker = validate_ticker(raw_ticker)

        # Already a PortfolioPosition
        if isinstance(raw_value, PortfolioPosition):
            normalized[ticker] = raw_value
            continue

        allocation: Union[int, float]
        position: Union[str, PositionType]

        if isinstance(raw_value, dict):
            if 'allocation' in raw_value:
                allocation = float(raw_value['allocation'])
            elif 'conviction' in raw_value:
                allocation = float(raw_value['conviction'])
            elif 'risk_allocation' in raw_value:
                allocation = float(raw_value['risk_allocation'])
            else:
                raise ValueError(f"{ticker}: missing 'allocation'/'conviction'/'risk_allocation'")

            if 'position' not in raw_value:
                raise ValueError(f"{ticker}: missing 'position'")
            position = str(raw_value['position']).lower()

        elif isinstance(raw_value, (tuple, list)) and len(raw_value) == 2:
            weight_or_alloc, pos = raw_value
            allocation = abs(float(weight_or_alloc))
            position = str(pos).lower()

        elif isinstance(raw_value, (int, float)):
            # signed weight
            w = float(raw_value)
            allocation = abs(w)
            position = 'long' if w >= 0 else 'short'

        else:
            raise ValueError(f"{ticker}: unsupported value type {type(raw_value)}")

        if not 0.0 <= allocation <= 1.0:
            raise ValueError(f"{ticker}: allocation must be between 0 and 1 (decimal)")

        if position not in ('long', 'short'):
            raise ValueError(f"{ticker}: position must be 'long' or 'short'")

        normalized[ticker] = PortfolioPosition(allocation=allocation, position=position)  # validator lowercases

    try:
        return PortfolioInput(normalized)
    except ValidationError as e:
        raise ValueError(f"Invalid portfolio input: {e}")


def validate_portfolio_dict(portfolio_dict: dict) -> dict:
    """Backwards-compatible validator returning a plain dict.

    Normalizes to the canonical schema and returns:
        {ticker: {allocation: float, position: 'long'|'short'}}
    """
    portfolio = normalize_portfolio_input(portfolio_dict)
    return {
        t: {
            'allocation': float(p.allocation),
            'position': p.position.value,
        }
        for t, p in portfolio.root.items()
    }

def validate_portfolio_input(portfolio: PortfolioInput | dict) -> PortfolioInput:
    """Explicit validator that returns a `PortfolioInput`.

    Accepts either a `PortfolioInput` or a legacy dict and normalizes to
    the canonical `PortfolioInput` schema.
    """
    return normalize_portfolio_input(portfolio)
