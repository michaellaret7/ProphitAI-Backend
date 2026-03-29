"""
Optimized ticker data loader for adding stock tickers to the database.
Loads comprehensive data including prices, fundamentals, news, grades, and ratings.
"""
from prophitai_data.repositories.price import get_price_data_15_mins
from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import (
    Ticker, Price, DailyPrices, Dividend,
    BalanceSheet, CashFlowStatement, IncomeStatement, FinancialRatio, AnalystEstimate,
    StockNews, PressRelease, PriceTargetNews, StockGradeNews,
    StockGradesIndividual, StockGradesSummary, Rating, AnalystRecommendation, PriceTargetSummary
)
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_data.db.utils import bulk_insert_with_copy
from prophitai_shared import get_current_utc_time

from datetime import datetime, timedelta, timezone
from sqlalchemy.dialects.postgresql import insert
import pandas as pd
import time
import uuid


class OptimizedTickerDataLoader:
    """
    Optimized stock ticker data loader with comprehensive data fetching.

    Loads:
    - Company profile (beta, IPO date, shares outstanding, etc.)
    - Quote data (price, market cap, EPS, P/E)
    - Intraday prices (15-min intervals, 2 years)
    - Daily prices (maximum history available)
    - Financial statements (balance sheets, income statements, cash flow)
    - Financial ratios
    - Analyst estimates
    - Dividends
    - News (stock news, press releases)
    - Grades and ratings
    - Price target data

    All timestamps are stored in UTC for consistency.
    """

    def __init__(self, ticker, sector=None, industry=None, sub_industry=None):
        self.ticker = ticker.upper()
        self.sector = sector
        self.industry = industry
        self.sub_industry = sub_industry
        self.fmp_api = FMP_API_DATA()
        self.ticker_id = None
        self.session = None

    # ================================
    # --> Helper funcs
    # ================================

    def _ensure_ticker_exists(self, allow_partial_reload=False):
        """
        Check if ticker exists in database.
        Returns True if ticker is new, False if it already exists.
        If allow_partial_reload is True, continues with existing ticker to complete missing data.
        """
        ticker_obj = self.session.query(Ticker).filter(Ticker.ticker == self.ticker).first()

        if ticker_obj:
            self.ticker_id = ticker_obj.id
            print(f"[{self.ticker}] Ticker already exists in database.")

            price_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
            daily_price_count = self.session.query(DailyPrices).filter(DailyPrices.ticker_id == self.ticker_id).count()
            balance_sheet_count = self.session.query(BalanceSheet).filter(BalanceSheet.ticker_id == self.ticker_id).count()

            print(f"[{self.ticker}] Existing data status:")
            print(f"  - Intraday price records: {price_count:,}")
            print(f"  - Daily price records: {daily_price_count:,}")
            print(f"  - Balance sheet records: {balance_sheet_count}")

            if allow_partial_reload:
                print(f"[{self.ticker}] Continuing to complete partial data...")
                return "partial"

            return False

        print(f"[{self.ticker}] Creating new ticker entry...")
        if self.sector or self.industry or self.sub_industry:
            print(f"[{self.ticker}] Classification - Sector: {self.sector or 'None'}, Industry: {self.industry or 'None'}, Sub-Industry: {self.sub_industry or 'None'}")

        ticker_obj = Ticker(
            id=uuid.uuid4(),
            ticker=self.ticker,
            is_etf=False,
            sector=self.sector,
            industry=self.industry,
            sub_industry=self.sub_industry
        )
        self.session.add(ticker_obj)
        self.session.flush()

        self.ticker_id = ticker_obj.id
        return True

    def _update_company_profile(self):
        """Update ticker table with company profile data (beta, IPO date, etc.)."""
        print(f"[{self.ticker}] Fetching company profile...")
        profile_data = self.fmp_api.get_company_profile(self.ticker)

        if profile_data and len(profile_data) > 0:
            profile = profile_data[0]

            ipo_date = None
            if profile.get('ipoDate'):
                try:
                    ipo_date = datetime.strptime(profile['ipoDate'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass

            earnings_announcement = None
            if profile.get('earningsAnnouncement'):
                try:
                    earnings_announcement = pd.to_datetime(profile['earningsAnnouncement'], utc=True)
                except (ValueError, TypeError):
                    pass

            update_data = {
                'ticker_name': profile.get('companyName'),
                'ticker_description': profile.get('description'),
                'beta': profile.get('beta'),
                'is_actively_trading': profile.get('isActivelyTrading'),
                'is_adr': profile.get('isAdr'),
                'is_fund': profile.get('isFund'),
                'ipo_date': ipo_date,
                'earnings_announcement': earnings_announcement,
                'last_updated': get_current_utc_time()
            }

            if profile.get('mktCap') and profile.get('price'):
                try:
                    shares_outstanding = int(profile['mktCap'] / profile['price'])
                    update_data['shares_outstanding'] = shares_outstanding
                except (TypeError, ZeroDivisionError):
                    pass

            update_data = {k: v for k, v in update_data.items() if v is not None}

            if update_data:
                self.session.query(Ticker).filter(Ticker.id == self.ticker_id).update(update_data)
                self.session.flush()
                print(f"[{self.ticker}] Updated company profile")
        else:
            print(f"[{self.ticker}] No company profile data found")

    def _update_ticker_quote_data(self):
        """Update ticker table with latest quote data."""
        print(f"[{self.ticker}] Fetching quote data...")
        quote_data = self.fmp_api.get_full_quote(self.ticker)

        if quote_data and len(quote_data) > 0:
            quote = quote_data[0]

            update_data = {
                'price': quote.get('price'),
                'market_cap': quote.get('marketCap'),
                'avg_volume': quote.get('avgVolume'),
                'eps': quote.get('eps'),
                'pe': quote.get('pe'),
                'dollar_volume': quote.get('avgVolume', 0) * quote.get('price', 0) if quote.get('avgVolume') and quote.get('price') else None,
                'last_updated': get_current_utc_time()
            }

            update_data = {k: v for k, v in update_data.items() if v is not None}

            if update_data:
                self.session.query(Ticker).filter(Ticker.id == self.ticker_id).update(update_data)
                self.session.flush()
                print(f"[{self.ticker}] Updated quote data")
        else:
            print(f"[{self.ticker}] No quote data found")

    def _get_intraday_prices_from_api(self):
        """Fetch intraday prices from FMP API with monthly chunks (2 years)."""
        all_data = []
        to_date = get_current_utc_time()
        limit_date = get_current_utc_time() - timedelta(days=365 * 2)
        call_count = 0

        print(f"[{self.ticker}] Fetching 2 years of intraday data...")
        print(f"[{self.ticker}] Date range: {limit_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")

        while to_date > limit_date:
            call_count += 1
            from_date = to_date - timedelta(days=30)
            if from_date < limit_date:
                from_date = limit_date

            print(f"[{self.ticker}] API call #{call_count}: Fetching {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")

            try:
                price_chunk = self.fmp_api.get_intraday_prices_for_ticker(
                    ticker=self.ticker,
                    from_date=from_date,
                    to_date=to_date
                )

                if not price_chunk:
                    print(f"[{self.ticker}] No data for this period")
                    to_date = from_date
                    continue

                all_data.extend(price_chunk)
                print(f"[{self.ticker}] Received {len(price_chunk):,} records. Total: {len(all_data):,}")

                to_date = from_date
                time.sleep(0.1)

            except Exception as e:
                print(f"[{self.ticker}] Error fetching chunk: {e}")
                to_date = from_date

        if not all_data:
            return pd.DataFrame()

        print(f"[{self.ticker}] Processing {len(all_data):,} total records...")
        df = pd.DataFrame(all_data)
        df.drop_duplicates(subset=['date'], inplace=True)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df.sort_values(by='date', inplace=True)

        print(f"[{self.ticker}] After deduplication: {len(df):,} records")
        return df

    # ================================
    # --> Data loading methods
    # ================================

    def _load_daily_prices(self):
        """Load daily OHLCV data into DailyPrices table (maximum history)."""
        print(f"[{self.ticker}] Loading daily prices (maximum history)...")

        existing_count = self.session.query(DailyPrices).filter(
            DailyPrices.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count:,} daily price records already exist")
            return True

        end_date = get_current_utc_time()
        start_date = datetime(1990, 1, 1, tzinfo=timezone.utc)

        try:
            print(f"[{self.ticker}] Fetching daily prices from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

            daily_data = self.fmp_api.get_daily_prices_for_ticker(
                self.ticker,
                start_date,
                end_date
            )

            if not daily_data or 'historical' not in daily_data or not daily_data['historical']:
                print(f"[{self.ticker}] No daily price data found from API")
                return False

            daily_records = []
            for day_data in daily_data['historical']:
                date_str = day_data.get('date')
                if not date_str:
                    continue

                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                daily_records.append({
                    'ticker_id': self.ticker_id,
                    'datetime': date_obj,
                    'open': day_data.get('open'),
                    'high': day_data.get('high'),
                    'low': day_data.get('low'),
                    'close': day_data.get('close'),
                    'adj_close': day_data.get('adjClose'),
                    'volume': day_data.get('volume')
                })

            if not daily_records:
                print(f"[{self.ticker}] No valid daily price records to insert")
                return False

            stmt = insert(DailyPrices).values(daily_records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'datetime'])
            self.session.execute(stmt)
            self.session.flush()

            print(f"[{self.ticker}] Loaded {len(daily_records):,} daily price records")
            return True

        except Exception as e:
            print(f"[{self.ticker}] Error loading daily prices: {e}")
            return False

    def _load_intraday_prices(self):
        """Load 15-minute intraday price data (2 years)."""
        print(f"[{self.ticker}] Loading intraday prices (2 years)...")

        existing_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count:,} intraday price records already exist")
            return True

        start_date = get_current_utc_time() - timedelta(days=365 * 2)
        end_date = get_current_utc_time()

        try:
            print(f"[{self.ticker}] Attempting to fetch 2 years of intraday data...")
            price_data = get_price_data_15_mins(self.ticker, start_date, end_date)

            if price_data.empty:
                print(f"[{self.ticker}] No existing data, fetching from FMP API...")
                price_data = self._get_intraday_prices_from_api()

            if not price_data.empty:
                price_data['ticker_id'] = self.ticker_id
                price_data.rename(columns={'date': 'datetime'}, inplace=True)

                for col in ['open', 'high', 'low', 'close']:
                    price_data[col] = pd.to_numeric(price_data[col], errors='coerce')

                price_data['volume'] = pd.to_numeric(price_data['volume'], errors='coerce').fillna(0).astype(int)

                price_records = price_data.to_dict('records')

                ordered_columns = ['ticker_id', 'datetime', 'open', 'high', 'low', 'close', 'volume']
                bulk_insert_with_copy(self.session, Price.__table__.fullname, price_records, ordered_columns)

                print(f"[{self.ticker}] Loaded {len(price_records):,} intraday price records")
                return True
            else:
                print(f"[{self.ticker}] No intraday price data found")
                return False

        except Exception as e:
            print(f"[{self.ticker}] Error loading intraday price data: {e}")
            return False

    def _load_balance_sheets(self):
        """Load balance sheet statements."""
        print(f"[{self.ticker}] Loading balance sheets...")

        existing_count = self.session.query(BalanceSheet).filter(
            BalanceSheet.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} balance sheet records already exist")
            return

        data = self.fmp_api.get_balance_sheets(self.ticker, period='quarter')
        if not data:
            print(f"[{self.ticker}] No balance sheet data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                'reportedCurrency': item.get('reportedCurrency'),
                'cik': item.get('cik'),
                'fillingDate': datetime.strptime(item['fillingDate'], '%Y-%m-%d').date() if item.get('fillingDate') else None,
                'acceptedDate': datetime.strptime(item['acceptedDate'][:10], '%Y-%m-%d').date() if item.get('acceptedDate') else None,
                'calendarYear': item.get('calendarYear'),
                'period': item.get('period'),
                'cashAndCashEquivalents': item.get('cashAndCashEquivalents'),
                'shortTermInvestments': item.get('shortTermInvestments'),
                'cashAndShortTermInvestments': item.get('cashAndShortTermInvestments'),
                'netReceivables': item.get('netReceivables'),
                'inventory': item.get('inventory'),
                'otherCurrentAssets': item.get('otherCurrentAssets'),
                'totalCurrentAssets': item.get('totalCurrentAssets'),
                'propertyPlantEquipmentNet': item.get('propertyPlantEquipmentNet'),
                'goodwill': item.get('goodwill'),
                'intangibleAssets': item.get('intangibleAssets'),
                'goodwillAndIntangibleAssets': item.get('goodwillAndIntangibleAssets'),
                'longTermInvestments': item.get('longTermInvestments'),
                'taxAssets': item.get('taxAssets'),
                'otherNonCurrentAssets': item.get('otherNonCurrentAssets'),
                'totalNonCurrentAssets': item.get('totalNonCurrentAssets'),
                'otherAssets': item.get('otherAssets'),
                'totalAssets': item.get('totalAssets'),
                'accountPayables': item.get('accountPayables'),
                'shortTermDebt': item.get('shortTermDebt'),
                'taxPayables': item.get('taxPayables'),
                'deferredRevenue': item.get('deferredRevenue'),
                'otherCurrentLiabilities': item.get('otherCurrentLiabilities'),
                'totalCurrentLiabilities': item.get('totalCurrentLiabilities'),
                'longTermDebt': item.get('longTermDebt'),
                'deferredRevenueNonCurrent': item.get('deferredRevenueNonCurrent'),
                'deferredTaxLiabilitiesNonCurrent': item.get('deferredTaxLiabilitiesNonCurrent'),
                'otherNonCurrentLiabilities': item.get('otherNonCurrentLiabilities'),
                'totalNonCurrentLiabilities': item.get('totalNonCurrentLiabilities'),
                'otherLiabilities': item.get('otherLiabilities'),
                'capitalLeaseObligations': item.get('capitalLeaseObligations'),
                'totalLiabilities': item.get('totalLiabilities'),
                'preferredStock': item.get('preferredStock'),
                'commonStock': item.get('commonStock'),
                'retainedEarnings': item.get('retainedEarnings'),
                'accumulatedOtherComprehensiveIncomeLoss': item.get('accumulatedOtherComprehensiveIncomeLoss'),
                'othertotalStockholdersEquity': item.get('othertotalStockholdersEquity'),
                'totalStockholdersEquity': item.get('totalStockholdersEquity'),
                'totalEquity': item.get('totalEquity'),
                'totalLiabilitiesAndStockholdersEquity': item.get('totalLiabilitiesAndStockholdersEquity'),
                'minorityInterest': item.get('minorityInterest'),
                'totalLiabilitiesAndTotalEquity': item.get('totalLiabilitiesAndTotalEquity'),
                'totalInvestments': item.get('totalInvestments'),
                'totalDebt': item.get('totalDebt'),
                'netDebt': item.get('netDebt'),
                'link': item.get('link'),
                'finalLink': item.get('finalLink')
            }
            records.append(record)

        if records:
            stmt = insert(BalanceSheet).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} balance sheet records")

    def _load_income_statements(self):
        """Load income statements."""
        print(f"[{self.ticker}] Loading income statements...")

        existing_count = self.session.query(IncomeStatement).filter(
            IncomeStatement.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} income statement records already exist")
            return

        data = self.fmp_api.get_income_statements(self.ticker, period='quarter')
        if not data:
            print(f"[{self.ticker}] No income statement data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                'reportedCurrency': item.get('reportedCurrency'),
                'cik': item.get('cik'),
                'fillingDate': datetime.strptime(item['fillingDate'], '%Y-%m-%d').date() if item.get('fillingDate') else None,
                'acceptedDate': datetime.strptime(item['acceptedDate'][:10], '%Y-%m-%d').date() if item.get('acceptedDate') else None,
                'calendarYear': item.get('calendarYear'),
                'period': item.get('period'),
                'revenue': item.get('revenue'),
                'costOfRevenue': item.get('costOfRevenue'),
                'grossProfit': item.get('grossProfit'),
                'grossProfitRatio': item.get('grossProfitRatio'),
                'researchAndDevelopmentExpenses': item.get('researchAndDevelopmentExpenses'),
                'generalAndAdministrativeExpenses': item.get('generalAndAdministrativeExpenses'),
                'sellingAndMarketingExpenses': item.get('sellingAndMarketingExpenses'),
                'sellingGeneralAndAdministrativeExpenses': item.get('sellingGeneralAndAdministrativeExpenses'),
                'otherExpenses': item.get('otherExpenses'),
                'operatingExpenses': item.get('operatingExpenses'),
                'costAndExpenses': item.get('costAndExpenses'),
                'interestIncome': item.get('interestIncome'),
                'interestExpense': item.get('interestExpense'),
                'depreciationAndAmortization': item.get('depreciationAndAmortization'),
                'ebitda': item.get('ebitda'),
                'ebitdaratio': item.get('ebitdaratio'),
                'operatingIncome': item.get('operatingIncome'),
                'operatingIncomeRatio': item.get('operatingIncomeRatio'),
                'totalOtherIncomeExpensesNet': item.get('totalOtherIncomeExpensesNet'),
                'incomeBeforeTax': item.get('incomeBeforeTax'),
                'incomeBeforeTaxRatio': item.get('incomeBeforeTaxRatio'),
                'incomeTaxExpense': item.get('incomeTaxExpense'),
                'netIncome': item.get('netIncome'),
                'netIncomeRatio': item.get('netIncomeRatio'),
                'eps': item.get('eps'),
                'epsdiluted': item.get('epsdiluted'),
                'weightedAverageShsOut': item.get('weightedAverageShsOut'),
                'weightedAverageShsOutDil': item.get('weightedAverageShsOutDil'),
                'link': item.get('link'),
                'finalLink': item.get('finalLink')
            }
            records.append(record)

        if records:
            stmt = insert(IncomeStatement).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} income statement records")

    def _load_cash_flow_statements(self):
        """Load cash flow statements."""
        print(f"[{self.ticker}] Loading cash flow statements...")

        existing_count = self.session.query(CashFlowStatement).filter(
            CashFlowStatement.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} cash flow statement records already exist")
            return

        data = self.fmp_api.get_cash_flow_statements(self.ticker, period='quarter')
        if not data:
            print(f"[{self.ticker}] No cash flow statement data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                'reportedCurrency': item.get('reportedCurrency'),
                'cik': item.get('cik'),
                'fillingDate': datetime.strptime(item['fillingDate'], '%Y-%m-%d').date() if item.get('fillingDate') else None,
                'acceptedDate': datetime.strptime(item['acceptedDate'][:10], '%Y-%m-%d').date() if item.get('acceptedDate') else None,
                'calendarYear': item.get('calendarYear'),
                'period': item.get('period'),
                'netIncome': item.get('netIncome'),
                'depreciationAndAmortization': item.get('depreciationAndAmortization'),
                'deferredIncomeTax': item.get('deferredIncomeTax'),
                'stockBasedCompensation': item.get('stockBasedCompensation'),
                'changeInWorkingCapital': item.get('changeInWorkingCapital'),
                'accountsReceivables': item.get('accountsReceivables'),
                'inventory': item.get('inventory'),
                'accountsPayables': item.get('accountsPayables'),
                'otherWorkingCapital': item.get('otherWorkingCapital'),
                'otherNonCashItems': item.get('otherNonCashItems'),
                'netCashProvidedByOperatingActivities': item.get('netCashProvidedByOperatingActivities'),
                'investmentsInPropertyPlantAndEquipment': item.get('investmentsInPropertyPlantAndEquipment'),
                'acquisitionsNet': item.get('acquisitionsNet'),
                'purchasesOfInvestments': item.get('purchasesOfInvestments'),
                'salesMaturitiesOfInvestments': item.get('salesMaturitiesOfInvestments'),
                'otherInvestingActivites': item.get('otherInvestingActivites'),
                'netCashUsedForInvestingActivites': item.get('netCashUsedForInvestingActivites'),
                'debtRepayment': item.get('debtRepayment'),
                'commonStockIssued': item.get('commonStockIssued'),
                'commonStockRepurchased': item.get('commonStockRepurchased'),
                'dividendsPaid': item.get('dividendsPaid'),
                'otherFinancingActivites': item.get('otherFinancingActivites'),
                'netCashUsedProvidedByFinancingActivities': item.get('netCashUsedProvidedByFinancingActivities'),
                'effectOfForexChangesOnCash': item.get('effectOfForexChangesOnCash'),
                'netChangeInCash': item.get('netChangeInCash'),
                'cashAtEndOfPeriod': item.get('cashAtEndOfPeriod'),
                'cashAtBeginningOfPeriod': item.get('cashAtBeginningOfPeriod'),
                'operatingCashFlow': item.get('operatingCashFlow'),
                'capitalExpenditure': item.get('capitalExpenditure'),
                'freeCashFlow': item.get('freeCashFlow'),
                'link': item.get('link'),
                'finalLink': item.get('finalLink')
            }
            records.append(record)

        if records:
            stmt = insert(CashFlowStatement).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} cash flow statement records")

    def _load_financial_ratios(self):
        """Load financial ratios."""
        print(f"[{self.ticker}] Loading financial ratios...")

        existing_count = self.session.query(FinancialRatio).filter(
            FinancialRatio.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} financial ratio records already exist")
            return

        data = self.fmp_api.get_financial_ratios(self.ticker, period='quarter')
        if not data:
            print(f"[{self.ticker}] No financial ratio data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                'calendarYear': item.get('calendarYear'),
                'period': item.get('period'),
                'currentRatio': item.get('currentRatio'),
                'quickRatio': item.get('quickRatio'),
                'cashRatio': item.get('cashRatio'),
                'daysOfSalesOutstanding': item.get('daysOfSalesOutstanding'),
                'daysOfInventoryOutstanding': item.get('daysOfInventoryOutstanding'),
                'operatingCycle': item.get('operatingCycle'),
                'daysOfPayablesOutstanding': item.get('daysOfPayablesOutstanding'),
                'cashConversionCycle': item.get('cashConversionCycle'),
                'grossProfitMargin': item.get('grossProfitMargin'),
                'operatingProfitMargin': item.get('operatingProfitMargin'),
                'pretaxProfitMargin': item.get('pretaxProfitMargin'),
                'netProfitMargin': item.get('netProfitMargin'),
                'effectiveTaxRate': item.get('effectiveTaxRate'),
                'returnOnAssets': item.get('returnOnAssets'),
                'returnOnEquity': item.get('returnOnEquity'),
                'returnOnCapitalEmployed': item.get('returnOnCapitalEmployed'),
                'netIncomePerEBT': item.get('netIncomePerEBT'),
                'ebtPerEbit': item.get('ebtPerEbit'),
                'ebitPerRevenue': item.get('ebitPerRevenue'),
                'debtRatio': item.get('debtRatio'),
                'debtEquityRatio': item.get('debtEquityRatio'),
                'longTermDebtToCapitalization': item.get('longTermDebtToCapitalization'),
                'totalDebtToCapitalization': item.get('totalDebtToCapitalization'),
                'interestCoverage': item.get('interestCoverage'),
                'cashFlowToDebtRatio': item.get('cashFlowToDebtRatio'),
                'companyEquityMultiplier': item.get('companyEquityMultiplier'),
                'receivablesTurnover': item.get('receivablesTurnover'),
                'payablesTurnover': item.get('payablesTurnover'),
                'inventoryTurnover': item.get('inventoryTurnover'),
                'fixedAssetTurnover': item.get('fixedAssetTurnover'),
                'assetTurnover': item.get('assetTurnover'),
                'operatingCashFlowPerShare': item.get('operatingCashFlowPerShare'),
                'freeCashFlowPerShare': item.get('freeCashFlowPerShare'),
                'cashPerShare': item.get('cashPerShare'),
                'payoutRatio': item.get('payoutRatio'),
                'operatingCashFlowSalesRatio': item.get('operatingCashFlowSalesRatio'),
                'freeCashFlowOperatingCashFlowRatio': item.get('freeCashFlowOperatingCashFlowRatio'),
                'cashFlowCoverageRatios': item.get('cashFlowCoverageRatios'),
                'shortTermCoverageRatios': item.get('shortTermCoverageRatios'),
                'capitalExpenditureCoverageRatio': item.get('capitalExpenditureCoverageRatio'),
                'dividendPaidAndCapexCoverageRatio': item.get('dividendPaidAndCapexCoverageRatio'),
                'dividendPayoutRatio': item.get('dividendPayoutRatio'),
                'priceBookValueRatio': item.get('priceBookValueRatio'),
                'priceToBookRatio': item.get('priceToBookRatio'),
                'priceToSalesRatio': item.get('priceToSalesRatio'),
                'priceEarningsRatio': item.get('priceEarningsRatio'),
                'priceToFreeCashFlowsRatio': item.get('priceToFreeCashFlowsRatio'),
                'priceToOperatingCashFlowsRatio': item.get('priceToOperatingCashFlowsRatio'),
                'priceCashFlowRatio': item.get('priceCashFlowRatio'),
                'priceEarningsToGrowthRatio': item.get('priceEarningsToGrowthRatio'),
                'priceSalesRatio': item.get('priceSalesRatio'),
                'dividendYield': item.get('dividendYield'),
                'enterpriseValueMultiple': item.get('enterpriseValueMultiple'),
                'priceFairValue': item.get('priceFairValue')
            }
            records.append(record)

        if records:
            stmt = insert(FinancialRatio).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} financial ratio records")

    def _load_analyst_estimates(self):
        """Load analyst estimates."""
        print(f"[{self.ticker}] Loading analyst estimates...")

        existing_count = self.session.query(AnalystEstimate).filter(
            AnalystEstimate.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} analyst estimate records already exist")
            return

        data = self.fmp_api.get_analyst_estimates(self.ticker)
        if not data:
            print(f"[{self.ticker}] No analyst estimate data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                'revenueLow': item.get('estimatedRevenueLow'),
                'revenueHigh': item.get('estimatedRevenueHigh'),
                'revenueAvg': item.get('estimatedRevenueAvg'),
                'ebitdaLow': item.get('estimatedEbitdaLow'),
                'ebitdaHigh': item.get('estimatedEbitdaHigh'),
                'ebitdaAvg': item.get('estimatedEbitdaAvg'),
                'ebitLow': item.get('estimatedEbitLow'),
                'ebitHigh': item.get('estimatedEbitHigh'),
                'ebitAvg': item.get('estimatedEbitAvg'),
                'netIncomeLow': item.get('estimatedNetIncomeLow'),
                'netIncomeHigh': item.get('estimatedNetIncomeHigh'),
                'netIncomeAvg': item.get('estimatedNetIncomeAvg'),
                'sgaExpenseLow': item.get('estimatedSgaExpenseLow'),
                'sgaExpenseHigh': item.get('estimatedSgaExpenseHigh'),
                'sgaExpenseAvg': item.get('estimatedSgaExpenseAvg'),
                'epsAvg': item.get('estimatedEpsAvg'),
                'epsHigh': item.get('estimatedEpsHigh'),
                'epsLow': item.get('estimatedEpsLow'),
                'numAnalystsRevenue': item.get('numberAnalystEstimatedRevenue'),
                'numAnalystsEps': item.get('numberAnalystsEstimatedEps')
            }
            records.append(record)

        if records:
            stmt = insert(AnalystEstimate).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} analyst estimate records")

    def _load_dividends(self):
        """Load dividend data."""
        print(f"[{self.ticker}] Loading dividend data...")

        existing_count = self.session.query(Dividend).filter(
            Dividend.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} dividend records already exist")
            return

        dividend_data = self.fmp_api.get_dividends(self.ticker)

        if dividend_data:
            dividend_records = []

            for dividend in dividend_data:
                dividend_record = {
                    'ticker_id': self.ticker_id,
                    'date': pd.to_datetime(dividend.get('date'), utc=True).date() if dividend.get('date') else None,
                    'recordDate': pd.to_datetime(dividend.get('recordDate'), utc=True).date() if dividend.get('recordDate') else None,
                    'paymentDate': pd.to_datetime(dividend.get('paymentDate'), utc=True).date() if dividend.get('paymentDate') else None,
                    'declarationDate': pd.to_datetime(dividend.get('declarationDate'), utc=True).date() if dividend.get('declarationDate') else None,
                    'adjDividend': dividend.get('adjDividend'),
                    'dividend': dividend.get('dividend'),
                    'yield_': dividend.get('yield'),
                    'frequency': dividend.get('frequency')
                }

                dividend_record = {k: v for k, v in dividend_record.items() if v is not None}

                if 'date' in dividend_record:
                    dividend_records.append(dividend_record)

            if dividend_records:
                self.session.bulk_insert_mappings(Dividend, dividend_records)
                self.session.flush()
                print(f"[{self.ticker}] Loaded {len(dividend_records)} dividend records")
            else:
                print(f"[{self.ticker}] No valid dividend data found")
        else:
            print(f"[{self.ticker}] No dividend data available")

    def _load_stock_news(self):
        """Load stock news articles."""
        print(f"[{self.ticker}] Loading stock news...")

        existing_count = self.session.query(StockNews).filter(
            StockNews.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} stock news records already exist")
            return

        data = self.fmp_api.get_stock_news(self.ticker, limit=1000)
        if not data:
            print(f"[{self.ticker}] No stock news found")
            return

        records = []
        for item in data:
            url = item.get('url')
            if not url:
                continue

            published_date = None
            if item.get('publishedDate'):
                try:
                    published_date = pd.to_datetime(item['publishedDate'], utc=True)
                except (ValueError, TypeError):
                    pass

            record = {
                'ticker_id': self.ticker_id,
                'publishedDate': published_date,
                'publisher': item.get('publisher'),
                'title': item.get('title'),
                'image': item.get('image'),
                'site': item.get('site'),
                'text': item.get('text'),
                'url': url[:512]
            }
            records.append(record)

        if records:
            stmt = insert(StockNews).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'url'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} stock news records")

    def _load_press_releases(self):
        """Load press releases."""
        print(f"[{self.ticker}] Loading press releases...")

        existing_count = self.session.query(PressRelease).filter(
            PressRelease.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} press release records already exist")
            return

        data = self.fmp_api.get_press_releases(self.ticker, limit=1000)
        if not data:
            print(f"[{self.ticker}] No press releases found")
            return

        records = []
        for item in data:
            url = item.get('url')
            if not url:
                continue

            published_date = None
            if item.get('date'):
                try:
                    published_date = pd.to_datetime(item['date'], utc=True)
                except (ValueError, TypeError):
                    pass

            record = {
                'ticker_id': self.ticker_id,
                'publishedDate': published_date,
                'publisher': item.get('publisher'),
                'title': item.get('title'),
                'image': item.get('image'),
                'site': item.get('site'),
                'text': item.get('text'),
                'url': url[:512]
            }
            records.append(record)

        if records:
            stmt = insert(PressRelease).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'url'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} press release records")

    def _load_stock_grades(self):
        """Load individual stock grades and grade summaries."""
        print(f"[{self.ticker}] Loading stock grades...")

        # Individual grades
        existing_individual = self.session.query(StockGradesIndividual).filter(
            StockGradesIndividual.ticker_id == self.ticker_id
        ).count()

        if existing_individual == 0:
            data = self.fmp_api.get_stock_grades_individual(self.ticker)
            if data:
                records = []
                for item in data:
                    date_str = item.get('date')
                    grading_company = item.get('gradingCompany')
                    if not date_str or not grading_company:
                        continue

                    record = {
                        'ticker_id': self.ticker_id,
                        'date': datetime.strptime(date_str[:10], '%Y-%m-%d').date(),
                        'gradingCompany': grading_company,
                        'previousGrade': item.get('previousGrade'),
                        'newGrade': item.get('newGrade'),
                        'action': item.get('action')
                    }
                    records.append(record)

                if records:
                    stmt = insert(StockGradesIndividual).values(records)
                    stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date', 'gradingCompany'])
                    self.session.execute(stmt)
                    self.session.flush()
                    print(f"[{self.ticker}] Loaded {len(records)} individual grade records")
        else:
            print(f"[{self.ticker}] {existing_individual} individual grade records already exist")

        # Grade summaries
        existing_summary = self.session.query(StockGradesSummary).filter(
            StockGradesSummary.ticker_id == self.ticker_id
        ).count()

        if existing_summary == 0:
            data = self.fmp_api.get_stock_grades_summary(self.ticker)
            if data:
                records = []
                for item in data:
                    date_str = item.get('date')
                    if not date_str:
                        continue

                    record = {
                        'ticker_id': self.ticker_id,
                        'date': datetime.strptime(date_str[:10], '%Y-%m-%d').date(),
                        'analystRatingsStrongBuy': item.get('strongBuy'),
                        'analystRatingsBuy': item.get('buy'),
                        'analystRatingsHold': item.get('hold'),
                        'analystRatingsSell': item.get('sell'),
                        'analystRatingsStrongSell': item.get('strongSell')
                    }
                    records.append(record)

                if records:
                    stmt = insert(StockGradesSummary).values(records)
                    stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
                    self.session.execute(stmt)
                    self.session.flush()
                    print(f"[{self.ticker}] Loaded {len(records)} grade summary records")
        else:
            print(f"[{self.ticker}] {existing_summary} grade summary records already exist")

    def _load_rating_scores(self):
        """Load historical rating scores."""
        print(f"[{self.ticker}] Loading rating scores...")

        existing_count = self.session.query(Rating).filter(
            Rating.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} rating score records already exist")
            return

        data = self.fmp_api.get_rating_scores(self.ticker)
        if not data:
            print(f"[{self.ticker}] No rating score data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str[:10], '%Y-%m-%d').date(),
                'rating': item.get('rating'),
                'overallScore': item.get('ratingScore'),
                'discountedCashFlowScore': item.get('ratingDetailsDCFScore'),
                'returnOnEquityScore': item.get('ratingDetailsROEScore'),
                'returnOnAssetsScore': item.get('ratingDetailsROAScore'),
                'debtToEquityScore': item.get('ratingDetailsDEScore'),
                'priceToEarningsScore': item.get('ratingDetailsPEScore'),
                'priceToBookScore': item.get('ratingDetailsPBScore')
            }
            records.append(record)

        if records:
            stmt = insert(Rating).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} rating score records")

    def _load_analyst_recommendations(self):
        """Load analyst recommendations."""
        print(f"[{self.ticker}] Loading analyst recommendations...")

        existing_count = self.session.query(AnalystRecommendation).filter(
            AnalystRecommendation.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} analyst recommendation records already exist")
            return

        data = self.fmp_api.get_analyst_recommendations(self.ticker)
        if not data:
            print(f"[{self.ticker}] No analyst recommendation data found")
            return

        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue

            record = {
                'ticker_id': self.ticker_id,
                'date': datetime.strptime(date_str[:10], '%Y-%m-%d').date(),
                'rating': item.get('rating'),
                'ratingScore': item.get('ratingScore'),
                'ratingRecommendation': item.get('ratingRecommendation'),
                'ratingDetailsDCFScore': item.get('ratingDetailsDCFScore'),
                'ratingDetailsDCFRecommendation': item.get('ratingDetailsDCFRecommendation'),
                'ratingDetailsROEScore': item.get('ratingDetailsROEScore'),
                'ratingDetailsROERecommendation': item.get('ratingDetailsROERecommendation'),
                'ratingDetailsROAScore': item.get('ratingDetailsROAScore'),
                'ratingDetailsROARecommendation': item.get('ratingDetailsROARecommendation'),
                'ratingDetailsDEScore': item.get('ratingDetailsDEScore'),
                'ratingDetailsDERecommendation': item.get('ratingDetailsDERecommendation'),
                'ratingDetailsPEScore': item.get('ratingDetailsPEScore'),
                'ratingDetailsPERecommendation': item.get('ratingDetailsPERecommendation'),
                'ratingDetailsPBScore': item.get('ratingDetailsPBScore'),
                'ratingDetailsPBRecommendation': item.get('ratingDetailsPBRecommendation')
            }
            records.append(record)

        if records:
            stmt = insert(AnalystRecommendation).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'date'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} analyst recommendation records")

    def _load_price_target_summary(self):
        """Load price target summary."""
        print(f"[{self.ticker}] Loading price target summary...")

        existing = self.session.query(PriceTargetSummary).filter(
            PriceTargetSummary.ticker_id == self.ticker_id
        ).first()

        if existing:
            print(f"[{self.ticker}] Price target summary already exists")
            return

        data = self.fmp_api.get_price_target_summary(self.ticker)
        if not data or len(data) == 0:
            print(f"[{self.ticker}] No price target summary found")
            return

        item = data[0] if isinstance(data, list) else data

        record = PriceTargetSummary(
            ticker_id=self.ticker_id,
            lastMonthCount=item.get('lastMonth'),
            lastMonthAvgPriceTarget=item.get('lastMonthAvgPriceTarget'),
            lastQuarterCount=item.get('lastQuarter'),
            lastQuarterAvgPriceTarget=item.get('lastQuarterAvgPriceTarget'),
            lastYearCount=item.get('lastYear'),
            lastYearAvgPriceTarget=item.get('lastYearAvgPriceTarget'),
            allTimeCount=item.get('allTime'),
            allTimeAvgPriceTarget=item.get('allTimeAvgPriceTarget'),
            publishers=item.get('publishers')
        )

        self.session.add(record)
        self.session.flush()
        print(f"[{self.ticker}] Loaded price target summary")

    def _load_price_target_news(self):
        """Load price target news."""
        print(f"[{self.ticker}] Loading price target news...")

        existing_count = self.session.query(PriceTargetNews).filter(
            PriceTargetNews.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} price target news records already exist")
            return

        data = self.fmp_api.get_price_target_news(self.ticker, limit=1000)
        if not data:
            print(f"[{self.ticker}] No price target news found")
            return

        records = []
        for item in data:
            news_url = item.get('newsURL')
            if not news_url:
                continue

            published_date = None
            if item.get('publishedDate'):
                try:
                    published_date = pd.to_datetime(item['publishedDate'], utc=True)
                except (ValueError, TypeError):
                    pass

            record = {
                'ticker_id': self.ticker_id,
                'publishedDate': published_date,
                'newsURL': news_url[:512],
                'newsTitle': item.get('newsTitle'),
                'analystName': item.get('analystName'),
                'priceTarget': item.get('priceTarget'),
                'adjPriceTarget': item.get('adjPriceTarget'),
                'priceWhenPosted': item.get('priceWhenPosted'),
                'newsPublisher': item.get('newsPublisher'),
                'newsBaseURL': item.get('newsBaseURL'),
                'analystCompany': item.get('analystCompany')
            }
            records.append(record)

        if records:
            stmt = insert(PriceTargetNews).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'newsURL'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} price target news records")

    def _load_stock_grade_news(self):
        """Load stock grade news."""
        print(f"[{self.ticker}] Loading stock grade news...")

        existing_count = self.session.query(StockGradeNews).filter(
            StockGradeNews.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] {existing_count} stock grade news records already exist")
            return

        data = self.fmp_api.get_stock_grade_news(self.ticker, limit=1000)
        if not data:
            print(f"[{self.ticker}] No stock grade news found")
            return

        records = []
        for item in data:
            news_url = item.get('newsURL')
            if not news_url:
                continue

            published_date = None
            if item.get('publishedDate'):
                try:
                    published_date = pd.to_datetime(item['publishedDate'], utc=True)
                except (ValueError, TypeError):
                    pass

            record = {
                'ticker_id': self.ticker_id,
                'publishedDate': published_date,
                'newsURL': news_url[:512],
                'newsTitle': item.get('newsTitle'),
                'newsBaseURL': item.get('newsBaseURL'),
                'newsPublisher': item.get('newsPublisher'),
                'newGrade': item.get('newGrade'),
                'previousGrade': item.get('previousGrade'),
                'gradingCompany': item.get('gradingCompany'),
                'action': item.get('action'),
                'priceWhenPosted': item.get('priceWhenPosted')
            }
            records.append(record)

        if records:
            stmt = insert(StockGradeNews).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'newsURL'])
            self.session.execute(stmt)
            self.session.flush()
            print(f"[{self.ticker}] Loaded {len(records)} stock grade news records")

    # ================================
    # --> Main orchestration
    # ================================

    def load_ticker_data(self, allow_partial_reload=False):
        """
        Main method to orchestrate loading all ticker data.

        Args:
            allow_partial_reload: If True, will complete missing data for existing tickers
        """
        print(f"\n{'='*60}")
        print(f"Loading ticker data: {self.ticker}")
        print(f"{'='*60}\n")

        self.session = MarketSession()

        try:
            ticker_status = self._ensure_ticker_exists(allow_partial_reload)
            if ticker_status is False:
                print(f"\n[{self.ticker}] Aborting: Ticker already exists. Use allow_partial_reload=True to complete missing data.")
                return

            is_partial_reload = (ticker_status == "partial")

            if not is_partial_reload:
                self._update_company_profile()

            self._update_ticker_quote_data()

            has_daily_data = self._load_daily_prices()
            if not has_daily_data and not is_partial_reload:
                print(f"\n[{self.ticker}] Warning: No daily price data available")

            self._load_intraday_prices()

            self._load_balance_sheets()
            self._load_income_statements()
            self._load_cash_flow_statements()

            self._load_financial_ratios()
            self._load_analyst_estimates()
            self._load_dividends()

            self._load_stock_news()
            self._load_press_releases()

            self._load_stock_grades()
            self._load_rating_scores()
            self._load_analyst_recommendations()

            self._load_price_target_summary()
            self._load_price_target_news()
            self._load_stock_grade_news()

            self.session.commit()

            print(f"\n[{self.ticker}] Successfully loaded all ticker data!")

        except Exception as e:
            print(f"\n[{self.ticker}] Error loading ticker data: {e}")
            self.session.rollback()
            raise
        finally:
            self.session.close()


def cleanup_ticker_data(ticker: str):
    """
    Remove all data for a ticker from the database.
    Useful for cleaning up partial loads before re-running.

    Args:
        ticker: Stock ticker symbol to clean up
    """
    session = MarketSession()
    try:
        ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()
        if not ticker_obj:
            print(f"[{ticker}] No ticker found in database.")
            return

        ticker_id = ticker_obj.id

        prices_deleted = session.query(Price).filter(Price.ticker_id == ticker_id).delete()
        daily_prices_deleted = session.query(DailyPrices).filter(DailyPrices.ticker_id == ticker_id).delete()

        balance_sheets_deleted = session.query(BalanceSheet).filter(BalanceSheet.ticker_id == ticker_id).delete()
        income_statements_deleted = session.query(IncomeStatement).filter(IncomeStatement.ticker_id == ticker_id).delete()
        cash_flow_deleted = session.query(CashFlowStatement).filter(CashFlowStatement.ticker_id == ticker_id).delete()
        ratios_deleted = session.query(FinancialRatio).filter(FinancialRatio.ticker_id == ticker_id).delete()
        estimates_deleted = session.query(AnalystEstimate).filter(AnalystEstimate.ticker_id == ticker_id).delete()
        dividends_deleted = session.query(Dividend).filter(Dividend.ticker_id == ticker_id).delete()

        stock_news_deleted = session.query(StockNews).filter(StockNews.ticker_id == ticker_id).delete()
        press_releases_deleted = session.query(PressRelease).filter(PressRelease.ticker_id == ticker_id).delete()
        price_target_news_deleted = session.query(PriceTargetNews).filter(PriceTargetNews.ticker_id == ticker_id).delete()
        grade_news_deleted = session.query(StockGradeNews).filter(StockGradeNews.ticker_id == ticker_id).delete()

        grades_individual_deleted = session.query(StockGradesIndividual).filter(StockGradesIndividual.ticker_id == ticker_id).delete()
        grades_summary_deleted = session.query(StockGradesSummary).filter(StockGradesSummary.ticker_id == ticker_id).delete()
        ratings_deleted = session.query(Rating).filter(Rating.ticker_id == ticker_id).delete()
        recommendations_deleted = session.query(AnalystRecommendation).filter(AnalystRecommendation.ticker_id == ticker_id).delete()
        price_target_summary_deleted = session.query(PriceTargetSummary).filter(PriceTargetSummary.ticker_id == ticker_id).delete()

        session.delete(ticker_obj)
        session.commit()

        print(f"[{ticker}] Cleanup complete:")
        print(f"  - Deleted {prices_deleted:,} intraday price records")
        print(f"  - Deleted {daily_prices_deleted:,} daily price records")
        print(f"  - Deleted {balance_sheets_deleted} balance sheet records")
        print(f"  - Deleted {income_statements_deleted} income statement records")
        print(f"  - Deleted {cash_flow_deleted} cash flow statement records")
        print(f"  - Deleted {ratios_deleted} financial ratio records")
        print(f"  - Deleted {estimates_deleted} analyst estimate records")
        print(f"  - Deleted {dividends_deleted} dividend records")
        print(f"  - Deleted {stock_news_deleted} stock news records")
        print(f"  - Deleted {press_releases_deleted} press release records")
        print(f"  - Deleted {price_target_news_deleted} price target news records")
        print(f"  - Deleted {grade_news_deleted} grade news records")
        print(f"  - Deleted {grades_individual_deleted} individual grade records")
        print(f"  - Deleted {grades_summary_deleted} grade summary records")
        print(f"  - Deleted {ratings_deleted} rating records")
        print(f"  - Deleted {recommendations_deleted} recommendation records")
        print(f"  - Deleted {price_target_summary_deleted} price target summary")
        print(f"  - Deleted ticker record")

    except Exception as e:
        print(f"[{ticker}] Error during cleanup: {e}")
        session.rollback()
    finally:
        session.close()


def load_single_ticker(
    ticker: str,
    sector: str = None,
    industry: str = None,
    sub_industry: str = None,
    allow_partial_reload: bool = False
):
    """
    Convenience function to load a single ticker.

    Args:
        ticker: Stock ticker symbol
        sector: Optional sector classification
        industry: Optional industry classification
        sub_industry: Optional sub-industry classification
        allow_partial_reload: If True, completes missing data for existing tickers
    """
    loader = OptimizedTickerDataLoader(
        ticker,
        sector=sector,
        industry=industry,
        sub_industry=sub_industry
    )
    loader.load_ticker_data(allow_partial_reload=allow_partial_reload)


def load_multiple_tickers(ticker_list: list):
    """
    Load multiple tickers in sequence.

    Args:
        ticker_list: List of tuples (ticker, sector, industry, sub_industry)
                     or list of ticker strings
    """
    for idx, item in enumerate(ticker_list):
        if isinstance(item, tuple):
            ticker, sector, industry, sub_industry = item
        else:
            ticker = item
            sector = industry = sub_industry = None

        print(f"\n{'#'*60}")
        print(f"# Processing ticker {idx + 1}/{len(ticker_list)}: {ticker}")
        print(f"{'#'*60}")

        try:
            load_single_ticker(ticker, sector, industry, sub_industry)
            time.sleep(1)
        except Exception as e:
            print(f"Failed to load {ticker}: {e}")
            continue
