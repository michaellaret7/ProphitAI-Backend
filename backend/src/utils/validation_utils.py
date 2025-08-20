"""
Validation utilities for ticker symbols and portfolio structures.

This module provides reusable validation functions for ensuring data integrity
across the application, particularly for financial instruments and portfolio data.
"""

from typing import Dict, Any


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


def validate_portfolio_dict(portfolio_dict: dict) -> dict:
    """
    Validate portfolio dictionary structure and values.
    
    Args:
        portfolio_dict: Portfolio dictionary to validate
        
    Returns:
        dict: Validated portfolio dictionary with normalized values
        
    Raises:
        ValueError: If portfolio structure is invalid
    """
    if not portfolio_dict:
        raise ValueError("Portfolio dictionary cannot be empty")
    
    if not isinstance(portfolio_dict, dict):
        raise ValueError("Portfolio must be a dictionary")
    
    validated_portfolio = {}
    
    for ticker, details in portfolio_dict.items():
        # Validate ticker
        validated_ticker = validate_ticker(ticker)
        
        # Validate details structure
        if not isinstance(details, dict):
            raise ValueError(f"Details for {ticker} must be a dictionary")
        
        if 'conviction' not in details or 'position' not in details:
            raise ValueError(f"Ticker {ticker} must have 'conviction' and 'position' keys")
        
        # Validate conviction value
        conviction = details['conviction']
        if not isinstance(conviction, (int, float)):
            raise ValueError(f"Conviction for {ticker} must be a number")
        
        if not 0.0 <= conviction <= 1.0:
            raise ValueError(f"Conviction for {ticker} must be between 0.0 and 1.0")
        
        # Validate position value
        position = details['position']
        if not isinstance(position, str):
            raise ValueError(f"Position for {ticker} must be a string")
        
        position = position.lower()
        if position not in ['long', 'short']:
            raise ValueError(f"Position for {ticker} must be 'long' or 'short'")
        
        validated_portfolio[validated_ticker] = {
            'conviction': float(conviction),
            'position': position
        }
    
    return validated_portfolio
