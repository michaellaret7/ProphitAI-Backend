import os
import json
import pandas as pd
import numpy as np
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from src.phaseTwo.portfolio_analysis import extract_asset_classes
from src.phaseTwo.data_retrieval import get_stock_tickers
from src.phaseTwo.stock_selection import _calculate_and_filter_metrics, _calculate_composite_scores, _generate_llm_prompt_content
from src.phaseTwo.financial_metrics import generate_fundamental_analysis_report
# Load environment variables from .env file
load_dotenv()

# Sample portfolio data for testing when this module is run directly
portfolio_data = {
    "portfolio": [
        {
            "asset_class": "coal_and_consumable_fuels",
            "allocation": 20,
            "reason": "Growth potential driven by AI demand and renewable energy applications. Allocation increased to balance total portfolio."
        },
        {
            "asset_class": "investment_grade_corporate_bond_etfs",
            "allocation": 20,
            "reason": "Attractive yields and stable income from sectors like Financials and Energy."
        },
        {
            "asset_class": "data_center_reits",
            "allocation": 10,
            "reason": "Growth driven by increasing demand for data storage and digital services."
        },
        {
            "asset_class": "broad_based_emerging_market_equity_etfs",
            "allocation": 15,
            "reason": "Diversification and growth opportunities in emerging markets with hedging strategies."
        },
        {
            "asset_class": "industrial_metals",
            "allocation": 10,
            "reason": "Essential for renewable energy technologies and benefiting from geopolitical trends."
        },
        {
            "asset_class": "cash",
            "allocation": 5,
            "reason": "Provides liquidity and flexibility for tactical opportunities and risk management."
        }
    ]
}

if __name__ == "__main__":
    dict = extract_asset_classes(portfolio_data)
    first_key = next(iter(dict))

    tickers = get_stock_tickers(first_key)
    tickers = tickers[first_key]

    df = _calculate_and_filter_metrics(tickers)
    new_df = _calculate_composite_scores(df)
    new_df = new_df[:5]

    # Filter the original df to include only the top 5 tickers
    top_tickers = new_df['Ticker'].tolist()
    df_top_5 = df[df['Ticker'].isin(top_tickers)]
    print(df_top_5)

    # Create the final dictionary
    final_stock_data = {}

    for index, row in df_top_5.iterrows():
        ticker = row['Ticker']
        # Convert row to dictionary, excluding the Ticker itself
        stock_metrics = row.drop('Ticker').to_dict()
        
        # Generate fundamental analysis report
        fundamental_report = generate_fundamental_analysis_report(ticker)
        
        # Combine metrics and report
        stock_metrics['fundamental_report'] = fundamental_report
        
        # Add to the main dictionary
        final_stock_data[ticker] = stock_metrics

    print(final_stock_data) 


