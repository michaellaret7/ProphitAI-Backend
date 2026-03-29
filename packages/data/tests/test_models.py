"""
Tests for SQLAlchemy model registration and table metadata.

Verifies that all models register with their correct Base class and have
the expected table names and schema assignments.
"""

import pytest


class TestMarketModels:
    """Verify market models register with MarketBase and have correct table metadata."""

    def test_ticker_tablename(self):
        from prophitai_data.db.models.market import Ticker
        assert Ticker.__tablename__ == 'tickers'

    def test_ticker_schema(self):
        from prophitai_data.db.models.market import Ticker
        assert Ticker.__table_args__['schema'] == 'ticker_universe'

    def test_price_tablename(self):
        from prophitai_data.db.models.market import Price
        assert Price.__tablename__ == 'prices'

    def test_price_schema(self):
        from prophitai_data.db.models.market import Price
        assert Price.__table_args__['schema'] == 'price_data'

    def test_daily_prices_tablename(self):
        from prophitai_data.db.models.market import DailyPrices
        assert DailyPrices.__tablename__ == 'daily_prices'

    def test_daily_prices_schema(self):
        from prophitai_data.db.models.market import DailyPrices
        assert DailyPrices.__table_args__['schema'] == 'price_data'

    def test_balance_sheet_schema(self):
        from prophitai_data.db.models.market import BalanceSheet
        assert BalanceSheet.__table_args__['schema'] == 'fundamental_data'

    def test_cash_flow_statement_schema(self):
        from prophitai_data.db.models.market import CashFlowStatement
        assert CashFlowStatement.__table_args__['schema'] == 'fundamental_data'

    def test_income_statement_schema(self):
        from prophitai_data.db.models.market import IncomeStatement
        assert IncomeStatement.__table_args__['schema'] == 'fundamental_data'

    def test_equity_screener_tablename(self):
        from prophitai_data.db.models.market import EquityScreener
        assert EquityScreener.__tablename__ == 'equity_screener'

    def test_equity_screener_schema(self):
        from prophitai_data.db.models.market import EquityScreener
        assert EquityScreener.__table_args__['schema'] == 'screener_data'

    def test_etf_screener_schema(self):
        from prophitai_data.db.models.market import ETFScreener
        assert ETFScreener.__table_args__['schema'] == 'screener_data'

    def test_press_release_tablename(self):
        from prophitai_data.db.models.market import PressRelease
        assert PressRelease.__tablename__ == 'press_releases'

    def test_press_release_schema(self):
        from prophitai_data.db.models.market import PressRelease
        assert PressRelease.__table_args__['schema'] == 'news_data'

    def test_stock_news_schema(self):
        from prophitai_data.db.models.market import StockNews
        assert StockNews.__table_args__['schema'] == 'news_data'

    def test_stock_grades_individual_schema(self):
        from prophitai_data.db.models.market import StockGradesIndividual
        assert StockGradesIndividual.__table_args__['schema'] == 'grades_and_ratings_data'

    def test_stock_grades_summary_schema(self):
        from prophitai_data.db.models.market import StockGradesSummary
        assert StockGradesSummary.__table_args__['schema'] == 'grades_and_ratings_data'

    def test_rating_scores_schema(self):
        from prophitai_data.db.models.market import Rating
        assert Rating.__table_args__['schema'] == 'grades_and_ratings_data'

    def test_analyst_recommendation_schema(self):
        from prophitai_data.db.models.market import AnalystRecommendation
        assert AnalystRecommendation.__table_args__['schema'] == 'grades_and_ratings_data'

    def test_all_market_tables_in_metadata(self):
        """Verify MarketBase.metadata contains all expected tables."""
        from prophitai_data.db.config import MarketBase
        from prophitai_data.db.models import market  # noqa: F401

        table_names = [t.name for t in MarketBase.metadata.sorted_tables]
        assert 'tickers' in table_names
        assert 'prices' in table_names
        assert 'daily_prices' in table_names
        assert 'equity_screener' in table_names
        assert 'balance_sheets' in table_names
        assert 'press_releases' in table_names
        assert 'stock_grades_individual' in table_names
        assert 'rating_scores' in table_names


class TestUserModels:
    """Verify user models register with UserBase."""

    def test_user_tablename(self):
        from prophitai_data.db.models.user import User
        assert User.__tablename__ == 'users'

    def test_portfolio_tablename(self):
        from prophitai_data.db.models.user import Portfolio
        assert Portfolio.__tablename__ == 'portfolios'

    def test_portfolio_item_tablename(self):
        from prophitai_data.db.models.user import PortfolioItem
        assert PortfolioItem.__tablename__ == 'portfolio_items'

    def test_portfolio_preference_tablename(self):
        from prophitai_data.db.models.user import PortfolioPreference
        assert PortfolioPreference.__tablename__ == 'portfolio_preferences'

    def test_watchlist_tablename(self):
        from prophitai_data.db.models.user import Watchlist
        assert Watchlist.__tablename__ == 'watchlists'

    def test_watchlist_item_tablename(self):
        from prophitai_data.db.models.user import WatchlistItem
        assert WatchlistItem.__tablename__ == 'watchlist_items'

    def test_conversation_tablename(self):
        from prophitai_data.db.models.user import Conversation
        assert Conversation.__tablename__ == 'conversations'

    def test_message_tablename(self):
        from prophitai_data.db.models.user import Message
        assert Message.__tablename__ == 'messages'

    def test_trade_proposal_tablename(self):
        from prophitai_data.db.models.user import TradeProposal
        assert TradeProposal.__tablename__ == 'trade_proposals'

    def test_all_user_tables_in_metadata(self):
        """Verify UserBase.metadata contains all expected tables."""
        from prophitai_data.db.config import UserBase
        from prophitai_data.db.models import user  # noqa: F401

        table_names = [t.name for t in UserBase.metadata.sorted_tables]
        assert 'users' in table_names
        assert 'portfolios' in table_names
        assert 'portfolio_items' in table_names
        assert 'watchlists' in table_names
        assert 'conversations' in table_names
        assert 'messages' in table_names
        assert 'trade_proposals' in table_names


class TestAltsModels:
    """Verify prophit_alts models register with ProphitAltsBase."""

    def test_fund_tablename(self):
        from prophitai_data.db.models.alts import Fund
        assert Fund.__tablename__ == 'funds'

    def test_fund_schema(self):
        from prophitai_data.db.models.alts import Fund
        assert Fund.__table_args__['schema'] == 'prophit_alts_funds'

    def test_fund_trade_tablename(self):
        from prophitai_data.db.models.alts import FundTrade
        assert FundTrade.__tablename__ == 'trades'

    def test_fund_trade_schema(self):
        from prophitai_data.db.models.alts import FundTrade
        assert FundTrade.__table_args__['schema'] == 'prophit_alts_funds'

    def test_fund_initial_position_tablename(self):
        from prophitai_data.db.models.alts import FundInitialPosition
        assert FundInitialPosition.__tablename__ == 'initial_positions'

    def test_fund_final_position_tablename(self):
        from prophitai_data.db.models.alts import FundFinalPosition
        assert FundFinalPosition.__tablename__ == 'final_positions'

    def test_all_alts_tables_in_metadata(self):
        """Verify ProphitAltsBase.metadata contains all expected tables."""
        from prophitai_data.db.config import ProphitAltsBase
        from prophitai_data.db.models import alts  # noqa: F401

        table_names = [t.name for t in ProphitAltsBase.metadata.sorted_tables]
        assert 'funds' in table_names
        assert 'trades' in table_names
        assert 'initial_positions' in table_names
        assert 'final_positions' in table_names


class TestMacroModels:
    """Verify macro models register with MacroDataBase."""

    def test_government_bond_rates_tablename(self):
        from prophitai_data.db.models.macro import GovernmentBondRates
        assert GovernmentBondRates.__tablename__ == 'gov_bond_rates'

    def test_commodity_prices_tablename(self):
        from prophitai_data.db.models.macro import CommodityPrices
        assert CommodityPrices.__tablename__ == 'commodity_prices'

    def test_economic_indicators_tablename(self):
        from prophitai_data.db.models.macro import EconomicIndicators
        assert EconomicIndicators.__tablename__ == 'economic_indicators'

    def test_economic_calendar_tablename(self):
        from prophitai_data.db.models.macro import EconomicCalendar
        assert EconomicCalendar.__tablename__ == 'economic_calendar'

    def test_all_macro_tables_in_metadata(self):
        """Verify MacroDataBase.metadata contains all expected tables."""
        from prophitai_data.db.config import MacroDataBase
        from prophitai_data.db.models import macro  # noqa: F401

        table_names = [t.name for t in MacroDataBase.metadata.sorted_tables]
        assert 'gov_bond_rates' in table_names
        assert 'commodity_prices' in table_names
        assert 'economic_indicators' in table_names
        assert 'economic_calendar' in table_names
