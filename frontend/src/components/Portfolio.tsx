import React, { useState } from 'react';
import './Portfolio.css';

// Define interfaces for different asset types
interface CashHolding {
  type: string;
  amount: number;
}

interface EquityHolding {
  symbol: string;
  company: string;
  shares: number;
  price: number;
  change1D: number;
  change1M: number;
  changeYTD: number;
  pe: number;
  fwdPE: number;
  evSales: number;
  dividend: number;
  pnl: number;
  taxNote: string;
}

interface ETFHolding {
  symbol: string;
  name: string;
  shares: number;
  nav: number;
  premiumDiscount: number;
  change1D: number;
  change1M: number;
  changeYTD: number;
  dividend: number;
  volatility: number;
  pnl: number;
  taxNote: string;
}

interface FixedIncomeHolding {
  bond: string;
  faceValue: number;
  price: number;
  yield: number;
  coupon: number;
  maturity: string;
  rating: string;
  sector: string;
  callable: boolean;
  accruedInt: number;
  totalReturn: number;
}

interface CommodityETF {
  symbol: string;
  name: string;
  shares: number;
  price: number;
  change1D: number;
  change1M: number;
  changeYTD: number;
  volatility: number;
  pnl: number;
}

interface FuturesContract {
  contract: string;
  contracts: number;
  price: number;
  change1D: number;
  change1M: number;
  changeYTD: number;
  contractMonth: string;
  lastRoll: string;
  openInterest: number;
  volume: number;
  margin: number;
  pnl: number;
}

interface AlternativeInvestment {
  fundName: string;
  type: string;
  investment: number;
  nav: number;
  return1M: number;
  cagr: number;
  volatility: number;
  sharpe: number;
  maxDD: number;
  alpha: number;
  beta: number;
  upDownCapture: string;
  sortino: number;
}

const Portfolio: React.FC = () => {
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({
    cash: true,
    equities: true,
    etfs: true,
    fixedIncome: true,
    commodities: true,
    forex: true,
    alternatives: true
  });

  // Mock data for demonstration
  const cashData: CashHolding = {
    type: "Available Cash",
    amount: 76435
  };

  const equityData: EquityHolding[] = [
    {
      symbol: "AAPL",
      company: "Apple Inc.",
      shares: 150,
      price: 185.42,
      change1D: 1.24,
      change1M: 5.67,
      changeYTD: 12.34,
      pe: 28.5,
      fwdPE: 24.2,
      evSales: 7.6,
      dividend: 0.52,
      pnl: 4235,
      taxNote: "Short-term gain"
    },
    {
      symbol: "MSFT",
      company: "Microsoft Corp.",
      shares: 120,
      price: 412.73,
      change1D: -0.87,
      change1M: 3.21,
      changeYTD: 18.56,
      pe: 32.1,
      fwdPE: 28.7,
      evSales: 12.4,
      dividend: 0.68,
      pnl: 8923,
      taxNote: "Long-term gain"
    },
    {
      symbol: "GOOGL",
      company: "Alphabet Inc.",
      shares: 80,
      price: 168.92,
      change1D: -0.43,
      change1M: 2.15,
      changeYTD: 24.78,
      pe: 25.3,
      fwdPE: 22.1,
      evSales: 4.9,
      dividend: 0.00,
      pnl: 3456,
      taxNote: "Consider harvesting"
    },
    {
      symbol: "NVDA",
      company: "NVIDIA Corp.",
      shares: 60,
      price: 875.28,
      change1D: 2.15,
      change1M: 8.94,
      changeYTD: 198.45,
      pe: 71.2,
      fwdPE: 48.5,
      evSales: 22.1,
      dividend: 0.03,
      pnl: 28945,
      taxNote: "Wait 3 months"
    },
    {
      symbol: "TSLA",
      company: "Tesla Inc.",
      shares: 100,
      price: 248.73,
      change1D: -1.87,
      change1M: -3.45,
      changeYTD: -15.23,
      pe: 78.4,
      fwdPE: 65.2,
      evSales: 8.9,
      dividend: 0.00,
      pnl: -5234,
      taxNote: "Tax loss harvest"
    },
    {
      symbol: "JPM",
      company: "JPMorgan Chase",
      shares: 75,
      price: 195.46,
      change1D: 0.52,
      change1M: 4.23,
      changeYTD: 32.18,
      pe: 12.8,
      fwdPE: 11.5,
      evSales: 3.2,
      dividend: 2.15,
      pnl: 4567,
      taxNote: "Long-term gain"
    }
  ];

  const etfData: ETFHolding[] = [
    {
      symbol: "SPY",
      name: "SPDR S&P 500 ETF",
      shares: 200,
      nav: 498.73,
      premiumDiscount: -0.02,
      change1D: 0.88,
      change1M: 2.41,
      changeYTD: 11.67,
      dividend: 1.28,
      volatility: 12.4,
      pnl: 12456,
      taxNote: "Long-term gain"
    },
    {
      symbol: "VTI",
      name: "Vanguard Total Stock",
      shares: 150,
      nav: 267.89,
      premiumDiscount: 0.01,
      change1D: 0.92,
      change1M: 2.78,
      changeYTD: 13.24,
      dividend: 1.31,
      volatility: 11.8,
      pnl: 8734,
      taxNote: "Long-term gain"
    },
    {
      symbol: "QQQ",
      name: "Invesco QQQ Trust",
      shares: 100,
      nav: 435.67,
      premiumDiscount: -0.01,
      change1D: 1.23,
      change1M: 4.56,
      changeYTD: 22.89,
      dividend: 0.51,
      volatility: 16.2,
      pnl: 9876,
      taxNote: "Short-term gain"
    },
    {
      symbol: "IQD",
      name: "iShares Corporate Bond",
      shares: 300,
      nav: 112.45,
      premiumDiscount: 0.02,
      change1D: 0.15,
      change1M: 0.87,
      changeYTD: 4.23,
      dividend: 3.45,
      volatility: 6.8,
      pnl: 2345,
      taxNote: "Long-term gain"
    },
    {
      symbol: "GLD",
      name: "SPDR Gold Trust",
      shares: 50,
      nav: 195.23,
      premiumDiscount: -0.01,
      change1D: -0.43,
      change1M: -1.23,
      changeYTD: 8.45,
      dividend: 0.00,
      volatility: 18.5,
      pnl: 1234,
      taxNote: "Long-term gain"
    }
  ];

  const fixedIncomeData: FixedIncomeHolding[] = [
    {
      bond: "US Treasury 10Y",
      faceValue: 50000,
      price: 46750,
      yield: 4.35,
      coupon: 4.25,
      maturity: "2034-05-15",
      rating: "AAA",
      sector: "Treasury",
      callable: false,
      accruedInt: 456,
      totalReturn: 2.45
    },
    {
      bond: "Verizon Bond",
      faceValue: 25000,
      price: 24125,
      yield: 5.12,
      coupon: 4.875,
      maturity: "2028-08-21",
      rating: "BBB+",
      sector: "Telecom",
      callable: true,
      accruedInt: 203,
      totalReturn: 1.23
    },
    {
      bond: "JPM Corporate",
      faceValue: 30000,
      price: 29450,
      yield: 4.89,
      coupon: 4.75,
      maturity: "2029-01-23",
      rating: "A-",
      sector: "Financial",
      callable: false,
      accruedInt: 298,
      totalReturn: 3.67
    }
  ];

  const commodityETFs: CommodityETF[] = [
    {
      symbol: "GLD",
      name: "SPDR Gold Trust",
      shares: 50,
      price: 195.23,
      change1D: -0.43,
      change1M: -1.23,
      changeYTD: 8.45,
      volatility: 18.5,
      pnl: 1234
    }
  ];

  const futuresContracts: FuturesContract[] = [
    {
      contract: "CLU5",
      contracts: 2,
      price: 73.45,
      change1D: 1.23,
      change1M: 3.45,
      changeYTD: 12.34,
      contractMonth: "Sep 2025",
      lastRoll: "2025-06-01",
      openInterest: 234567,
      volume: 45678,
      margin: 8500,
      pnl: 2890
    }
  ];

  const alternativeData: AlternativeInvestment[] = [
    {
      fundName: "Millennium LP",
      type: "Hedge Fund",
      investment: 500000,
      nav: 547325,
      return1M: 1.45,
      cagr: 12.8,
      volatility: 8.4,
      sharpe: 1.52,
      maxDD: -4.2,
      alpha: 4.2,
      beta: 0.31,
      upDownCapture: "105%/45%",
      sortino: 2.14
    },
    {
      fundName: "Citadel LP",
      type: "Hedge Fund",
      investment: 750000,
      nav: 823450,
      return1M: 0.87,
      cagr: 15.2,
      volatility: 6.8,
      sharpe: 2.24,
      maxDD: -2.8,
      alpha: 6.8,
      beta: 0.28,
      upDownCapture: "112%/38%",
      sortino: 2.87
    },
    {
      fundName: "Albemarle Shipping Fund LP",
      type: "Hedge Fund",
      investment: 250000,
      nav: 267890,
      return1M: 2.34,
      cagr: 18.9,
      volatility: 22.4,
      sharpe: 0.84,
      maxDD: -15.6,
      alpha: 8.9,
      beta: 0.45,
      upDownCapture: "89%/78%",
      sortino: 1.23
    },
    {
      fundName: "Neural Labs",
      type: "Private Equity",
      investment: 200000,
      nav: 289500,
      return1M: 0,
      cagr: 31.2,
      volatility: 0,
      sharpe: 0,
      maxDD: 0,
      alpha: 0,
      beta: 0,
      upDownCapture: "N/A",
      sortino: 0
    },
    {
      fundName: "SmartWires LLC",
      type: "Private Equity",
      investment: 150000,
      nav: 178650,
      return1M: 0,
      cagr: 24.7,
      volatility: 0,
      sharpe: 0,
      maxDD: 0,
      alpha: 0,
      beta: 0,
      upDownCapture: "N/A",
      sortino: 0
    }
  ];

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${value.toFixed(2)}%`;
  };

  return (
    <div className="portfolio-container">
      <section className="portfolio-header">
        <h1 className="portfolio-title">Portfolio Overview</h1>
        <p className="portfolio-subtitle">Comprehensive view of your investment holdings across all asset classes</p>
      </section>

      {/* Portfolio Summary Cards */}
      <section className="portfolio-summary">
        <div className="summary-card">
          <div className="summary-icon">📊</div>
          <div className="summary-content">
            <h3>Total Portfolio Value</h3>
            <p className="summary-value">$3,245,678</p>
            <span className="summary-change positive">+$45,234 (+1.41%)</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">💰</div>
          <div className="summary-content">
            <h3>Cash & Equivalents</h3>
            <p className="summary-value">{formatCurrency(cashData.amount)}</p>
            <span className="summary-change">2.35% of portfolio</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">📈</div>
          <div className="summary-content">
            <h3>Today's P&L</h3>
            <p className="summary-value positive">+$12,456</p>
            <span className="summary-change positive">+0.38%</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">🎯</div>
          <div className="summary-content">
            <h3>YTD Performance</h3>
            <p className="summary-value positive">+18.76%</p>
            <span className="summary-change">vs S&P +11.67%</span>
          </div>
        </div>
      </section>

      {/* Cash & Cash Equivalents Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('cash')}>
          <div className="section-title">
            <span className="section-icon">💵</span>
            <h2>Cash & Cash Equivalents</h2>
          </div>
          <span className={`expand-icon ${expandedSections.cash ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.cash && (
          <div className="cash-content">
            <div className="cash-item">
              <span className="cash-label">{cashData.type}</span>
              <span className="cash-amount">{formatCurrency(cashData.amount)}</span>
            </div>
          </div>
        )}
      </section>

      {/* Equities Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('equities')}>
          <div className="section-title">
            <span className="section-icon">📊</span>
            <h2>Equities</h2>
          </div>
          <span className={`expand-icon ${expandedSections.equities ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.equities && (
          <div className="table-container">
            <table className="asset-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Company</th>
                  <th>Shares</th>
                  <th>Price</th>
                  <th>1D %</th>
                  <th>1M %</th>
                  <th>YTD %</th>
                  <th>P/E</th>
                  <th>Fwd P/E</th>
                  <th>EV/Sales</th>
                  <th>Dividend</th>
                  <th>P&L</th>
                  <th>Tax Note</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {equityData.map((equity) => (
                  <tr key={equity.symbol}>
                    <td className="symbol-cell">{equity.symbol}</td>
                    <td>{equity.company}</td>
                    <td>{equity.shares}</td>
                    <td>${equity.price.toFixed(2)}</td>
                    <td className={equity.change1D >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(equity.change1D)}
                    </td>
                    <td className={equity.change1M >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(equity.change1M)}
                    </td>
                    <td className={equity.changeYTD >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(equity.changeYTD)}
                    </td>
                    <td>{equity.pe.toFixed(1)}x</td>
                    <td>{equity.fwdPE.toFixed(1)}x</td>
                    <td>{equity.evSales.toFixed(1)}</td>
                    <td>{equity.dividend.toFixed(2)}%</td>
                    <td className={equity.pnl >= 0 ? 'positive' : 'negative'}>
                      {formatCurrency(equity.pnl)}
                    </td>
                    <td className="tax-note">{equity.taxNote}</td>
                    <td>
                      <button className="action-btn">Details</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Exchange-Traded Funds Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('etfs')}>
          <div className="section-title">
            <span className="section-icon">📈</span>
            <h2>Exchange-Traded Funds</h2>
          </div>
          <span className={`expand-icon ${expandedSections.etfs ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.etfs && (
          <div className="table-container">
            <table className="asset-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                  <th>Shares</th>
                  <th>NAV</th>
                  <th>Premium/Discount</th>
                  <th>1D %</th>
                  <th>1M %</th>
                  <th>YTD %</th>
                  <th>Dividend</th>
                  <th>Volatility</th>
                <th>P&L</th>
                  <th>Tax Note</th>
                  <th>Action</th>
              </tr>
            </thead>
            <tbody>
                {etfData.map((etf) => (
                  <tr key={etf.symbol}>
                    <td className="symbol-cell">{etf.symbol}</td>
                    <td>{etf.name}</td>
                    <td>{etf.shares}</td>
                    <td>${etf.nav.toFixed(2)}</td>
                    <td className={etf.premiumDiscount >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(etf.premiumDiscount)}
                    </td>
                    <td className={etf.change1D >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(etf.change1D)}
                    </td>
                    <td className={etf.change1M >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(etf.change1M)}
                  </td>
                    <td className={etf.changeYTD >= 0 ? 'positive' : 'negative'}>
                      {formatPercent(etf.changeYTD)}
                  </td>
                    <td>{etf.dividend.toFixed(2)}%</td>
                    <td>{etf.volatility.toFixed(1)}%</td>
                    <td className={etf.pnl >= 0 ? 'positive' : 'negative'}>
                      {formatCurrency(etf.pnl)}
                  </td>
                    <td className="tax-note">{etf.taxNote}</td>
                  <td>
                      <button className="action-btn">Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </section>

      {/* Fixed Income Securities Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('fixedIncome')}>
          <div className="section-title">
            <span className="section-icon">🏦</span>
            <h2>Fixed Income Securities</h2>
          </div>
          <span className={`expand-icon ${expandedSections.fixedIncome ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.fixedIncome && (
          <div className="table-container">
            <table className="asset-table">
              <thead>
                <tr>
                  <th>Bond</th>
                  <th>Face Value</th>
                  <th>Price</th>
                  <th>Yield</th>
                  <th>Coupon</th>
                  <th>Maturity</th>
                  <th>Rating</th>
                  <th>Sector</th>
                  <th>Callable</th>
                  <th>Accrued Int.</th>
                  <th>Total Return</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {fixedIncomeData.map((bond) => (
                  <tr key={bond.bond}>
                    <td className="symbol-cell">{bond.bond}</td>
                    <td>{formatCurrency(bond.faceValue)}</td>
                    <td>{formatCurrency(bond.price)}</td>
                    <td>{bond.yield.toFixed(2)}%</td>
                    <td>{bond.coupon.toFixed(3)}%</td>
                    <td>{bond.maturity}</td>
                    <td className="rating">{bond.rating}</td>
                    <td>{bond.sector}</td>
                    <td>{bond.callable ? 'Yes' : 'No'}</td>
                    <td>${bond.accruedInt}</td>
                    <td className="positive">{formatPercent(bond.totalReturn)}</td>
                    <td>
                      <button className="action-btn">Details</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Commodities Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('commodities')}>
          <div className="section-title">
            <span className="section-icon">🛢️</span>
            <h2>Commodities</h2>
          </div>
          <span className={`expand-icon ${expandedSections.commodities ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.commodities && (
          <div className="commodities-container">
            <h3 className="subsection-title">Commodity ETFs</h3>
            <div className="table-container">
              <table className="asset-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th>Shares</th>
                    <th>Price</th>
                    <th>1D %</th>
                    <th>1M %</th>
                    <th>YTD %</th>
                    <th>Volatility</th>
                    <th>P&L</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {commodityETFs.map((etf) => (
                    <tr key={etf.symbol}>
                      <td className="symbol-cell">{etf.symbol}</td>
                      <td>{etf.name}</td>
                      <td>{etf.shares}</td>
                      <td>${etf.price.toFixed(2)}</td>
                      <td className={etf.change1D >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(etf.change1D)}
                      </td>
                      <td className={etf.change1M >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(etf.change1M)}
                      </td>
                      <td className={etf.changeYTD >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(etf.changeYTD)}
                      </td>
                      <td>{etf.volatility.toFixed(1)}%</td>
                      <td className={etf.pnl >= 0 ? 'positive' : 'negative'}>
                        {formatCurrency(etf.pnl)}
                      </td>
                      <td>
                        <button className="action-btn">Details</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3 className="subsection-title">Futures Contracts</h3>
            <div className="table-container">
              <table className="asset-table">
                <thead>
                  <tr>
                    <th>Contract</th>
                    <th>Contracts</th>
                    <th>Price</th>
                    <th>1D %</th>
                    <th>1M %</th>
                    <th>YTD %</th>
                    <th>Contract Month</th>
                    <th>Last Roll</th>
                    <th>Open Interest</th>
                    <th>Volume (30D)</th>
                    <th>Margin</th>
                    <th>P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {futuresContracts.map((contract) => (
                    <tr key={contract.contract}>
                      <td className="symbol-cell">{contract.contract}</td>
                      <td>{contract.contracts}</td>
                      <td>${contract.price.toFixed(2)}</td>
                      <td className={contract.change1D >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(contract.change1D)}
                      </td>
                      <td className={contract.change1M >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(contract.change1M)}
                      </td>
                      <td className={contract.changeYTD >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(contract.changeYTD)}
                      </td>
                      <td>{contract.contractMonth}</td>
                      <td>{contract.lastRoll}</td>
                      <td>{contract.openInterest.toLocaleString()}</td>
                      <td>{contract.volume.toLocaleString()}</td>
                      <td>${contract.margin.toLocaleString()}</td>
                      <td className={contract.pnl >= 0 ? 'positive' : 'negative'}>
                        {formatCurrency(contract.pnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* Foreign Exchange Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('forex')}>
          <div className="section-title">
            <span className="section-icon">💱</span>
            <h2>Foreign Exchange</h2>
          </div>
          <span className={`expand-icon ${expandedSections.forex ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.forex && (
          <div className="forex-content">
            <div className="no-positions">
              <h3>No FX Positions</h3>
              <p>Your portfolio currently has no foreign exchange positions.</p>
            </div>
          </div>
        )}
      </section>

      {/* Alternative Investments Section */}
      <section className="asset-section">
        <div className="section-header" onClick={() => toggleSection('alternatives')}>
          <div className="section-title">
            <span className="section-icon">🏗️</span>
            <h2>Alternative Investments</h2>
          </div>
          <span className={`expand-icon ${expandedSections.alternatives ? 'expanded' : ''}`}>▼</span>
        </div>
        {expandedSections.alternatives && (
          <div className="table-container">
            <table className="asset-table">
              <thead>
                <tr>
                  <th>Fund Name</th>
                  <th>Type</th>
                  <th>Investment</th>
                  <th>NAV</th>
                  <th>1M Return</th>
                  <th>CAGR</th>
                  <th>Volatility</th>
                  <th>Sharpe</th>
                  <th>Max DD</th>
                  <th>Alpha</th>
                  <th>Beta</th>
                  <th>Up/Down Capture</th>
                  <th>Sortino</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {alternativeData.map((fund) => (
                  <tr key={fund.fundName}>
                    <td className="symbol-cell">{fund.fundName}</td>
                    <td>{fund.type}</td>
                    <td>{formatCurrency(fund.investment)}</td>
                    <td>{formatCurrency(fund.nav)}</td>
                    <td className={fund.return1M >= 0 ? 'positive' : 'negative'}>
                      {fund.return1M ? formatPercent(fund.return1M) : 'N/A'}
                    </td>
                    <td className="positive">{fund.cagr ? formatPercent(fund.cagr) : 'N/A'}</td>
                    <td>{fund.volatility ? `${fund.volatility.toFixed(1)}%` : 'N/A'}</td>
                    <td>{fund.sharpe ? fund.sharpe.toFixed(2) : 'N/A'}</td>
                    <td className="negative">{fund.maxDD ? `${fund.maxDD.toFixed(1)}%` : 'N/A'}</td>
                    <td className="positive">{fund.alpha ? formatPercent(fund.alpha) : 'N/A'}</td>
                    <td>{fund.beta ? fund.beta.toFixed(2) : 'N/A'}</td>
                    <td>{fund.upDownCapture}</td>
                    <td>{fund.sortino ? fund.sortino.toFixed(2) : 'N/A'}</td>
                    <td>
                      <button className="action-btn">Details</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Portfolio; 