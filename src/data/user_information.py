import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    json = {
        "user_information": {
            "age": "35",
            "net_worth": "1,292,902",
            "risk_tolerance": "Medium Risk Tolerance",
            "investment_goals": "Medium term high growth, some income",
            "time_horizon": "5 Years",
            "Overall Description": "The user is a 35 year old who wants to maximize returns in the medium term, while still having some income. They are comfortable with moderate risk."
        }
    }
    
    return json