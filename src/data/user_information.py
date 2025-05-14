import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "45",
            "net_worth": "$624,023",
            "risk_tolerance": "Medium Risk Tolerance",
            "investment_goals": "Medium term high growth, some income",
            "time_horizon": "3 Years",
            "Overall Description": """
            The user is a 45 year old who wants to maximize returns in the medium term, while still having some income. 
            They are comfortable with moderate risk. The use emphasized heavy emphasis on low volatility and income as the priority.
            """
        }
    }
    
    return user_data