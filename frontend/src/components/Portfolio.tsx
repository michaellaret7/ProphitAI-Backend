import React, { useState, useEffect } from 'react';
import './Portfolio.css';
import appleLogo from '../assets/logos/icons8-apple-logo-48.png';
import googleLogo from '../assets/logos/icons8-google-logo-48.png';

// Define the Holding interface based on the backend model and frontend needs
interface Holding {
  symbol: string;
  name?: string; // Name might not come from the DB, so it's optional
  quantity: number;
  currentPrice: number;
  marketValue: number;
  pnl: number;
  pnlPercent: number;
  portfolioPercent: number;
  analystSentiment?: string; // Analyst sentiment might not come from the DB
}

const Portfolio: React.FC = () => {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Hardcoded user_name for now, this could come from auth context or props
  const userName = "test_user_beta_two"; 

  useEffect(() => {
    const fetchHoldings = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`http://localhost:8000/api/portfolio/holdings/${userName}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        const data: { holdings: Holding[] } = await response.json();
        
        // Map backend data to frontend Holding interface, adding placeholders if needed
        const fetchedHoldings = data.holdings.map(h => ({
          ...h,
          name: h.symbol, // Placeholder for name, can be enriched later
          analystSentiment: 'N/A' // Placeholder for analyst sentiment
        }));        
        setHoldings(fetchedHoldings);

      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unknown error occurred while fetching holdings.');
        }
        console.error("Failed to fetch holdings:", err);
        setHoldings([]); // Set to empty array on error
      } finally {
        setIsLoading(false);
      }
    };

    fetchHoldings();
  }, [userName]); // Re-fetch if userName changes

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
            <p className="summary-value">{isLoading ? '-' : holdings.length}</p>
            <span className="summary-change positive"></span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">💰</div>
          <div className="summary-content">
            <h3>Total Value</h3>
            <p className="summary-value">
              {isLoading ? '-' : 
                `$${holdings.reduce((acc, h) => acc + h.marketValue, 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              }
            </p>
            <span className="summary-change positive"></span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">📈</div>
          <div className="summary-content">
            <h3>Today's P&L</h3>
            <p className="summary-value positive">N/A</p>
            <span className="summary-change"></span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">🎯</div>
          <div className="summary-content">
            <h3>Best Performer</h3>
            <p className="summary-value">N/A</p>
            <span className="summary-change positive"></span>
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
                  <td>{holding.name || holding.symbol}</td>
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
                        color: getSentimentColor(holding.analystSentiment || 'neutral'),
                        fontWeight: '600',
                        fontSize: '0.875rem'
                      }}
                    >
                      {formatSentiment(holding.analystSentiment || 'N/A')}
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

        {isLoading && <div className="loading-message">Loading holdings...</div>}
        {error && <div className="error-message">Error fetching holdings: {error}</div>}
        {!isLoading && !error && holdings.length === 0 && <div className="info-message">No holdings found for this user.</div>}
      </section>
    </div>
  );
};

export default Portfolio; 