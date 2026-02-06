"""Company repository functions for company management and user-company assignments."""

from app.db.core.models.user_data_models import *
from typing import Optional
from app.utils.decorators.database import with_transaction
from app.utils.time_utils import get_current_utc_time
import uuid


@with_transaction('user')
def assign_all_users_to_company_by_name(company_name: str, session=None) -> int:
    """
    Set company_id for all users to the ID of the company with the given name.
    Returns the number of rows updated.
    """
    company = session.query(Company).filter(Company.name == company_name).first()
    if not company:
        raise ValueError("Company not found")
    updated = session.query(User).update({User.company_id: company.id}, synchronize_session=False)
    return updated

@with_transaction('user')
def assign_all_users_to_prophitai(session=None) -> int:
    return assign_all_users_to_company_by_name('ProphitAI', session=session)

@with_transaction('user')
def set_all_users_to_admin(session=None) -> int:
    """
    Set role='admin' for all users. Returns number of rows updated.
    """
    updated = session.query(User).update({User.role: 'admin'}, synchronize_session=False)
    return updated

@with_transaction('user')
def assign_user_to_company_by_id(email: str, company_id: str, role: Optional[str] = None, session=None) -> bool:
    """Assign a user to a company by company ID."""
    user = session.query(User).filter(User.email == email).first()
    if not user:
        return False
    company = session.query(Company).filter(Company.id == company_id).first()
    if not company:
        return False
    user.company_id = company.id
    if role is not None:
        user.role = role
    return True

@with_transaction('user')
def add_company(company_name:str, seats:int, session=None):
    company = Company(
        id = uuid.uuid4(),
        name=company_name,
        creation_date=get_current_utc_time(),
        seats=seats
    )
    session.add(company)
    # commit handled by decorator
