"""Portfolio preference CRUD operations."""

import uuid
from typing import List, Optional, Dict

from prophitai_data.db.config import UserSession
from prophitai_data.db.models.user import *
from prophitai_shared import get_current_utc_time
from prophitai_data.session import with_session, with_transaction


@with_session('user')
def get_portfolio_preference(portfolio_id: uuid.UUID, session=None) -> Optional[Dict]:
    """
    Get portfolio preferences by portfolio ID.

    Args:
        portfolio_id: Portfolio UUID

    Returns:
        Dictionary containing preference data, or None if not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    preference = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).first()

    if not preference:
        return None

    return {
        'id': preference.id,
        'portfolio_id': str(preference.portfolio_id),
        'description': preference.description,
        # Risk Profile
        'risk_tolerance': preference.risk_tolerance,
        'investment_time_horizon': preference.investment_time_horizon,
        'liquidity_needs': preference.liquidity_needs,
        # Asset Allocations
        'equities_allocation': float(preference.equities_allocation) if preference.equities_allocation else None,
        'fixed_income_allocation': float(preference.fixed_income_allocation) if preference.fixed_income_allocation else None,
        'commodities_allocation': float(preference.commodities_allocation) if preference.commodities_allocation else None,
        'currencies_allocation': float(preference.currencies_allocation) if preference.currencies_allocation else None,
        'cryptocurrencies_allocation': float(preference.cryptocurrencies_allocation) if preference.cryptocurrencies_allocation else None,
        'alternatives_hedge_funds_allocation': float(preference.alternatives_hedge_funds_allocation) if preference.alternatives_hedge_funds_allocation else None,
        'alternatives_pe_vc_allocation': float(preference.alternatives_pe_vc_allocation) if preference.alternatives_pe_vc_allocation else None,
        'cash_allocation': float(preference.cash_allocation) if preference.cash_allocation else None,
        # Equity Sector Preferences
        'equity_sector_communication_services': preference.equity_sector_communication_services,
        'equity_sector_consumer_discretionary': preference.equity_sector_consumer_discretionary,
        'equity_sector_consumer_staples': preference.equity_sector_consumer_staples,
        'equity_sector_energy': preference.equity_sector_energy,
        'equity_sector_financials': preference.equity_sector_financials,
        'equity_sector_health_care': preference.equity_sector_health_care,
        'equity_sector_industrials': preference.equity_sector_industrials,
        'equity_sector_information_technology': preference.equity_sector_information_technology,
        'equity_sector_materials': preference.equity_sector_materials,
        'equity_sector_real_estate': preference.equity_sector_real_estate,
        'equity_sector_utilities': preference.equity_sector_utilities,
        # Fixed Income Sector Preferences
        'fixed_income_sector_sovereign_treasuries': preference.fixed_income_sector_sovereign_treasuries,
        'fixed_income_sector_ig_credit': preference.fixed_income_sector_ig_credit,
        'fixed_income_sector_high_yield': preference.fixed_income_sector_high_yield,
        'fixed_income_sector_securitized_products': preference.fixed_income_sector_securitized_products,
        # Ticker Lists
        'tickers_to_include': preference.tickers_to_include,
        'tickers_to_exclude': preference.tickers_to_exclude,
        # Timestamps
        'created_date': preference.created_date.isoformat() if preference.created_date else None,
        'updated_date': preference.updated_date.isoformat() if preference.updated_date else None,
    }


@with_transaction('user')
def create_portfolio_preference(
    portfolio_id: uuid.UUID,
    description: Optional[str] = None,
    risk_tolerance: Optional[str] = None,
    investment_time_horizon: Optional[str] = None,
    liquidity_needs: Optional[str] = None,
    equities_allocation: Optional[float] = None,
    fixed_income_allocation: Optional[float] = None,
    commodities_allocation: Optional[float] = None,
    currencies_allocation: Optional[float] = None,
    cryptocurrencies_allocation: Optional[float] = None,
    alternatives_hedge_funds_allocation: Optional[float] = None,
    alternatives_pe_vc_allocation: Optional[float] = None,
    cash_allocation: Optional[float] = None,
    equity_sector_communication_services: Optional[str] = None,
    equity_sector_consumer_discretionary: Optional[str] = None,
    equity_sector_consumer_staples: Optional[str] = None,
    equity_sector_energy: Optional[str] = None,
    equity_sector_financials: Optional[str] = None,
    equity_sector_health_care: Optional[str] = None,
    equity_sector_industrials: Optional[str] = None,
    equity_sector_information_technology: Optional[str] = None,
    equity_sector_materials: Optional[str] = None,
    equity_sector_real_estate: Optional[str] = None,
    equity_sector_utilities: Optional[str] = None,
    fixed_income_sector_sovereign_treasuries: Optional[str] = None,
    fixed_income_sector_ig_credit: Optional[str] = None,
    fixed_income_sector_high_yield: Optional[str] = None,
    fixed_income_sector_securitized_products: Optional[str] = None,
    tickers_to_include: Optional[List[str]] = None,
    tickers_to_exclude: Optional[List[str]] = None,
    session=None
) -> Dict:
    """
    Create portfolio preferences for a portfolio.

    Args:
        portfolio_id: Portfolio UUID (must exist)
        description: Portfolio description
        risk_tolerance: One of 'Capital Preservation', 'Income', 'Balanced/Moderate Growth',
                       'Growth', 'Aggressive Growth/Speculation'
        investment_time_horizon: One of 'Short term (0-2 years)', 'Medium term (3-7 years)',
                                'Long term (8+ years)'
        liquidity_needs: One of 'High', 'Medium', 'Low'
        *_allocation: Decimal values 0-1 for asset class allocations
        equity_sector_*: One of 'Include', 'Exclude', 'Not Selected'
        fixed_income_sector_*: One of 'Include', 'Exclude', 'Not Selected'
        tickers_to_include: List of tickers to include
        tickers_to_exclude: List of tickers to exclude

    Returns:
        Dictionary containing the created preference data

    Raises:
        ValueError: If portfolio doesn't exist or preference already exists
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    # Verify portfolio exists
    portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Check if preference already exists
    existing = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).first()
    if existing:
        raise ValueError(f"Preference already exists for portfolio {portfolio_id}")

    now = get_current_utc_time()
    preference = PortfolioPreference(
        portfolio_id=portfolio_id,
        description=description,
        risk_tolerance=risk_tolerance,
        investment_time_horizon=investment_time_horizon,
        liquidity_needs=liquidity_needs,
        equities_allocation=equities_allocation,
        fixed_income_allocation=fixed_income_allocation,
        commodities_allocation=commodities_allocation,
        currencies_allocation=currencies_allocation,
        cryptocurrencies_allocation=cryptocurrencies_allocation,
        alternatives_hedge_funds_allocation=alternatives_hedge_funds_allocation,
        alternatives_pe_vc_allocation=alternatives_pe_vc_allocation,
        cash_allocation=cash_allocation,
        equity_sector_communication_services=equity_sector_communication_services or 'Not Selected',
        equity_sector_consumer_discretionary=equity_sector_consumer_discretionary or 'Not Selected',
        equity_sector_consumer_staples=equity_sector_consumer_staples or 'Not Selected',
        equity_sector_energy=equity_sector_energy or 'Not Selected',
        equity_sector_financials=equity_sector_financials or 'Not Selected',
        equity_sector_health_care=equity_sector_health_care or 'Not Selected',
        equity_sector_industrials=equity_sector_industrials or 'Not Selected',
        equity_sector_information_technology=equity_sector_information_technology or 'Not Selected',
        equity_sector_materials=equity_sector_materials or 'Not Selected',
        equity_sector_real_estate=equity_sector_real_estate or 'Not Selected',
        equity_sector_utilities=equity_sector_utilities or 'Not Selected',
        fixed_income_sector_sovereign_treasuries=fixed_income_sector_sovereign_treasuries or 'Not Selected',
        fixed_income_sector_ig_credit=fixed_income_sector_ig_credit or 'Not Selected',
        fixed_income_sector_high_yield=fixed_income_sector_high_yield or 'Not Selected',
        fixed_income_sector_securitized_products=fixed_income_sector_securitized_products or 'Not Selected',
        tickers_to_include=tickers_to_include,
        tickers_to_exclude=tickers_to_exclude,
        created_date=now,
        updated_date=now,
    )
    session.add(preference)
    session.flush()

    return {
        'id': preference.id,
        'portfolio_id': str(preference.portfolio_id),
        'created_date': preference.created_date.isoformat(),
    }


@with_transaction('user')
def update_portfolio_preference(
    portfolio_id: uuid.UUID,
    description: Optional[str] = None,
    risk_tolerance: Optional[str] = None,
    investment_time_horizon: Optional[str] = None,
    liquidity_needs: Optional[str] = None,
    equities_allocation: Optional[float] = None,
    fixed_income_allocation: Optional[float] = None,
    commodities_allocation: Optional[float] = None,
    currencies_allocation: Optional[float] = None,
    cryptocurrencies_allocation: Optional[float] = None,
    alternatives_hedge_funds_allocation: Optional[float] = None,
    alternatives_pe_vc_allocation: Optional[float] = None,
    cash_allocation: Optional[float] = None,
    equity_sector_communication_services: Optional[str] = None,
    equity_sector_consumer_discretionary: Optional[str] = None,
    equity_sector_consumer_staples: Optional[str] = None,
    equity_sector_energy: Optional[str] = None,
    equity_sector_financials: Optional[str] = None,
    equity_sector_health_care: Optional[str] = None,
    equity_sector_industrials: Optional[str] = None,
    equity_sector_information_technology: Optional[str] = None,
    equity_sector_materials: Optional[str] = None,
    equity_sector_real_estate: Optional[str] = None,
    equity_sector_utilities: Optional[str] = None,
    fixed_income_sector_sovereign_treasuries: Optional[str] = None,
    fixed_income_sector_ig_credit: Optional[str] = None,
    fixed_income_sector_high_yield: Optional[str] = None,
    fixed_income_sector_securitized_products: Optional[str] = None,
    tickers_to_include: Optional[List[str]] = None,
    tickers_to_exclude: Optional[List[str]] = None,
    session=None
) -> bool:
    """
    Update portfolio preferences. Only provided fields are updated.

    Args:
        portfolio_id: Portfolio UUID
        [other args]: Fields to update (None values are ignored)

    Returns:
        True if updated, False if preference not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    preference = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).first()

    if not preference:
        return False

    # Update only provided fields
    if description is not None:
        preference.description = description
    if risk_tolerance is not None:
        preference.risk_tolerance = risk_tolerance
    if investment_time_horizon is not None:
        preference.investment_time_horizon = investment_time_horizon
    if liquidity_needs is not None:
        preference.liquidity_needs = liquidity_needs
    if equities_allocation is not None:
        preference.equities_allocation = equities_allocation
    if fixed_income_allocation is not None:
        preference.fixed_income_allocation = fixed_income_allocation
    if commodities_allocation is not None:
        preference.commodities_allocation = commodities_allocation
    if currencies_allocation is not None:
        preference.currencies_allocation = currencies_allocation
    if cryptocurrencies_allocation is not None:
        preference.cryptocurrencies_allocation = cryptocurrencies_allocation
    if alternatives_hedge_funds_allocation is not None:
        preference.alternatives_hedge_funds_allocation = alternatives_hedge_funds_allocation
    if alternatives_pe_vc_allocation is not None:
        preference.alternatives_pe_vc_allocation = alternatives_pe_vc_allocation
    if cash_allocation is not None:
        preference.cash_allocation = cash_allocation
    if equity_sector_communication_services is not None:
        preference.equity_sector_communication_services = equity_sector_communication_services
    if equity_sector_consumer_discretionary is not None:
        preference.equity_sector_consumer_discretionary = equity_sector_consumer_discretionary
    if equity_sector_consumer_staples is not None:
        preference.equity_sector_consumer_staples = equity_sector_consumer_staples
    if equity_sector_energy is not None:
        preference.equity_sector_energy = equity_sector_energy
    if equity_sector_financials is not None:
        preference.equity_sector_financials = equity_sector_financials
    if equity_sector_health_care is not None:
        preference.equity_sector_health_care = equity_sector_health_care
    if equity_sector_industrials is not None:
        preference.equity_sector_industrials = equity_sector_industrials
    if equity_sector_information_technology is not None:
        preference.equity_sector_information_technology = equity_sector_information_technology
    if equity_sector_materials is not None:
        preference.equity_sector_materials = equity_sector_materials
    if equity_sector_real_estate is not None:
        preference.equity_sector_real_estate = equity_sector_real_estate
    if equity_sector_utilities is not None:
        preference.equity_sector_utilities = equity_sector_utilities
    if fixed_income_sector_sovereign_treasuries is not None:
        preference.fixed_income_sector_sovereign_treasuries = fixed_income_sector_sovereign_treasuries
    if fixed_income_sector_ig_credit is not None:
        preference.fixed_income_sector_ig_credit = fixed_income_sector_ig_credit
    if fixed_income_sector_high_yield is not None:
        preference.fixed_income_sector_high_yield = fixed_income_sector_high_yield
    if fixed_income_sector_securitized_products is not None:
        preference.fixed_income_sector_securitized_products = fixed_income_sector_securitized_products
    if tickers_to_include is not None:
        preference.tickers_to_include = tickers_to_include
    if tickers_to_exclude is not None:
        preference.tickers_to_exclude = tickers_to_exclude

    preference.updated_date = get_current_utc_time()
    return True


@with_transaction('user')
def delete_portfolio_preference(portfolio_id: uuid.UUID, session=None) -> bool:
    """
    Delete portfolio preferences for a portfolio.

    Args:
        portfolio_id: Portfolio UUID

    Returns:
        True if deleted, False if not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    result = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).delete(synchronize_session=False)

    return result > 0
