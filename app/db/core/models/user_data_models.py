# database/models/user_models.py
"""
Complete User Data Models for all tables in the user_data database
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.db.core.db_config import UserBase

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
    creation_date = Column(DateTime, default=datetime.utcnow)
    
    # Direct company association
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True, index=True)
    role = Column(String, default='member')
    
    # Relationships
    company = relationship('Company', back_populates='users')
    # subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')

class Company(UserBase):
    __tablename__ = 'companies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow)
    seats = Column(Integer)
    
    # Relationships
    users = relationship('User', back_populates='company')
    # subscriptions = relationship('Subscription', back_populates='company', cascade='all, delete-orphan')

class Portfolio(UserBase):
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=False)
    
    # Additional fields
    sector = Column(String, index=True)
    industry = Column(String, index=True)
    sub_industry = Column(String)
    allocation = Column(Float)
    is_current = Column(Boolean, default=True, index=True)
    
    # New fields for recommendations
    supporting_metrics = Column(JSONB, nullable=True)
    reason_for_rec = Column(Text, nullable=True)
    
    # Additional tracking fields that might be useful
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # If portfolios belong to a company or user, you might want to add:
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Relationships
    company = relationship('Company', backref='portfolios')
    user = relationship('User', backref='portfolios')


