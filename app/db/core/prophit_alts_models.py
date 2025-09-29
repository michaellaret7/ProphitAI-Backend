# database/models/prophit_alts_models.py
"""
ProphitAlts Data Models for all tables in the prophit_alts database
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Numeric, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.core.db_config import ProphitAltsBase
from datetime import datetime
import uuid
import enum

# =============================================================================
# ENUMS
# =============================================================================

class PositionType(enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class TradeAction(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    REBALANCE = "REBALANCE"
    
# =============================================================================
# FUND MANAGEMENT SCHEMA
# =============================================================================

class Fund(ProphitAltsBase):
    __tablename__ = 'funds'
    __table_args__ = {'schema': 'prophit_alts_funds'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_name = Column(String, nullable=False, unique=True)
    strategy = Column(String, nullable=False)
    unrealized_pnl = Column(Numeric(15, 2), nullable=True)
    alpha = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)
    net_exposure = Column(Numeric(5, 2), nullable=True)
    
    # Relationships
    trades = relationship('FundTrade', back_populates='fund', lazy='dynamic', cascade='all, delete-orphan')
    initial_positions = relationship('FundInitialPosition', back_populates='fund', lazy='dynamic', cascade='all, delete-orphan')
    final_positions = relationship('FundFinalPosition', back_populates='fund', lazy='dynamic', cascade='all, delete-orphan')

class FundTrade(ProphitAltsBase):
    __tablename__ = 'trades'
    __table_args__ = {'schema': 'prophit_alts_funds'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey('prophit_alts_funds.funds.id'), nullable=False, index=True)
    ticker_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String, nullable=False)  # BUY, SELL, etc.
    dollar_amount = Column(Numeric(15, 2), nullable=False)
    datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    industry = Column(String, nullable=False)
    reasoning = Column(String, nullable=True)
    
    # Relationships
    fund = relationship('Fund', back_populates='trades')
    # Note: ticker relationship would be cross-database, handled at application level

class FundInitialPosition(ProphitAltsBase):
    __tablename__ = 'initial_positions'
    __table_args__ = {'schema': 'prophit_alts_funds'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey('prophit_alts_funds.funds.id'), nullable=False, index=True)
    fund_name = Column(String, nullable=False)  # Denormalized for convenience
    ticker_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ticker_name = Column(String, nullable=False)
    position = Column(Enum(PositionType), nullable=False)
    industry = Column(String, nullable=False)
    conviction = Column(Float, nullable=False)
    reasoning = Column(String, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    fund = relationship('Fund', back_populates='initial_positions')
    # Note: ticker relationship would be cross-database, handled at application level

class FundFinalPosition(ProphitAltsBase):
    __tablename__ = 'final_positions'
    __table_args__ = (
        UniqueConstraint('fund_id', 'ticker_id', name='unique_fund_ticker'),
        {'schema': 'prophit_alts_funds'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey('prophit_alts_funds.funds.id'), nullable=False, index=True)
    fund_name = Column(String, nullable=False)  # Denormalized for convenience
    ticker_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ticker_name = Column(String, nullable=False)
    position = Column(Enum(PositionType), nullable=False)
    industry = Column(String, nullable=False)
    portfolio_allocation = Column(Float, nullable=False)  # Percentage of total portfolio
    reasoning = Column(String, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    fund = relationship('Fund', back_populates='final_positions')


 