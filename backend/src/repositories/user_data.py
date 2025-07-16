from backend.src.db.core.user_data_models import *
from backend.src.db.core.db_config import UserSession
from sqlalchemy.orm import joinedload
from typing import Optional, Union, Dict, Any

def get_all_user_data(email: Optional[str] = None, user_id: Optional[str] = None, workos_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get complete user data by email, user_id, or workos_id
    
    Args:
        email: User's email address
        user_id: User's UUID
        workos_id: User's WorkOS ID
        
    Returns:
        Dictionary containing complete user data with companies and portfolios, or None if not found
    """
    if not any([email, user_id, workos_id]):
        raise ValueError("At least one identifier (email, user_id, or workos_id) must be provided")
    
    with UserSession() as session:
        # Build query with eager loading of related data
        query = session.query(User).options(
            joinedload(User.company_associations).joinedload(CompanyUser.company),
            joinedload(User.portfolios)
        )
        
        # Apply filters based on provided identifiers
        if email:
            query = query.filter(User.email == email)
        elif user_id:
            query = query.filter(User.id == user_id)
        elif workos_id:
            query = query.filter(User.workos_id == workos_id)
        
        user = query.first()
        
        if not user:
            return None
        
        # Format user data
        user_data = {
            'id': str(user.id),
            'workos_id': user.workos_id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
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
        
        # Add portfolio information
        for portfolio in user.portfolios:
            user_data['portfolios'].append({
                'id': portfolio.id,
                'portfolio_id': str(portfolio.portfolio_id),
                'name': portfolio.name,
                'ticker': portfolio.ticker,
                'sector': portfolio.sector,
                'industry': portfolio.industry,
                'sub_industry': portfolio.sub_industry,
                'allocation': portfolio.allocation,
                'is_current': portfolio.is_current,
                'supporting_metrics': portfolio.supporting_metrics,
                'reason_for_rec': portfolio.reason_for_rec,
                'created_date': portfolio.created_date.isoformat() if portfolio.created_date else None,
                'updated_date': portfolio.updated_date.isoformat() if portfolio.updated_date else None
            })
        
        return user_data

def get_user_basic_info(email: Optional[str] = None, user_id: Optional[str] = None, workos_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get basic user info (id, workos_id, email, first_name, last_name) by email, user_id, or workos_id
    
    Args:
        email: User's email address
        user_id: User's UUID
        workos_id: User's WorkOS ID
        
    Returns:
        Dictionary containing only basic user info, or None if not found
    """
    if not any([email, user_id, workos_id]):
        raise ValueError("At least one identifier (email, user_id, or workos_id) must be provided")
    
    with UserSession() as session:
        query = session.query(User)
        
        # Apply filters based on provided identifiers
        if email:
            query = query.filter(User.email == email)
        elif user_id:
            query = query.filter(User.id == user_id)
        elif workos_id:
            query = query.filter(User.workos_id == workos_id)
        
        user = query.first()
        
        if not user:
            return None
        
        return {
            'id': str(user.id),
            'workos_id': user.workos_id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

def add_user(email:str, first_name:str, last_name:str):
    session = UserSession()

    workos_id = "" # TODO: get workos_id from workos

    user = session.query(User).filter(User.email == email).first()
    if user:
        return user, 'User already exists'
    
    user = User(
        id = uuid.uuid4(),
        workos_id=workos_id,
        email=email,
        first_name=first_name,
        last_name=last_name
    )

    session.add(user)
    session.commit()
    session.close()

def add_company_user(email:str, company_name:str, role:str):
    session = UserSession()

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
    session.commit()
    session.close()

def add_company(company_name:str, seats:int):
    session = UserSession()
    company = Company(
        id = uuid.uuid4(),
        name=company_name,
        creation_date=datetime.now(),
        seats=seats
    )
    session.add(company)
    session.commit()
    session.close()


