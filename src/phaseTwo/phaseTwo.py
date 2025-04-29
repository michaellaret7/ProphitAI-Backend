import os
import json
import pandas as pd
import numpy as np
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import concurrent.futures
import functools
import time

# Import from utils package
from src.utils.caching import cache_result
from src.utils.file_utils import load_schema_data
from src.utils.database import get_default_db_config

# Import from our modules
from src.phaseTwo.data_retrieval import get_daily_closing_prices, get_fundamentals_data, get_stock_tickers
from src.phaseTwo.financial_metrics import calculate_stock_metrics, debug_json_encoding, generate_fundamental_analysis_report
from src.phaseTwo.sentiment_analysis import get_news_sentiment, batch_analyze_news_sentiment
from src.phaseTwo.stock_selection import select_top_performing_stocks, analyze_tickers_and_generate_recommendations
from src.phaseTwo.portfolio_analysis import analyze_portfolio

# Load environment variables from .env file
load_dotenv()

# Sample portfolio data for testing when this module is run directly
portfolio_data = {
    "portfolio": [
        {
            "asset_class": "semiconductors",
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

