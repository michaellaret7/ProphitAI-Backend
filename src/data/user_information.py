import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "25",
            "net_worth": "$124,023",
            "risk_tolerance": "High Risk Tolerance",
            "investment_goals": "Short term high growth, little to no income",
            "time_horizon": "1 year",
            "Overall Description": "The user is a very young investor who has a very high risk tolerance and wants to mazimize returns. He wants to target high growth stocks and ETFs. High volatility is allowed."
        }
    }
    
    return user_data