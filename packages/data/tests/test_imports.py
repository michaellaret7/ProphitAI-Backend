"""Migration verification — every module in prophitai-data must import cleanly."""
import os
import pathlib
import importlib

import pytest


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "prophitai_data"


class TestFoundationImports:
    """Verify all foundation layer modules import cleanly."""

    def test_db_config(self):
        from prophitai_data.db import config  # noqa: F401

    def test_db_utils(self):
        from prophitai_data.db import utils  # noqa: F401

    def test_db_models_market(self):
        from prophitai_data.db.models import market  # noqa: F401

    def test_db_models_user(self):
        from prophitai_data.db.models import user  # noqa: F401

    def test_db_models_alts(self):
        from prophitai_data.db.models import alts  # noqa: F401

    def test_db_models_macro(self):
        from prophitai_data.db.models import macro  # noqa: F401

    def test_session_decorators(self):
        from prophitai_data.session import decorators  # noqa: F401

    def test_session_reexports(self):
        from prophitai_data.session import with_session, with_transaction, with_sessions  # noqa: F401

    def test_encryption(self):
        from prophitai_data.internal import encryption  # noqa: F401

    def test_cache(self):
        from prophitai_data.cache import data_cache  # noqa: F401

    def test_cache_reexports(self):
        from prophitai_data.cache import get_cache, DataCache  # noqa: F401


class TestClientImports:
    """Verify all client modules import cleanly."""

    def test_fmp_client(self):
        from prophitai_data.clients import fmp  # noqa: F401

    def test_options_client(self):
        from prophitai_data.clients.options import client  # noqa: F401

    def test_options_service(self):
        from prophitai_data.clients.options import service  # noqa: F401

    def test_options_repository(self):
        from prophitai_data.clients.options import repository  # noqa: F401

    def test_snaptrade_client(self):
        from prophitai_data.clients.snaptrade import client  # noqa: F401

    def test_snaptrade_broker(self):
        from prophitai_data.clients.snaptrade import broker  # noqa: F401

    def test_snaptrade_credentials(self):
        from prophitai_data.clients.snaptrade import credentials  # noqa: F401

    def test_snaptrade_auth(self):
        from prophitai_data.clients.snaptrade import auth  # noqa: F401

    def test_snaptrade_accounts(self):
        from prophitai_data.clients.snaptrade import accounts  # noqa: F401

    def test_snaptrade_trading(self):
        from prophitai_data.clients.snaptrade import trading  # noqa: F401

    def test_snaptrade_connections(self):
        from prophitai_data.clients.snaptrade import connections  # noqa: F401


class TestRepositoryImports:
    """Verify all repository modules import cleanly."""

    def test_price(self):
        from prophitai_data.repositories import price  # noqa: F401

    def test_ticker(self):
        from prophitai_data.repositories import ticker  # noqa: F401

    def test_news(self):
        from prophitai_data.repositories import news  # noqa: F401

    def test_transcripts(self):
        from prophitai_data.repositories import transcripts  # noqa: F401

    def test_ratings(self):
        from prophitai_data.repositories import ratings  # noqa: F401

    def test_etf(self):
        from prophitai_data.repositories import etf  # noqa: F401

    def test_screener(self):
        from prophitai_data.repositories import screener  # noqa: F401

    def test_fundamentals_models(self):
        from prophitai_data.repositories.fundamentals import models  # noqa: F401

    def test_fundamentals_fetchers(self):
        from prophitai_data.repositories.fundamentals import fetchers  # noqa: F401

    def test_fundamentals_statements(self):
        from prophitai_data.repositories.fundamentals import statements  # noqa: F401

    def test_macro_indicators(self):
        from prophitai_data.repositories.macro import indicators  # noqa: F401

    def test_macro_calendar(self):
        from prophitai_data.repositories.macro import calendar  # noqa: F401

    def test_macro_commodities(self):
        from prophitai_data.repositories.macro import commodities  # noqa: F401

    def test_macro_rates(self):
        from prophitai_data.repositories.macro import rates  # noqa: F401

    def test_user_account(self):
        from prophitai_data.repositories.user import account  # noqa: F401

    def test_user_watchlist(self):
        from prophitai_data.repositories.user import watchlist  # noqa: F401

    def test_user_trade_proposal(self):
        from prophitai_data.repositories.user import trade_proposal  # noqa: F401

    def test_portfolio_crud(self):
        from prophitai_data.repositories.portfolio import crud  # noqa: F401

    def test_portfolio_retrieval(self):
        from prophitai_data.repositories.portfolio import retrieval  # noqa: F401

    def test_portfolio_preferences(self):
        from prophitai_data.repositories.portfolio import preferences  # noqa: F401

    def test_portfolio_alerts(self):
        from prophitai_data.repositories.portfolio import alerts  # noqa: F401

    def test_messaging_conversations(self):
        from prophitai_data.repositories.messaging import conversations  # noqa: F401

    def test_messaging_messages(self):
        from prophitai_data.repositories.messaging import messages  # noqa: F401

    def test_messaging_read_state(self):
        from prophitai_data.repositories.messaging import read_state  # noqa: F401


class TestJobImports:
    """Verify all job modules import cleanly."""

    def test_base_updater(self):
        from prophitai_data.jobs import base  # noqa: F401

    def test_market_ticker(self):
        from prophitai_data.jobs.market import ticker  # noqa: F401

    def test_market_price(self):
        from prophitai_data.jobs.market import price  # noqa: F401

    def test_fundamentals_orchestrator(self):
        from prophitai_data.jobs.fundamentals import orchestrator  # noqa: F401

    def test_fundamentals_financial_statements(self):
        from prophitai_data.jobs.fundamentals import financial_statements  # noqa: F401

    def test_fundamentals_analyst_data(self):
        from prophitai_data.jobs.fundamentals import analyst_data  # noqa: F401

    def test_fundamentals_etf_data(self):
        from prophitai_data.jobs.fundamentals import etf_data  # noqa: F401

    def test_fundamentals_news_data(self):
        from prophitai_data.jobs.fundamentals import news_data  # noqa: F401

    def test_portfolio_update(self):
        from prophitai_data.jobs.portfolio import update  # noqa: F401

    def test_portfolio_monitor(self):
        from prophitai_data.jobs.portfolio import monitor  # noqa: F401

    def test_portfolio_detections(self):
        from prophitai_data.jobs.portfolio import detections  # noqa: F401

    def test_portfolio_models(self):
        from prophitai_data.jobs.portfolio import models  # noqa: F401

    def test_portfolio_utils(self):
        from prophitai_data.jobs.portfolio import utils  # noqa: F401

    def test_portfolio_messages(self):
        from prophitai_data.jobs.portfolio import messages  # noqa: F401

    def test_portfolio_batch_monitor(self):
        from prophitai_data.jobs.portfolio import batch_monitor  # noqa: F401


class TestNoOldImports:
    """Verify no source file contains stale 'from app.' imports."""

    def test_no_app_imports_in_source(self):
        """Scan all .py files for 'from app.' — migration must have rewritten all."""
        violations = []
        for py_file in PACKAGE_ROOT.rglob("*.py"):
            content = py_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("from app.") or stripped.startswith("import app."):
                    violations.append(f"{py_file.relative_to(PACKAGE_ROOT)}:{i}: {stripped}")
        assert violations == [], f"Found stale app.* imports:\n" + "\n".join(violations)

    def test_no_calc_imports_in_source(self):
        """Verify data package has zero calculation imports (dependency boundary)."""
        violations = []
        for py_file in PACKAGE_ROOT.rglob("*.py"):
            content = py_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Reason: skip string literals (error messages mention calc)
                if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                    continue
                if "prophitai_calc" in stripped and ("from" in stripped or "import" in stripped):
                    violations.append(f"{py_file.relative_to(PACKAGE_ROOT)}:{i}: {stripped}")
        assert violations == [], f"Found calc imports in data package:\n" + "\n".join(violations)
