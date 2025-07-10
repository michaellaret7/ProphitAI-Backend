# database/models/market_models.py
"""
Complete Market Data Models for all tables in the market_data database
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Date, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.src.db.core.db_config import MarketBase
import uuid

# =============================================================================
# TICKER UNIVERSE SCHEMA
# =============================================================================

class Ticker(MarketBase):
    __tablename__ = 'tickers'
    __table_args__ = {'schema': 'ticker_universe'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, nullable=False, unique=True, index=True)
    sector = Column(String, index=True)
    industry = Column(String, index=True)
    sub_industry = Column(String)
    is_etf = Column(Boolean, default=False)
    
    # Quote data columns
    price = Column(Float)
    market_cap = Column(Numeric)
    avg_volume = Column(Numeric)
    eps = Column(Float)
    pe = Column(Float)
    dollar_volume = Column(Numeric)  # Calculated as avg_volume * price
    last_updated = Column(DateTime)  # Track when quote data was last updated
    
    # Relationships - using lazy='dynamic' for large collections
    balance_sheets = relationship('BalanceSheet', back_populates='ticker', lazy='dynamic')
    cash_flow_statements = relationship('CashFlowStatement', back_populates='ticker', lazy='dynamic')
    income_statements = relationship('IncomeStatement', back_populates='ticker', lazy='dynamic')
    financial_ratios = relationship('FinancialRatio', back_populates='ticker', lazy='dynamic')
    analyst_estimates = relationship('AnalystEstimate', back_populates='ticker', lazy='dynamic')
    etf_holdings = relationship('ETFHolding', back_populates='ticker', lazy='dynamic')
    etf_info = relationship('ETFInfo', back_populates='ticker', uselist=False)
    dividends = relationship('Dividend', back_populates='ticker', lazy='dynamic')
    earnings_transcripts = relationship('EarningsTranscript', back_populates='ticker', lazy='dynamic')
    prices = relationship('Price', back_populates='ticker', lazy='dynamic')
    press_releases = relationship('PressRelease', back_populates='ticker', lazy='dynamic')
    stock_news = relationship('StockNews', back_populates='ticker', lazy='dynamic')
    price_target_news = relationship('PriceTargetNews', back_populates='ticker', lazy='dynamic')
    stock_grade_news = relationship('StockGradeNews', back_populates='ticker', lazy='dynamic')
    general_news = relationship('GeneralNews', back_populates='ticker', lazy='dynamic')
    stock_grades_individual = relationship('StockGradesIndividual', back_populates='ticker', lazy='dynamic')
    stock_grades_summary = relationship('StockGradesSummary', back_populates='ticker', lazy='dynamic')
    rating_scores = relationship('Rating', back_populates='ticker', lazy='dynamic')
    analyst_recommendations = relationship('AnalystRecommendation', back_populates='ticker', lazy='dynamic')
    price_target_summary = relationship('PriceTargetSummary', back_populates='ticker', uselist=False)

# =============================================================================
# FUNDAMENTAL DATA SCHEMA
# =============================================================================

class BalanceSheet(MarketBase):
    __tablename__ = 'balance_sheets'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    reportedCurrency = Column(String)
    cik = Column(String)
    fillingDate = Column(Date)
    acceptedDate = Column(Date)
    calendarYear = Column(Integer, index=True)
    period = Column(String)
    cashAndCashEquivalents = Column(Numeric)
    shortTermInvestments = Column(Numeric)
    cashAndShortTermInvestments = Column(Numeric)
    netReceivables = Column(Numeric)
    inventory = Column(Numeric)
    otherCurrentAssets = Column(Numeric)
    totalCurrentAssets = Column(Numeric)
    propertyPlantEquipmentNet = Column(Numeric)
    goodwill = Column(Numeric)
    intangibleAssets = Column(Numeric)
    goodwillAndIntangibleAssets = Column(Numeric)
    longTermInvestments = Column(Numeric)
    taxAssets = Column(Numeric)
    otherNonCurrentAssets = Column(Numeric)
    totalNonCurrentAssets = Column(Numeric)
    otherAssets = Column(Numeric)
    totalAssets = Column(Numeric)
    accountPayables = Column(Numeric)
    shortTermDebt = Column(Numeric)
    taxPayables = Column(Numeric)
    deferredRevenue = Column(Numeric)
    otherCurrentLiabilities = Column(Numeric)
    totalCurrentLiabilities = Column(Numeric)
    longTermDebt = Column(Numeric)
    deferredRevenueNonCurrent = Column(Numeric)
    deferredTaxLiabilitiesNonCurrent = Column(Numeric)
    otherNonCurrentLiabilities = Column(Numeric)
    totalNonCurrentLiabilities = Column(Numeric)
    otherLiabilities = Column(Numeric)
    capitalLeaseObligations = Column(Numeric)
    totalLiabilities = Column(Numeric)
    preferredStock = Column(Numeric)
    commonStock = Column(Numeric)
    retainedEarnings = Column(Numeric)
    accumulatedOtherComprehensiveIncomeLoss = Column(Numeric)
    othertotalStockholdersEquity = Column(Numeric)
    totalStockholdersEquity = Column(Numeric)
    totalEquity = Column(Numeric)
    totalLiabilitiesAndStockholdersEquity = Column(Numeric)
    minorityInterest = Column(Numeric)
    totalLiabilitiesAndTotalEquity = Column(Numeric)
    totalInvestments = Column(Numeric)
    totalDebt = Column(Numeric)
    netDebt = Column(Numeric)
    link = Column(String)
    finalLink = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='balance_sheets')

class CashFlowStatement(MarketBase):
    __tablename__ = 'cash_flow_statements'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    reportedCurrency = Column(String)
    cik = Column(String)
    fillingDate = Column(Date)
    acceptedDate = Column(Date)
    calendarYear = Column(Integer, index=True)
    period = Column(String)
    netIncome = Column(Numeric)
    depreciationAndAmortization = Column(Numeric)
    deferredIncomeTax = Column(Numeric)
    stockBasedCompensation = Column(Numeric)
    changeInWorkingCapital = Column(Numeric)
    accountsReceivables = Column(Numeric)
    inventory = Column(Numeric)
    accountsPayables = Column(Numeric)
    otherWorkingCapital = Column(Numeric)
    otherNonCashItems = Column(Numeric)
    netCashProvidedByOperatingActivities = Column(Numeric)
    investmentsInPropertyPlantAndEquipment = Column(Numeric)
    acquisitionsNet = Column(Numeric)
    purchasesOfInvestments = Column(Numeric)
    salesMaturitiesOfInvestments = Column(Numeric)
    otherInvestingActivites = Column(Numeric)
    netCashUsedForInvestingActivites = Column(Numeric)
    debtRepayment = Column(Numeric)
    commonStockIssued = Column(Numeric)
    commonStockRepurchased = Column(Numeric)
    dividendsPaid = Column(Numeric)
    otherFinancingActivites = Column(Numeric)
    netCashUsedProvidedByFinancingActivities = Column(Numeric)
    effectOfForexChangesOnCash = Column(Numeric)
    netChangeInCash = Column(Numeric)
    cashAtEndOfPeriod = Column(Numeric)
    cashAtBeginningOfPeriod = Column(Numeric)
    operatingCashFlow = Column(Numeric)
    capitalExpenditure = Column(Numeric)
    freeCashFlow = Column(Numeric)
    link = Column(String)
    finalLink = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='cash_flow_statements')

class IncomeStatement(MarketBase):
    __tablename__ = 'income_statements'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    reportedCurrency = Column(String)
    cik = Column(String)
    fillingDate = Column(Date)
    acceptedDate = Column(Date)
    calendarYear = Column(Integer, index=True)
    period = Column(String)
    revenue = Column(Numeric)
    costOfRevenue = Column(Numeric)
    grossProfit = Column(Numeric)
    grossProfitRatio = Column(Float)
    researchAndDevelopmentExpenses = Column(Numeric)
    generalAndAdministrativeExpenses = Column(Numeric)
    sellingAndMarketingExpenses = Column(Numeric)
    sellingGeneralAndAdministrativeExpenses = Column(Numeric)
    otherExpenses = Column(Numeric)
    operatingExpenses = Column(Numeric)
    costAndExpenses = Column(Numeric)
    interestIncome = Column(Numeric)
    interestExpense = Column(Numeric)
    depreciationAndAmortization = Column(Numeric)
    ebitda = Column(Numeric)
    ebitdaratio = Column(Float)
    operatingIncome = Column(Numeric)
    operatingIncomeRatio = Column(Float)
    totalOtherIncomeExpensesNet = Column(Numeric)
    incomeBeforeTax = Column(Numeric)
    incomeBeforeTaxRatio = Column(Float)
    incomeTaxExpense = Column(Numeric)
    netIncome = Column(Numeric)
    netIncomeRatio = Column(Float)
    eps = Column(Float)
    epsdiluted = Column(Float)
    weightedAverageShsOut = Column(Numeric)
    weightedAverageShsOutDil = Column(Numeric)
    link = Column(String)
    finalLink = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='income_statements')

class FinancialRatio(MarketBase):
    __tablename__ = 'financial_ratios'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    calendarYear = Column(Integer, index=True)
    period = Column(String)
    currentRatio = Column(Float)
    quickRatio = Column(Float)
    cashRatio = Column(Float)
    daysOfSalesOutstanding = Column(Float)
    daysOfInventoryOutstanding = Column(Float)
    operatingCycle = Column(Float)
    daysOfPayablesOutstanding = Column(Float)
    cashConversionCycle = Column(Float)
    grossProfitMargin = Column(Float)
    operatingProfitMargin = Column(Float)
    pretaxProfitMargin = Column(Float)
    netProfitMargin = Column(Float)
    effectiveTaxRate = Column(Float)
    returnOnAssets = Column(Float)
    returnOnEquity = Column(Float)
    returnOnCapitalEmployed = Column(Float)
    netIncomePerEBT = Column(Float)
    ebtPerEbit = Column(Float)
    ebitPerRevenue = Column(Float)
    debtRatio = Column(Float)
    debtEquityRatio = Column(Float)
    longTermDebtToCapitalization = Column(Float)
    totalDebtToCapitalization = Column(Float)
    interestCoverage = Column(Float)
    cashFlowToDebtRatio = Column(Float)
    companyEquityMultiplier = Column(Float)
    receivablesTurnover = Column(Float)
    payablesTurnover = Column(Float)
    inventoryTurnover = Column(Float)
    fixedAssetTurnover = Column(Float)
    assetTurnover = Column(Float)
    operatingCashFlowPerShare = Column(Float)
    freeCashFlowPerShare = Column(Float)
    cashPerShare = Column(Float)
    payoutRatio = Column(Float)
    operatingCashFlowSalesRatio = Column(Float)
    freeCashFlowOperatingCashFlowRatio = Column(Float)
    cashFlowCoverageRatios = Column(Float)
    shortTermCoverageRatios = Column(Float)
    capitalExpenditureCoverageRatio = Column(Float)
    dividendPaidAndCapexCoverageRatio = Column(Float)
    dividendPayoutRatio = Column(Float)
    priceBookValueRatio = Column(Float)
    priceToBookRatio = Column(Float)
    priceToSalesRatio = Column(Float)
    priceEarningsRatio = Column(Float)
    priceToFreeCashFlowsRatio = Column(Float)
    priceToOperatingCashFlowsRatio = Column(Float)
    priceCashFlowRatio = Column(Float)
    priceEarningsToGrowthRatio = Column(Float)
    priceSalesRatio = Column(Float)
    dividendYield = Column(Float)
    enterpriseValueMultiple = Column(Float)
    priceFairValue = Column(Float)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='financial_ratios')

class AnalystEstimate(MarketBase):
    __tablename__ = 'analyst_estimates'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    revenueLow = Column(Numeric)
    revenueHigh = Column(Numeric)
    revenueAvg = Column(Numeric)
    ebitdaLow = Column(Numeric)
    ebitdaHigh = Column(Numeric)
    ebitdaAvg = Column(Numeric)
    ebitLow = Column(Numeric)
    ebitHigh = Column(Numeric)
    ebitAvg = Column(Numeric)
    netIncomeLow = Column(Numeric)
    netIncomeHigh = Column(Numeric)
    netIncomeAvg = Column(Numeric)
    sgaExpenseLow = Column(Numeric)
    sgaExpenseHigh = Column(Numeric)
    sgaExpenseAvg = Column(Numeric)
    epsAvg = Column(Float)
    epsHigh = Column(Float)
    epsLow = Column(Float)
    numAnalystsRevenue = Column(Integer)
    numAnalystsEps = Column(Integer)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='analyst_estimates')

class ETFHolding(MarketBase):
    __tablename__ = 'etf_holdings'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    asset = Column(String, primary_key=True)
    name = Column(String)
    isin = Column(String)
    securityCusip = Column(String)
    sharesNumber = Column(Numeric)
    weightPercentage = Column(Float)
    marketValue = Column(Numeric)
    updatedAt = Column(DateTime)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='etf_holdings')

class ETFInfo(MarketBase):
    __tablename__ = 'etf_info'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True)
    name = Column(String)
    description = Column(Text)
    isin = Column(String)
    assetClass = Column(String)
    securityCusip = Column(String)
    domicile = Column(String)
    website = Column(String)
    etfCompany = Column(String)
    expenseRatio = Column(Float)
    assetsUnderManagement = Column(Numeric)
    avgVolume = Column(Integer)
    inceptionDate = Column(Date)
    nav = Column(Float)
    navCurrency = Column(String)
    holdingsCount = Column(Integer)
    updatedAt = Column(DateTime)
    sectorsList = Column(JSON)  # Using JSON type for list storage
    
    # Relationship
    ticker = relationship('Ticker', back_populates='etf_info')

class Dividend(MarketBase):
    __tablename__ = 'dividends'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    recordDate = Column(Date)
    paymentDate = Column(Date)
    declarationDate = Column(Date)
    adjDividend = Column(Float)
    dividend = Column(Float)
    yield_ = Column(Float, name='yield')  # 'yield' is a Python keyword
    frequency = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='dividends')

class EarningsTranscript(MarketBase):
    __tablename__ = 'earnings_transcript'
    __table_args__ = {'schema': 'fundamental_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    period = Column(String, primary_key=True)
    year = Column(Integer, primary_key=True)
    date = Column(Date, index=True)
    content = Column(Text)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='earnings_transcripts')

# =============================================================================
# PRICE DATA SCHEMA
# =============================================================================

class Price(MarketBase):
    __tablename__ = 'prices'
    __table_args__ = {'schema': 'price_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    datetime = Column(DateTime, primary_key=True, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='prices')

# =============================================================================
# NEWS DATA SCHEMA
# =============================================================================

class PressRelease(MarketBase):
    __tablename__ = 'press_releases'
    __table_args__ = {'schema': 'news_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    publishedDate = Column(DateTime, index=True)
    publisher = Column(String)
    title = Column(String)
    image = Column(String)
    site = Column(String)
    text = Column(Text)
    url = Column(String(512), primary_key=True)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='press_releases')

class StockNews(MarketBase):
    __tablename__ = 'stock_news'
    __table_args__ = {'schema': 'news_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    publishedDate = Column(DateTime, index=True)
    publisher = Column(String)
    title = Column(String)
    image = Column(String)
    site = Column(String)
    text = Column(Text)
    url = Column(String(512), primary_key=True)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='stock_news')

class PriceTargetNews(MarketBase):
    __tablename__ = 'price_target_news'
    __table_args__ = {'schema': 'news_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    publishedDate = Column(DateTime, index=True)
    newsURL = Column(String(512), primary_key=True)
    newsTitle = Column(String)
    analystName = Column(String)
    priceTarget = Column(Float)
    adjPriceTarget = Column(Float)
    priceWhenPosted = Column(Float)
    newsPublisher = Column(String)
    newsBaseURL = Column(String)
    analystCompany = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='price_target_news')

class StockGradeNews(MarketBase):
    __tablename__ = 'stock_grade_news'
    __table_args__ = {'schema': 'news_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    publishedDate = Column(DateTime, index=True)
    newsURL = Column(String(512), primary_key=True)
    newsTitle = Column(String)
    newsBaseURL = Column(String)
    newsPublisher = Column(String)
    newGrade = Column(String)
    previousGrade = Column(String)
    gradingCompany = Column(String)
    action = Column(String)
    priceWhenPosted = Column(Float)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='stock_grade_news')

class GeneralNews(MarketBase):
    __tablename__ = 'general_news'
    __table_args__ = {'schema': 'news_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    publishedDate = Column(DateTime, index=True)
    publisher = Column(String)
    title = Column(String)
    image = Column(String)
    site = Column(String)
    text = Column(Text)
    url = Column(String(512), primary_key=True)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='general_news')

# =============================================================================
# GRADES AND RATINGS DATA SCHEMA
# =============================================================================

class StockGradesIndividual(MarketBase):
    __tablename__ = 'stock_grades_individual'
    __table_args__ = {'schema': 'grades_and_ratings_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    gradingCompany = Column(String, primary_key=True)
    previousGrade = Column(String)
    newGrade = Column(String)
    action = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='stock_grades_individual')

class StockGradesSummary(MarketBase):
    __tablename__ = 'stock_grades_summary'
    __table_args__ = {'schema': 'grades_and_ratings_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    analystRatingsStrongBuy = Column(Integer)
    analystRatingsBuy = Column(Integer)
    analystRatingsHold = Column(Integer)
    analystRatingsSell = Column(Integer)
    analystRatingsStrongSell = Column(Integer)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='stock_grades_summary')

class Rating(MarketBase):
    __tablename__ = 'rating_scores'
    __table_args__ = {'schema': 'grades_and_ratings_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    rating = Column(String)
    overallScore = Column(Float)
    discountedCashFlowScore = Column(Float)
    returnOnEquityScore = Column(Float)
    returnOnAssetsScore = Column(Float)
    debtToEquityScore = Column(Float)
    priceToEarningsScore = Column(Float)
    priceToBookScore = Column(Float)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='rating_scores')

class AnalystRecommendation(MarketBase):
    __tablename__ = 'analyst_recommendations'
    __table_args__ = {'schema': 'grades_and_ratings_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    date = Column(Date, primary_key=True, index=True)
    rating = Column(String)
    ratingScore = Column(Float)
    ratingRecommendation = Column(String)
    ratingDetailsDCFScore = Column(Float)
    ratingDetailsDCFRecommendation = Column(String)
    ratingDetailsROEScore = Column(Float)
    ratingDetailsROERecommendation = Column(String)
    ratingDetailsROAScore = Column(Float)
    ratingDetailsROARecommendation = Column(String)
    ratingDetailsDEScore = Column(Float)
    ratingDetailsDERecommendation = Column(String)
    ratingDetailsPEScore = Column(Float)
    ratingDetailsPERecommendation = Column(String)
    ratingDetailsPBScore = Column(Float)
    ratingDetailsPBRecommendation = Column(String)
    
    # Relationship
    ticker = relationship('Ticker', back_populates='analyst_recommendations')

class PriceTargetSummary(MarketBase):
    __tablename__ = 'price_target_summary'
    __table_args__ = {'schema': 'grades_and_ratings_data'}
    
    ticker_id = Column(UUID(as_uuid=True), ForeignKey('ticker_universe.tickers.id'), primary_key=True, index=True)
    lastMonthCount = Column(Integer)
    lastMonthAvgPriceTarget = Column(Float)
    lastQuarterCount = Column(Integer)
    lastQuarterAvgPriceTarget = Column(Float)
    lastYearCount = Column(Integer)
    lastYearAvgPriceTarget = Column(Float)
    allTimeCount = Column(Integer)
    allTimeAvgPriceTarget = Column(Float)
    publishers = Column(JSON)  # Storing as JSON array
    
    # Relationship
    ticker = relationship('Ticker', back_populates='price_target_summary')