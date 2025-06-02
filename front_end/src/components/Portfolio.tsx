import React from 'react';
import './Portfolio.css';
import appleLogo from '../assets/logos/icons8-apple-logo-48.png';
import googleLogo from '../assets/logos/icons8-google-logo-48.png';

const Portfolio: React.FC = () => {
  // Holdings data with analyst sentiment
  const holdings = [
    {
      symbol: 'AAPL',
      name: 'Apple Inc.',
      quantity: 100,
      currentPrice: 189.95,
      marketValue: 18995.00,
      pnl: 3995.00,
      pnlPercent: 26.63,
      portfolioPercent: 15.24,
      analystSentiment: 'overweight'
    },
    {
      symbol: 'MSFT',
      name: 'Microsoft Corp.',
      quantity: 50,
      currentPrice: 423.85,
      marketValue: 21192.50,
      pnl: 5692.50,
      pnlPercent: 36.73,
      portfolioPercent: 17.01,
      analystSentiment: 'strong buy'
    },
    {
      symbol: 'GOOGL',
      name: 'Alphabet Inc.',
      quantity: 30,
      currentPrice: 175.94,
      marketValue: 5278.20,
      pnl: 1528.20,
      pnlPercent: 40.75,
      portfolioPercent: 4.24,
      analystSentiment: 'overweight'
    },
    {
      symbol: 'AMZN',
      name: 'Amazon.com Inc.',
      quantity: 25,
      currentPrice: 178.35,
      marketValue: 4458.75,
      pnl: 958.75,
      pnlPercent: 27.39,
      portfolioPercent: 3.58,
      analystSentiment: 'neutral'
    },
    {
      symbol: 'NVDA',
      name: 'NVIDIA Corp.',
      quantity: 40,
      currentPrice: 495.22,
      marketValue: 19808.80,
      pnl: 8808.80,
      pnlPercent: 80.12,
      portfolioPercent: 15.90,
      analystSentiment: 'strong buy'
    },
    {
      symbol: 'SPY',
      name: 'SPDR S&P 500 ETF',
      quantity: 20,
      currentPrice: 452.16,
      marketValue: 9043.20,
      pnl: 1243.20,
      pnlPercent: 15.94,
      portfolioPercent: 7.26,
      analystSentiment: 'overweight'
    },
    {
      symbol: 'QQQ',
      name: 'Invesco QQQ Trust',
      quantity: 15,
      currentPrice: 391.56,
      marketValue: 5873.40,
      pnl: 873.40,
      pnlPercent: 17.47,
      portfolioPercent: 4.71,
      analystSentiment: 'neutral'
    },
    {
      symbol: 'VTI',
      name: 'Vanguard Total Stock Market ETF',
      quantity: 30,
      currentPrice: 235.48,
      marketValue: 7064.40,
      pnl: 564.40,
      pnlPercent: 8.69,
      portfolioPercent: 5.67,
      analystSentiment: 'overweight'
    },
    {
      symbol: 'TSLA',
      name: 'Tesla Inc.',
      quantity: 10,
      currentPrice: 238.83,
      marketValue: 2388.30,
      pnl: -311.70,
      pnlPercent: -11.54,
      portfolioPercent: 1.92,
      analystSentiment: 'underweight'
    },
    {
      symbol: 'META',
      name: 'Meta Platforms Inc.',
      quantity: 35,
      currentPrice: 352.08,
      marketValue: 12322.80,
      pnl: 2822.80,
      pnlPercent: 29.71,
      portfolioPercent: 9.89,
      analystSentiment: 'overweight'
    },
    {
      symbol: 'BRK.B',
      name: 'Berkshire Hathaway',
      quantity: 20,
      currentPrice: 368.90,
      marketValue: 7378.00,
      pnl: 378.00,
      pnlPercent: 5.40,
      portfolioPercent: 5.92,
      analystSentiment: 'neutral'
    },
    {
      symbol: 'GE',
      name: 'General Electric Co.',
      quantity: 50,
      currentPrice: 115.23,
      marketValue: 5761.50,
      pnl: -438.50,
      pnlPercent: -7.07,
      portfolioPercent: 4.62,
      analystSentiment: 'strong sell'
    }
  ];

  // Function to get sentiment color
  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'strong sell':
        return '#8B0000'; // Dark red
      case 'underweight':
        return '#DC143C'; // Crimson
      case 'neutral':
        return '#FFA500'; // Orange
      case 'overweight':
        return '#90EE90'; // Light green
      case 'strong buy':
        return '#228B22'; // Forest green
      default:
        return '#808080'; // Gray
    }
  };

  // Function to format sentiment text
  const formatSentiment = (sentiment: string) => {
    return sentiment.split(' ').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  // Function to get logo for ticker
  const getLogoUrl = (symbol: string) => {
    switch (symbol) {
      case 'AAPL':
        return appleLogo;
      case 'GOOGL':
        return googleLogo;
      default:
        return `https://logo.clearbit.com/${symbol.toLowerCase()}.com`;
    }
  };

  return (
    <div className="portfolio-container">
      <section className="portfolio-header">
        <h1 className="portfolio-title">Portfolio Overview</h1>
        <p className="portfolio-subtitle">Manage and analyze your investment holdings</p>
      </section>

      {/* Portfolio Summary Cards */}
      <section className="portfolio-summary">
        <div className="summary-card">
          <div className="summary-icon">📊</div>
          <div className="summary-content">
            <h3>Total Holdings</h3>
            <p className="summary-value">24</p>
            <span className="summary-change positive">+2 this month</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">💰</div>
          <div className="summary-content">
            <h3>Total Value</h3>
            <p className="summary-value">$124,613.20</p>
            <span className="summary-change positive">+$1,245.31 (+1.01%)</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">📈</div>
          <div className="summary-content">
            <h3>Today's P&L</h3>
            <p className="summary-value positive">+$45.31</p>
            <span className="summary-change">+0.04%</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">🎯</div>
          <div className="summary-content">
            <h3>Best Performer</h3>
            <p className="summary-value">NVDA</p>
            <span className="summary-change positive">+12.5% today</span>
          </div>
        </div>
      </section>

      {/* Holdings Table */}
      <section className="holdings-section">
        <div className="holdings-header">
          <h2>Holdings</h2>
          <div className="holdings-actions">
            <button className="btn-filter">Filter</button>
            <button className="btn-sort">Sort</button>
            <button className="btn-export">Export</button>
          </div>
        </div>

        <div className="holdings-table">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Quantity</th>
                <th>Current Price</th>
                <th>Market Value</th>
                <th>P&L</th>
                <th>% of Portfolio</th>
                <th>Analyst Sentiment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.symbol}>
                  <td className="symbol">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <img 
                        src={getLogoUrl(holding.symbol)} 
                        alt={`${holding.symbol} logo`}
                        style={{ width: '24px', height: '24px', borderRadius: '4px' }}
                        onError={(e) => {
                          e.currentTarget.src = `https://ui-avatars.com/api/?name=${holding.symbol}&background=5b4cdb&color=fff&size=24`;
                        }}
                      />
                      {holding.symbol}
                    </div>
                  </td>
                  <td>{holding.name}</td>
                  <td>{holding.quantity}</td>
                  <td>${holding.currentPrice.toFixed(2)}</td>
                  <td>${holding.marketValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className={holding.pnl >= 0 ? 'positive' : 'negative'}>
                    {holding.pnl >= 0 ? '+' : ''}${holding.pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({holding.pnl >= 0 ? '+' : ''}{holding.pnlPercent.toFixed(2)}%)
                  </td>
                  <td>{holding.portfolioPercent.toFixed(2)}%</td>
                  <td>
                    <span 
                      style={{ 
                        color: getSentimentColor(holding.analystSentiment),
                        fontWeight: '600',
                        fontSize: '0.875rem'
                      }}
                    >
                      {formatSentiment(holding.analystSentiment)}
                    </span>
                  </td>
                  <td>
                    <button className="btn-action">•••</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default Portfolio; 