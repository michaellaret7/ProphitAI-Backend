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
    workos_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, nullable=False, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    
    # Relationships
    company_associations = relationship('CompanyUser', back_populates='user', cascade='all, delete-orphan')
    companies = relationship('Company', secondary='company_users', viewonly=True)
    # subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')

class Company(UserBase):
    __tablename__ = 'companies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow)
    seats = Column(Integer)
    
    # Relationships
    user_associations = relationship('CompanyUser', back_populates='company', cascade='all, delete-orphan')
    users = relationship('User', secondary='company_users', viewonly=True)
    # subscriptions = relationship('Subscription', back_populates='company', cascade='all, delete-orphan')

class CompanyUser(UserBase):
    __tablename__ = 'company_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Additional fields that might be useful
    role = Column(String, default='member')  # admin, member, viewer, etc.
    joined_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='company_associations')
    company = relationship('Company', back_populates='user_associations')
    
    # Unique constraint to prevent duplicate user-company associations
    __table_args__ = (
        {'extend_existing': True}  # This allows updating the table definition
    )

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


