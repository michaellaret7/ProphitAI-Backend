import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "48",
            "net_worth": "$75,000,000",
            "investment size(as a percentage of net worth)": "65%",
            "risk_tolerance": "Very High",
            "investment_goals": "High growth with some income",
            "time_horizon": "5 Years",
            "Overall Description": """
            I want a very technology/AI/growth focused portfolio. I am very wealthy and have a high risk tolerance. Find undervalued high growth potential 
            assets and invest heavily in them.
            """
        }
    }

    return user_data