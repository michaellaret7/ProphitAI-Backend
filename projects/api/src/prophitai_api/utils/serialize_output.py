from prophitai_data.db.config import UserSession
from prophitai_data.db.models.user import *

def serialize_sqlalchemy_obj(obj):
        """Convert SQLAlchemy object to dictionary"""
        if obj is None:
            return None

        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            # Convert datetime/date objects to strings
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            # Convert Decimal to float
            elif hasattr(value, 'is_finite'):
                value = float(value)
            # Convert UUID to string
            elif hasattr(value, 'hex'):  # UUID objects have a hex attribute
                value = str(value)
            result[column.name] = value
        return result