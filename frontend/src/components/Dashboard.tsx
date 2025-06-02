import React, { useState } from 'react';
import './Dashboard.css';
import logo from '../assets/logo.png';
import Portfolio from './Portfolio';

const Dashboard: React.FC = () => {
  const [hoveredSector, setHoveredSector] = useState<string | null>(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState('All');
  const [activeView, setActiveView] = useState<'dashboard' | 'portfolio' | 'ai-insights' | 'allocation' | 'optimization'>('dashboard');

  const sectors = [
    { name: 'Tech', percentage: 25, color: '#5b4cdb', value: '$31,153' },
    { name: 'Financial', percentage: 20, color: '#06b6d4', value: '$24,923' },
    { name: 'Healthcare', percentage: 15, color: '#8b5cf6', value: '$18,692' },
    { name: 'Consumer', percentage: 15, color: '#ec4899', value: '$18,692' },
    { name: 'Energy', percentage: 10, color: '#f59e0b', value: '$12,461' },
    { name: 'Other', percentage: 15, color: '#6b7280', value: '$18,692' }
  ];

  const timeframes = ['1D', '1W', '1M', '3M', '1Y', 'All'];

  const renderMainContent = () => {
    switch (activeView) {
      case 'portfolio':
        return <Portfolio />;
      case 'dashboard':
      default:
        return (
          <>
            {/* Welcome Section */}
            <section className="welcome-section">
              <h1 className="welcome-title">Welcome back, <span className="highlight">John</span></h1>
              <p className="welcome-subtitle">Here's an overview of your portfolio performance</p>
            </section>

            {/* Metrics Cards */}
            <section className="metrics-grid">
              <div className="metric-card">
                <div className="metric-header">
                  <span className="metric-icon">💵</span>
                  <span className="metric-label">Total Value</span>
                </div>
                <div className="metric-value">$124,613.2</div>
                <div className="metric-change positive">
                  <span className="change-arrow">↑</span>
                  $45.31 (+0.0%) Today
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span className="metric-icon">📈</span>
                  <span className="metric-label">Overall Return</span>
                </div>
                <div className="metric-value">+18.7%</div>
                <div className="metric-change positive">
                  <span className="change-arrow">↑</span>
                  1.2% vs last month
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span className="metric-icon">🤖</span>
                  <span className="metric-label">AI Risk Score</span>
                </div>
                <div className="metric-value">72<span className="metric-unit">/100</span></div>
                <div className="metric-change">Moderate Low volatility</div>
                <div className="risk-bar">
                  <div className="risk-fill" style={{width: '72%'}}></div>
                </div>
              </div>

              <div className="metric-card warning-card">
                <div className="metric-header">
                  <span className="metric-icon">⚖️</span>
                  <span className="metric-label">Optimization</span>
                </div>
                <div className="metric-value">3 issues found</div>
                <div className="metric-change warning">Needs attention Click to view</div>
              </div>
            </section>

            {/* Charts Section */}
            <section className="charts-section">
              {/* Portfolio Performance Chart */}
              <div className="chart-container performance-chart-container">
                <div className="chart-header">
                  <h2 className="chart-title">Portfolio Performance</h2>
                  <div className="chart-controls">
                    <div className="time-selector">
                      {timeframes.map(tf => (
                        <button 
                          key={tf}
                          className={`time-btn ${selectedTimeframe === tf ? 'active' : ''}`}
                          onClick={() => setSelectedTimeframe(tf)}
                        >
                          {tf}
                        </button>
                      ))}
                    </div>
                    <button className="chart-action-btn" title="Download">📥</button>
                    <button className="chart-action-btn" title="Refresh">🔄</button>
                  </div>
                </div>
                <div className="chart-legend">
                  <span className="legend-item">
                    <span className="legend-dot pulse" style={{background: '#5b4cdb'}}></span>
                    Your Portfolio
                  </span>
                  <span className="legend-item">
                    <span className="legend-dot" style={{background: '#a0aec0'}}></span>
                    S&P 500
                  </span>
                </div>
                <div className="chart-body">
                  <svg viewBox="0 0 800 300" className="performance-svg" preserveAspectRatio="none">
                    {/* Grid lines */}
                    <g className="grid">
                      {[0, 1, 2, 3, 4].map(i => (
                        <line key={i} x1="0" y1={60 + i * 50} x2="800" y2={60 + i * 50} stroke="#e2e8f0" />
                      ))}
                    </g>
                    {/* S&P 500 line */}
                    <path
                      className="sp500-line"
                      d="M 0,180 L 40,175 L 80,170 L 120,172 L 160,168 L 200,165 L 240,162 L 280,160 L 320,158 L 360,155 L 400,152 L 440,150 L 480,148 L 520,146 L 560,144 L 600,142 L 640,141 L 680,140 L 720,139 L 760,138 L 800,137"
                      fill="none"
                      stroke="#a0aec0"
                      strokeWidth="2"
                      strokeDasharray="5,5"
                    />
                    {/* Portfolio line - realistic market movement */}
                    <path
                      className="portfolio-line"
                      d="M 0,200 L 15,195 L 25,190 L 35,193 L 45,188 L 55,185 L 65,182 L 75,180 L 85,175 L 95,178 L 105,173 L 115,170 L 125,165 L 135,160 L 145,155 L 155,150 L 165,148 L 175,145 L 185,142 L 195,138 L 205,135 L 215,132 L 225,128 L 235,125 L 245,122 L 255,120 L 265,115 L 275,118 L 285,113 L 295,110 L 305,108 L 315,105 L 325,102 L 335,98 L 345,95 L 355,92 L 365,88 L 375,85 L 385,82 L 395,80 L 405,75 L 415,72 L 425,70 L 435,68 L 445,65 L 455,62 L 465,60 L 475,58 L 485,55 L 495,52 L 505,50 L 515,48 L 525,45 L 535,42 L 545,40 L 555,38 L 565,35 L 575,33 L 585,30 L 595,28 L 605,25 L 615,23 L 625,20 L 635,22 L 645,25 L 655,28 L 665,30 L 675,33 L 685,35 L 695,38 L 705,40 L 715,42 L 725,45 L 735,48 L 745,50 L 755,52 L 765,55 L 775,58 L 785,60 L 795,62 L 800,65"
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth="2"
                    />
                    <path
                      className="portfolio-area"
                      d="M 0,200 L 15,195 L 25,190 L 35,193 L 45,188 L 55,185 L 65,182 L 75,180 L 85,175 L 95,178 L 105,173 L 115,170 L 125,165 L 135,160 L 145,155 L 155,150 L 165,148 L 175,145 L 185,142 L 195,138 L 205,135 L 215,132 L 225,128 L 235,125 L 245,122 L 255,120 L 265,115 L 275,118 L 285,113 L 295,110 L 305,108 L 315,105 L 325,102 L 335,98 L 345,95 L 355,92 L 365,88 L 375,85 L 385,82 L 395,80 L 405,75 L 415,72 L 425,70 L 435,68 L 445,65 L 455,62 L 465,60 L 475,58 L 485,55 L 495,52 L 505,50 L 515,48 L 525,45 L 535,42 L 545,40 L 555,38 L 565,35 L 575,33 L 585,30 L 595,28 L 605,25 L 615,23 L 625,20 L 635,22 L 645,25 L 655,28 L 665,30 L 675,33 L 685,35 L 695,38 L 705,40 L 715,42 L 725,45 L 735,48 L 745,50 L 755,52 L 765,55 L 775,58 L 785,60 L 795,62 L 800,65 L 800,300 L 0,300 Z"
                      fill="url(#portfolioGradient3)"
                      opacity="0.3"
                    />
                    <defs>
                      <linearGradient id="portfolioGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#5b4cdb" />
                        <stop offset="100%" stopColor="#5b4cdb" stopOpacity="0" />
                      </linearGradient>
                      <linearGradient id="portfolioGradient2" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#06b6d4" />
                        <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                      </linearGradient>
                      <linearGradient id="portfolioGradient3" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#06b6d4" />
                        <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="chart-labels">
                    <span>$150,000</span>
                    <span>$140,000</span>
                    <span>$130,000</span>
                    <span>$120,000</span>
                    <span>$110,000</span>
                    <span>$100,000</span>
                    <span>$90,000</span>
                  </div>
                  <div className="chart-dates">
                    <span>May 4</span>
                    <span>May 12</span>
                    <span>May 20</span>
                    <span>May 28</span>
                    <span>Jun 1</span>
                  </div>
                </div>
              </div>

              {/* Asset Allocation Chart */}
              <div className="chart-container allocation-chart-container">
                <div className="chart-header">
                  <h2 className="chart-title">Asset Allocation</h2>
                  <button className="chart-menu-btn">⋮</button>
                </div>
                <div className="allocation-content">
                  <div className="donut-container">
                    <svg viewBox="0 0 200 200" className="donut-chart">
                      {/* Background circle */}
                      <circle cx="100" cy="100" r="80" fill="none" stroke="#f3f4f6" strokeWidth="40" />
                      
                      {/* Sector segments */}
                      {(() => {
                        let offset = 0;
                        return sectors.map((sector) => {
                          const circumference = 2 * Math.PI * 80;
                          const strokeLength = (sector.percentage / 100) * circumference;
                          const currentOffset = offset;
                          offset += strokeLength;
                          
                          return (
                            <circle
                              key={sector.name}
                              cx="100"
                              cy="100"
                              r="80"
                              fill="none"
                              stroke={sector.color}
                              strokeWidth={hoveredSector === sector.name ? "45" : "40"}
                              strokeDasharray={`${strokeLength} ${circumference}`}
                              strokeDashoffset={`-${currentOffset}`}
                              transform="rotate(-90 100 100)"
                              className="donut-segment"
                              onMouseEnter={() => setHoveredSector(sector.name)}
                              onMouseLeave={() => setHoveredSector(null)}
                              style={{
                                cursor: 'pointer',
                                transition: 'all 0.3s ease',
                                opacity: hoveredSector && hoveredSector !== sector.name ? 0.6 : 1
                              }}
                            />
                          );
                        });
                      })()}
                    </svg>
                    
                    {/* Center text */}
                    <div className="donut-center">
                      {hoveredSector ? (
                        <>
                          <div className="center-value">{sectors.find(s => s.name === hoveredSector)?.percentage}%</div>
                          <div className="center-label">{hoveredSector}</div>
                        </>
                      ) : (
                        <>
                          <div className="center-value">6</div>
                          <div className="center-label">Sectors</div>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="allocation-legend">
                    {sectors.map(sector => (
                      <div 
                        key={sector.name}
                        className={`legend-item ${hoveredSector === sector.name ? 'active' : ''}`}
                        onMouseEnter={() => setHoveredSector(sector.name)}
                        onMouseLeave={() => setHoveredSector(null)}
                      >
                        <span className="legend-color" style={{background: sector.color}}></span>
                        <span className="legend-text">{sector.name} ({sector.percentage}%)</span>
                        <span className="legend-value">{sector.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <button className="view-all-btn">View All Assets</button>
              </div>
            </section>

            {/* AI Insights Section */}
            <section className="insights-section">
              <div className="insights-header">
                <h2 className="insights-title">
                  <span className="insights-icon">🤖</span>
                  AI Insights
                </h2>
                <button className="insights-filter">Today</button>
              </div>
              <div className="insights-grid">
                <div className="insight-card alert">
                  <div className="insight-icon">⚠️</div>
                  <div className="insight-content">
                    <h3 className="insight-title">Risk Alert</h3>
                    <p className="insight-description">Tech sector exposure exceeds recommended allocation by 8%</p>
                    <p className="insight-time">2 hours ago</p>
                  </div>
                  <button className="insight-action">Review</button>
                </div>
                
                <div className="insight-card opportunity">
                  <div className="insight-icon">💡</div>
                  <div className="insight-content">
                    <h3 className="insight-title">Rebalancing Opportunity</h3>
                    <p className="insight-description">Healthcare sector shows strong growth potential</p>
                    <p className="insight-time">5 hours ago</p>
                  </div>
                  <button className="insight-action">Explore</button>
                </div>
              </div>
            </section>
          </>
        );
    }
  };

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <img src={logo} alt="ProphitAI" className="sidebar-logo" />
        </div>
        
        <nav className="sidebar-nav">
          <a 
            href="#" 
            className={`nav-item ${activeView === 'dashboard' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('dashboard'); }}
          >
            <span className="nav-icon">📊</span>
            <span className="nav-text">Dashboard</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'portfolio' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('portfolio'); }}
          >
            <span className="nav-icon">💼</span>
            <span className="nav-text">Portfolio</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'ai-insights' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('ai-insights'); }}
          >
            <span className="nav-icon">🤖</span>
            <span className="nav-text">AI Insights</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'allocation' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('allocation'); }}
          >
            <span className="nav-icon">📈</span>
            <span className="nav-text">Allocation</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'optimization' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('optimization'); }}
          >
            <span className="nav-icon">⚡</span>
            <span className="nav-text">Optimization</span>
          </a>
        </nav>
        
        <div className="sidebar-section">
          <a href="#" className="nav-item account-item">
            <span className="nav-icon">🏦</span>
            <span className="nav-text">Charles Schwab</span>
            <span className="account-status">Connected</span>
          </a>
        </div>
        
        <nav className="sidebar-nav">
          <a href="#" className="nav-item">
            <span className="nav-icon">📈</span>
            <span className="nav-text">Backtesting</span>
          </a>
          <a href="#" className="nav-item">
            <span className="nav-icon">⚠️</span>
            <span className="nav-text">Risk Analysis</span>
          </a>
          <a href="#" className="nav-item">
            <span className="nav-icon">⚙️</span>
            <span className="nav-text">Settings</span>
          </a>
        </nav>
        
        <div className="sidebar-actions">
          <button className="btn-upload">
            <span className="btn-icon">📤</span>
            Upload Portfolio
          </button>
          <button className="btn-add-asset">
            <span className="btn-icon">➕</span>
            Add Asset
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="dashboard-header">
          <div className="search-container">
            <span className="search-icon">🔍</span>
            <input 
              type="text" 
              placeholder="Search for stocks, assets..." 
              className="search-input"
            />
          </div>
          <div className="header-right">
            <button className="notification-btn">
              <span className="notification-dot"></span>
              <span className="notification-icon">🔔</span>
            </button>
            <div className="user-profile">
              <img src="https://ui-avatars.com/api/?name=John+Doe&background=5b4cdb&color=fff" alt="User" className="user-avatar" />
              <span className="user-name">John Doe</span>
              <span className="dropdown-arrow">▼</span>
            </div>
          </div>
        </header>

        {renderMainContent()}
      </main>
    </div>
  );
};

export default Dashboard; 