import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "45",
            "net_worth": "$750,000",
            "investment size(as a percentage of net worth)": "25%",
            "risk_tolerance": "Low to Moderate",
            "investment_goals": "Capital preservation and steady income",
            "time_horizon": "10 Years",
            "Overall Description": """
            I am looking for a relatively conservative investment strategy. My primary goal is to preserve my capital while generating a steady stream of income.
            I'm interested in high-quality bonds, dividend-paying blue-chip stocks, and real estate investment trusts (REITs).
            I plan to retire in 20 years and want a portfolio that provides stability and reliable returns.
            """
        }
    }

    return user_data