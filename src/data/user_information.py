import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "28",
            "net_worth": "$2,500,000",
            "risk_tolerance": "High Risk Tolerance",
            "investment_goals": "High growth, low income, around 10-15% volatility",
            "time_horizon": "2 Years",
            "Overall Description": """
            The user is a 28-year-old nearing retirement and focused on high growth, low income, and around 10-15% volatility.
            He is particularly bullish on the tech and semiconductor sectors.
            """
        }
    }
    
    return user_data