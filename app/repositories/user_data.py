from app.db.core.user_data_models import *
from app.db.core.db_config import UserSession
from sqlalchemy.orm import joinedload, selectinload
from typing import Optional, Union, Dict, Any
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.decorators.database import with_session, with_transaction
from datetime import datetime
import uuid

@with_session('user')
def get_all_user_data(email: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get complete user data by email
    
    Args:
        email: User's email address
        
    Returns:
        Dictionary containing complete user data with companies and portfolios, or None if not found
    """
    if not email:
        raise ValueError("Email must be provided")
    
    # Build query with eager loading of related data
    # Using selectinload for portfolios to avoid duplicates
    query = session.query(User).options(
        joinedload(User.company_associations).joinedload(CompanyUser.company),
        selectinload(User.portfolios)
    )
    
    # Apply filter by email
    query = query.filter(User.email == email)
    
    user = query.first()
    
    if not user:
        return None
    
    # Format user data
    user_data = {
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'creation_date': user.creation_date.isoformat() if getattr(user, 'creation_date', None) else None,
        'companies': [],
        'portfolios': []
    }
    
    # Add company information
    for company_user in user.company_associations:
        company = company_user.company
        user_data['companies'].append({
            'id': str(company.id),
            'name': company.name,
            'creation_date': company.creation_date.isoformat() if company.creation_date else None,
            'seats': company.seats,
            'user_role': company_user.role,
            'joined_date': company_user.joined_date.isoformat() if company_user.joined_date else None
        })
    
    # Add portfolio information - deduplicate by portfolio_id
    seen_portfolio_ids = set()
    for portfolio in user.portfolios:
        portfolio_id = str(portfolio.portfolio_id)
        if portfolio_id not in seen_portfolio_ids:
            seen_portfolio_ids.add(portfolio_id)
            user_data['portfolios'].append({
                'name': portfolio.name,
                'portfolio_id': portfolio_id,
                'is_current': portfolio.is_current
            })
    
    return user_data

@with_session('user')
def get_user_basic_info(email: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get basic user info (id, email, first_name, last_name) by email
    
    Args:
        email: User's email address
        
    Returns:
        Dictionary containing only basic user info, or None if not found
    """
    if not email:
        raise ValueError("Email must be provided")
    
    query = session.query(User).filter(User.email == email)
    user = query.first()
    
    if not user:
        return None
    
    return {
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name
    }

@with_transaction('user')
def add_user(email: str, first_name: str, last_name: str, clerk_id: Optional[str] = None, session=None):
    user = session.query(User).filter(User.email == email).first()
    if user:
        # Return the existing user object for caller handling
        return user
    
    user = User(
        id = uuid.uuid4(),
        clerk_id=clerk_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        creation_date=datetime.now()
    )

    session.add(user)
    return user

@with_transaction('user')
def update_user_clerk_id(email: str, clerk_id: str, session=None) -> None:
    user = session.query(User).filter(User.email == email).first()
    if user and user.clerk_id != clerk_id:
        user.clerk_id = clerk_id

@with_transaction('user')
def update_user_fields(
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    clerk_id: Optional[str] = None,
    session=None
) -> bool:
    if not email:
        raise ValueError("Email must be provided")

    user = session.query(User).filter(User.email == email).first()
    if not user:
        return False

    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if clerk_id is not None:
        user.clerk_id = clerk_id

    # commit handled by decorator
    return True

@with_transaction('user')
def add_company_user(email:str, company_name:str, role:str, session=None):

    user = session.query(User).filter(User.email == email).first()
    company = session.query(Company).filter(Company.name == company_name).first()

    if not user:
        return 'User not found'
    if not company:
        return 'Company not found'

    company_user = CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        joined_date=datetime.now()
    )

    session.add(company_user)
    # commit handled by decorator

@with_transaction('user')
def add_company(company_name:str, seats:int, session=None):
    company = Company(
        id = uuid.uuid4(),
        name=company_name,
        creation_date=datetime.now(),
        seats=seats
    )
    session.add(company)
    # commit handled by decorator

@with_session('user')
def get_user_current_portfolio(email: str, session=None):
    if not email:
        raise ValueError("Email must be provided")
    
    user = session.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    user_id = user.id

    portfolio = session.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.is_current == True).all()
    portfolio = [serialize_sqlalchemy_obj(p) for p in portfolio]
    
    return portfolio

