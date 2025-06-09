import React from 'react';
import './ProphitAlts.css';
import birdLogo from '../assets/bird_logo.png';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChartLine, faArrowUp, faArrowDown, faInfoCircle } from '@fortawesome/free-solid-svg-icons';

interface AltPortfolio {
  id: string;
  fundName: string;
  strategy: string;
  description: string;
  sector: string;
  aum: string;
  inception: string;
  minInvestment: string;
  performance: {
    ytd: number;
    oneYear: number;
    threeYear: number;
    fiveYear: number;
    volatility: number;
    sharpeRatio: number;
  };
  riskLevel: 'Low' | 'Medium' | 'High';
  highlights: string[];
  topAssets: {
    ticker: string;
    name: string;
    return: number;
    position: 'Long' | 'Short';
  }[];
}

const ProphitAlts: React.FC = () => {
  const altPortfolios: AltPortfolio[] = [
    {
      id: 'prophitalts-healthcare',
      fundName: 'ProphitAlts Healthcare Long/Short Fund',
      strategy: 'Long/Short',
      description: 'A sophisticated long/short equity strategy focused exclusively on healthcare sector opportunities. The fund leverages deep sector expertise to identify mispriced securities across pharmaceuticals, biotech, medical devices, and healthcare services.',
      sector: 'Healthcare',
      aum: '$2.4B',
      inception: '2018',
      minInvestment: '$1,000,000',
      performance: {
        ytd: 18.7,
        oneYear: 22.3,
        threeYear: 19.8,
        fiveYear: 21.2,
        volatility: 12.4,
        sharpeRatio: 1.82
      },
      riskLevel: 'Medium',
      highlights: [
        'Proprietary biotech valuation models',
        'FDA approval prediction analytics',
        'Low correlation to broader markets'
      ],
      topAssets: [
        { ticker: 'UNH', name: 'UnitedHealth Group', return: 42.3, position: 'Long' },
        { ticker: 'JNJ', name: 'Johnson & Johnson', return: 38.7, position: 'Long' },
        { ticker: 'PFE', name: 'Pfizer', return: 35.2, position: 'Short' },
        { ticker: 'TMO', name: 'Thermo Fisher', return: 31.8, position: 'Long' },
        { ticker: 'ABBV', name: 'AbbVie', return: 29.4, position: 'Long' }
      ]
    },
    {
      id: 'prophitalts-global',
      fundName: 'ProphitAlts Global Macro Fund',
      strategy: 'Macro Fund',
      description: 'A dynamic macro strategy designed to perform well across various economic environments. The portfolio adjusts exposures to global equities, bonds, commodities, and currencies based on macroeconomic trends and market opportunities.',
      sector: 'Multi-Asset',
      aum: '$8.1B',
      inception: '1996',
      minInvestment: '$5,000,000',
      performance: {
        ytd: 12.4,
        oneYear: 15.8,
        threeYear: 11.2,
        fiveYear: 12.9,
        volatility: 8.7,
        sharpeRatio: 1.45
      },
      riskLevel: 'Low',
      highlights: [
        'Navigate any economic environment',
        'Consistent returns across cycles',
        'Top-tier risk management framework'
      ],
      topAssets: [
        { ticker: 'SPY', name: 'S&P 500 ETF', return: 28.9, position: 'Long' },
        { ticker: 'GLD', name: 'Gold ETF', return: 24.3, position: 'Long' },
        { ticker: 'TLT', name: 'Treasury Bonds', return: 21.7, position: 'Short' },
        { ticker: 'DXY', name: 'US Dollar Index', return: 18.2, position: 'Long' },
        { ticker: 'VIX', name: 'Volatility Index', return: 15.8, position: 'Short' }
      ]
    },
    {
      id: 'prophitalts-tech',
      fundName: 'ProphitAlts TMT Long/Short Fund',
      strategy: 'Long/Short',
      description: 'A technology-focused long/short strategy employing fundamental analysis and market insights to identify opportunities in technology stocks. The fund focuses on both growth opportunities and overvalued positions across the tech sector.',
      sector: 'Technology',
      aum: '$3.7B',
      inception: '2015',
      minInvestment: '$10,000,000',
      performance: {
        ytd: 31.2,
        oneYear: 38.6,
        threeYear: 28.4,
        fiveYear: 32.1,
        volatility: 18.9,
        sharpeRatio: 2.14
      },
      riskLevel: 'High',
      highlights: [
        'Deep technology sector expertise',
        'Proven track record of alpha generation',
        'Access to premium deal flow'
      ],
      topAssets: [
        { ticker: 'NVDA', name: 'NVIDIA', return: 58.2, position: 'Long' },
        { ticker: 'AAPL', name: 'Apple', return: 45.7, position: 'Long' },
        { ticker: 'META', name: 'Meta Platforms', return: 42.1, position: 'Short' },
        { ticker: 'GOOGL', name: 'Alphabet', return: 38.9, position: 'Long' },
        { ticker: 'MSFT', name: 'Microsoft', return: 36.4, position: 'Long' }
      ]
    }
  ];

  const formatPerformance = (value: number) => {
    const isPositive = value >= 0;
    return (
      <span className={`performance-value ${isPositive ? 'positive' : 'negative'}`}>
        <FontAwesomeIcon icon={isPositive ? faArrowUp : faArrowDown} />
        {Math.abs(value).toFixed(1)}%
      </span>
    );
  };

  return (
    <div className="prophit-alts-container">
      <div className="alts-header">
        <div>
          <h1 className="alts-title">Alternative Portfolios</h1>
          <p className="alts-subtitle">Exclusive access to institutional-grade investment strategies</p>
        </div>
        <button className="learn-more-btn">
          <FontAwesomeIcon icon={faInfoCircle} />
          Learn More
        </button>
      </div>

      <div className="portfolios-grid">
        {altPortfolios.map((portfolio) => (
          <div key={portfolio.id} className="alt-portfolio-card">
            <div className="portfolio-header">
              <div className="fund-info">
                <h2 className="fund-name">
                  <span className="prophit-text">ProphitAlts</span> {portfolio.fundName.replace('ProphitAlts ', '')}
                </h2>
                <span className="strategy-tag">{portfolio.strategy}</span>
              </div>
              <img src={birdLogo} alt="ProphitAlts" className="bird-logo" />
            </div>

            <p className="portfolio-description">{portfolio.description}</p>

            <div className="portfolio-metrics">
              <div className="metric-group">
                <div className="metric">
                  <span className="metric-label">AUM</span>
                  <span className="metric-value">{portfolio.aum}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">Inception</span>
                  <span className="metric-value">{portfolio.inception}</span>
                </div>
              </div>
            </div>

            <div className="performance-section">
              <h3 className="section-title">Performance</h3>
              <div className="performance-grid">
                <div className="performance-item">
                  <span className="period">YTD</span>
                  {formatPerformance(portfolio.performance.ytd)}
                </div>
                <div className="performance-item">
                  <span className="period">1 Year</span>
                  {formatPerformance(portfolio.performance.oneYear)}
                </div>
                <div className="performance-item">
                  <span className="period">3 Years</span>
                  {formatPerformance(portfolio.performance.threeYear)}
                </div>
                <div className="performance-item">
                  <span className="period">5 Years</span>
                  {formatPerformance(portfolio.performance.fiveYear)}
                </div>
              </div>
              <div className="risk-metrics">
                <div className="risk-metric">
                  <span className="risk-label">Volatility</span>
                  <span className="risk-value">{portfolio.performance.volatility.toFixed(1)}%</span>
                </div>
                <div className="risk-metric">
                  <span className="risk-label">Sharpe Ratio</span>
                  <span className="risk-value">{portfolio.performance.sharpeRatio.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="highlights-section">
              <h3 className="section-title">Key Highlights</h3>
              <ul className="highlights-list">
                {portfolio.highlights.map((highlight, index) => (
                  <li key={index}>{highlight}</li>
                ))}
              </ul>
            </div>

            <div className="top-assets-section">
              <h3 className="section-title">Top Performing Assets</h3>
              <div className="assets-list">
                {portfolio.topAssets.map((asset, index) => (
                  <div key={index} className="asset-item">
                    <div className="asset-info">
                      <span className="asset-ticker">{asset.ticker}</span>
                      <span className="asset-name">{asset.name}</span>
                      <span className={`position-indicator ${asset.position.toLowerCase()}`}>
                        {asset.position}
                      </span>
                    </div>
                    <span className={`asset-return ${asset.return >= 0 ? 'positive' : 'negative'}`}>
                      +{asset.return.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="portfolio-actions">
              <button className="invest-btn">
                <FontAwesomeIcon icon={faChartLine} />
                Invest Now
              </button>
              <button className="details-btn">View Details</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProphitAlts; 