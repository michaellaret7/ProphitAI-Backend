# database/models/user_models.py
"""
Complete User Data Models for all tables in the user_data database
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text, UniqueConstraint, CheckConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid
from app.db.core.db_config import UserBase
from app.utils.time_utils import get_current_utc_time

# =============================================================================
# USER DATA SCHEMA
# =============================================================================

class User(UserBase):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, nullable=False, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    creation_date = Column(DateTime, default=get_current_utc_time)

    # Direct company association
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True, index=True)
    role = Column(String, default='member')
    
    # Relationships
    company = relationship('Company', back_populates='users')
    watchlists = relationship('Watchlist', back_populates='user', cascade='all, delete-orphan')
    # subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')

class Company(UserBase):
    __tablename__ = 'companies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    creation_date = Column(DateTime, default=get_current_utc_time)
    seats = Column(Integer)
    
    # Relationships
    users = relationship('User', back_populates='company')
    # subscriptions = relationship('Subscription', back_populates='company', cascade='all, delete-orphan')

class Portfolio(UserBase):
    __tablename__ = 'portfolios'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    nav = Column(Float, nullable=True)  # Net Asset Value - total portfolio value
    created_date = Column(DateTime, default=get_current_utc_time)
    updated_date = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)
    is_current = Column(Boolean, default=False, index=True)
    is_discretionary = Column(Boolean, default=False, index=True)
    alert_state = Column(JSONB, nullable=True)  # Tracks last alert state per type for deduplication

    # Relationships
    user = relationship('User', backref='portfolios')
    items = relationship('PortfolioItem', back_populates='portfolio', cascade='all, delete-orphan')
    preferences = relationship('PortfolioPreference', back_populates='portfolio', uselist=False, cascade='all, delete-orphan')

class PortfolioItem(UserBase):
    __tablename__ = 'portfolio_items'

    portfolio_id = Column(UUID(as_uuid=True), ForeignKey('portfolios.id', ondelete='CASCADE'), primary_key=True)
    ticker = Column(String, primary_key=True)
    allocation = Column(Float)  # Decimal format: 0.25 = 25%, range 0-1
    num_shares = Column(Integer, nullable=True)
    position_nav = Column(Float, nullable=True)  # Position value: num_shares * current_price
    supporting_metrics = Column(JSONB, nullable=True)
    reason_for_rec = Column(Text, nullable=True)
    created_date = Column(DateTime, default=get_current_utc_time)
    updated_date = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    # Relationships
    portfolio = relationship('Portfolio', back_populates='items')


class PortfolioPreference(UserBase):
    """
    Portfolio preferences and investment guidelines.

    Each portfolio has one associated preference record that defines:
    - Risk tolerance and investment objectives
    - Asset allocation targets
    - Sector preferences (include/exclude)
    - Ticker restrictions
    """
    __tablename__ = 'portfolio_preferences'
    __table_args__ = (
        # Ensure allocation values are between 0 and 1
        CheckConstraint('equities_allocation >= 0 AND equities_allocation <= 1', name='chk_equities_allocation'),
        CheckConstraint('fixed_income_allocation >= 0 AND fixed_income_allocation <= 1', name='chk_fixed_income_allocation'),
        CheckConstraint('commodities_allocation >= 0 AND commodities_allocation <= 1', name='chk_commodities_allocation'),
        CheckConstraint('currencies_allocation >= 0 AND currencies_allocation <= 1', name='chk_currencies_allocation'),
        CheckConstraint('cryptocurrencies_allocation >= 0 AND cryptocurrencies_allocation <= 1', name='chk_cryptocurrencies_allocation'),
        CheckConstraint('alternatives_hedge_funds_allocation >= 0 AND alternatives_hedge_funds_allocation <= 1', name='chk_hedge_funds_allocation'),
        CheckConstraint('alternatives_pe_vc_allocation >= 0 AND alternatives_pe_vc_allocation <= 1', name='chk_pe_vc_allocation'),
        CheckConstraint('cash_allocation >= 0 AND cash_allocation <= 1', name='chk_cash_allocation'),
        # Ensure enum-like string columns have valid values
        CheckConstraint(
            "risk_tolerance IN ('Capital Preservation', 'Income', 'Balanced/Moderate Growth', 'Growth', 'Aggressive Growth/Speculation')",
            name='chk_risk_tolerance'
        ),
        CheckConstraint(
            "investment_time_horizon IN ('Short term (0-2 years)', 'Medium term (3-7 years)', 'Long term (8+ years)')",
            name='chk_time_horizon'
        ),
        CheckConstraint(
            "liquidity_needs IN ('High', 'Medium', 'Low')",
            name='chk_liquidity_needs'
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)  # Portfolio description

    # Risk Profile
    risk_tolerance = Column(String(50), nullable=True)
    investment_time_horizon = Column(String(30), nullable=True)
    liquidity_needs = Column(String(10), nullable=True)

    # Asset Allocation Preferences (decimal 0-1)
    equities_allocation = Column(Numeric(5, 4), nullable=True)
    fixed_income_allocation = Column(Numeric(5, 4), nullable=True)
    commodities_allocation = Column(Numeric(5, 4), nullable=True)
    currencies_allocation = Column(Numeric(5, 4), nullable=True)
    cryptocurrencies_allocation = Column(Numeric(5, 4), nullable=True)
    alternatives_hedge_funds_allocation = Column(Numeric(5, 4), nullable=True)
    alternatives_pe_vc_allocation = Column(Numeric(5, 4), nullable=True)
    cash_allocation = Column(Numeric(5, 4), nullable=True)

    # Equity Sector Preferences ('Include', 'Exclude', 'Not Selected')
    equity_sector_communication_services = Column(String(15), default='Not Selected')
    equity_sector_consumer_discretionary = Column(String(15), default='Not Selected')
    equity_sector_consumer_staples = Column(String(15), default='Not Selected')
    equity_sector_energy = Column(String(15), default='Not Selected')
    equity_sector_financials = Column(String(15), default='Not Selected')
    equity_sector_health_care = Column(String(15), default='Not Selected')
    equity_sector_industrials = Column(String(15), default='Not Selected')
    equity_sector_information_technology = Column(String(15), default='Not Selected')
    equity_sector_materials = Column(String(15), default='Not Selected')
    equity_sector_real_estate = Column(String(15), default='Not Selected')
    equity_sector_utilities = Column(String(15), default='Not Selected')

    # Fixed Income Sector Preferences ('Include', 'Exclude', 'Not Selected')
    fixed_income_sector_sovereign_treasuries = Column(String(15), default='Not Selected')
    fixed_income_sector_ig_credit = Column(String(15), default='Not Selected')
    fixed_income_sector_high_yield = Column(String(15), default='Not Selected')
    fixed_income_sector_securitized_products = Column(String(15), default='Not Selected')

    # Ticker Lists
    tickers_to_include = Column(ARRAY(String), nullable=True)
    tickers_to_exclude = Column(ARRAY(String), nullable=True)

    # Timestamps
    created_date = Column(DateTime, default=get_current_utc_time)
    updated_date = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    # Relationships
    portfolio = relationship('Portfolio', back_populates='preferences')

class Watchlist(UserBase):
    __tablename__ = 'watchlists'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String, nullable=False)
    creation_date = Column(DateTime, default=get_current_utc_time)
    updated_date = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    # Relationships
    user = relationship('User', back_populates='watchlists')
    items = relationship('WatchlistItem', back_populates='watchlist', cascade='all, delete-orphan')

class WatchlistItem(UserBase):
    __tablename__ = 'watchlist_items'

    watchlist_id = Column(UUID(as_uuid=True), ForeignKey('watchlists.id', ondelete='CASCADE'), primary_key=True)
    ticker = Column(String, primary_key=True)
    price_on_inception = Column(Float, nullable=True)
    added_at = Column(DateTime, default=get_current_utc_time)

    # Relationships
    watchlist = relationship('Watchlist', back_populates='items')


# =============================================================================
# MESSAGING SCHEMA
# =============================================================================

class Conversation(UserBase):
    """
    1-on-1 direct message conversation between two users.

    user_1_id and user_2_id should be ordered by UUID when creating
    to ensure uniqueness (prevents duplicate conversations between same users).

    Read state is tracked via last_read_at timestamps per user.
    To check unread: user_X_last_read_at < latest_message.created_at
    To get unread count: COUNT messages WHERE created_at > user_X_last_read_at
    """
    __tablename__ = 'conversations'
    __table_args__ = (
        UniqueConstraint('user_1_id', 'user_2_id', name='uq_conversation_users'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_1_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    user_2_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Per-user read timestamps (single source of truth for read state)
    # NULL means user has never opened the conversation
    user_1_last_read_at = Column(DateTime, nullable=True)
    user_2_last_read_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=get_current_utc_time)
    updated_at = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    # Relationships
    messages = relationship('Message', back_populates='conversation', cascade='all, delete-orphan')
    user_1 = relationship('User', foreign_keys=[user_1_id])
    user_2 = relationship('User', foreign_keys=[user_2_id])


class Message(UserBase):
    """
    Individual message in a DM conversation.

    Read state is NOT stored here - it's derived from Conversation.user_X_last_read_at.
    A message is "read" by a user if message.created_at <= conversation.user_X_last_read_at.
    """
    __tablename__ = 'messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default='text')  # text, image, file
    created_at = Column(DateTime, default=get_current_utc_time, index=True)

    # Relationships
    conversation = relationship('Conversation', back_populates='messages')
    sender = relationship('User')
