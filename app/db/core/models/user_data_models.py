# database/models/user_models.py
"""
Complete User Data Models for all tables in the user_data database
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
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

    # Relationships
    user = relationship('User', backref='portfolios')
    items = relationship('PortfolioItem', back_populates='portfolio', cascade='all, delete-orphan')

class PortfolioItem(UserBase):
    __tablename__ = 'portfolio_items'

    portfolio_id = Column(UUID(as_uuid=True), ForeignKey('portfolios.id', ondelete='CASCADE'), primary_key=True)
    ticker = Column(String, primary_key=True)
    allocation = Column(Float)  # Decimal format: 0.25 = 25%, range 0-1
    num_shares = Column(Float, nullable=True)
    supporting_metrics = Column(JSONB, nullable=True)
    reason_for_rec = Column(Text, nullable=True)
    created_date = Column(DateTime, default=get_current_utc_time)
    updated_date = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    # Relationships
    portfolio = relationship('Portfolio', back_populates='items')

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
