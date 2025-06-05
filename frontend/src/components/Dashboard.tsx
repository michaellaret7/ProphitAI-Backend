import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import logo from '../assets/logo.png';
import ibkrLogo from '../assets/logos/ibkr-logo.png';
import Portfolio from './Portfolio';
import AiInsightsPage from './AiInsightsPage';
import ProphitGpt from './ProphitGpt';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
    faChartPie, faLightbulb, faTasks, faHistory,
    faExclamationTriangle, faCog, faUpload, faPlus, faSearch, faChartLine,
    faSlidersH, faDollarSign, faRobot, faBalanceScale, faFilter
} from '@fortawesome/free-solid-svg-icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/react';
import clsx from 'clsx';

interface Sector {
  name: string;
  percentage: number;
  color: string;
  // value: string; // This field is no longer sent by the backend
}

// Define a type for ETF visibility state
interface EtfVisibility {
  spy: boolean;
  qqq: boolean;
  iwm: boolean;
  gld: boolean;
  dbc: boolean;
  eem: boolean;
}

const Dashboard: React.FC = () => {
  const [hoveredSector, setHoveredSector] = useState<string | null>(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState('All');
  const [activeView, setActiveView] = useState<'dashboard' | 'portfolio' | 'manager' | 'optimizer' | 'builder' | 'prophitgpt' | 'risk-analysis' | 'backtest' | 'asset-universe' | 'news'>('dashboard');
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [isLoadingAllocation, setIsLoadingAllocation] = useState(true);
  const [allocationError, setAllocationError] = useState<string | null>(null);
  
  // Add a debounced state for hover to reduce frequent updates
  const debouncedHoveredSector = useRef<string | null>(null);
  const hoverTimeout = useRef<NodeJS.Timeout | null>(null);
  
  // Debounce hover state updates
  const handleHoverChange = (sectorName: string | null) => {
    if (hoverTimeout.current) {
      clearTimeout(hoverTimeout.current);
    }
    hoverTimeout.current = setTimeout(() => {
      debouncedHoveredSector.current = sectorName;
      setHoveredSector(sectorName);
    }, 50); // 50ms debounce to prevent rapid state changes
  };
  
  useEffect(() => {
    return () => {
      if (hoverTimeout.current) {
        clearTimeout(hoverTimeout.current);
      }
    };
  }, []);
  
  // Portfolio performance state
  const [portfolioPerformance, setPortfolioPerformance] = useState<any>({
    performanceData: [],
    totalReturn: 0,
    startDate: '',
    endDate: '',
    spyTotalReturn: null,
    qqqTotalReturn: null,
    iwmTotalReturn: null,
    gldTotalReturn: null,
    dbcTotalReturn: null,
    eemTotalReturn: null,
  });
  const [isLoadingPerformance, setIsLoadingPerformance] = useState(true);
  const [performanceError, setPerformanceError] = useState<string | null>(null);
  
  const performanceChartContainerRef = useRef<HTMLDivElement>(null);

  const timeframes = ['1M', '3M', '1Y', 'All'];

  // State for ETF visibility
  const [etfVisibility, setEtfVisibility] = useState<EtfVisibility>({
    spy: true,
    qqq: true,
    iwm: true,
    gld: true,
    dbc: true,
    eem: true,
  });

  useEffect(() => {
    const fetchAllocationData = async () => {
      setIsLoadingAllocation(true);
      setAllocationError(null);
      try {
        const portfolioId = "f0e3e97b-ff5c-48a2-93e9-d8a1fa84c75b"; // Hardcoded portfolio_id
        const response = await fetch(`http://localhost:8000/api/portfolio/allocation/${portfolioId}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setSectors(data.sectors);
      } catch (error) {
        if (error instanceof Error) {
          setAllocationError(error.message);
        } else {
          setAllocationError('An unknown error occurred');
        }
        console.error("Failed to fetch allocation data:", error);
        setSectors([
          { name: 'Error Loading Allocation', percentage: 100, color: '#dc2626' }
        ]);
      } finally {
        setIsLoadingAllocation(false);
      }
    };

    if (activeView === 'dashboard') {
      fetchAllocationData();
    }
  }, [activeView]);

  useEffect(() => {
    // Ensure selectedTimeframe is valid after removing 1D and 1W
    if (selectedTimeframe === '1D' || selectedTimeframe === '1W') {
      setSelectedTimeframe('1M'); // Default to 1M if current selection was removed
    }

    const fetchPortfolioPerformance = async () => {
      setIsLoadingPerformance(true);
      setPerformanceError(null);
      try {
        const userId = "2594bb4d-784c-4c53-a049-8438baaf0d7c"; // User ID from the request
        
        // Determine days based on selected timeframe
        let days = 365; // Default
        switch (selectedTimeframe) {
          case '1M': days = 30; break;
          case '3M': days = 90; break;
          case '1Y': days = 365; break;
          case 'All': days = 1825; break; // 5 years
        }
        
        const response = await fetch(`http://localhost:8000/api/portfolio/performance/${userId}?days=${days}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setPortfolioPerformance(data);
      } catch (error) {
        if (error instanceof Error) {
          setPerformanceError(error.message);
        } else {
          setPerformanceError('An unknown error occurred');
        }
        console.error("Failed to fetch portfolio performance:", error);
      } finally {
        setIsLoadingPerformance(false);
      }
    };

    if (activeView === 'dashboard') {
      fetchPortfolioPerformance();
    }
  }, [activeView, selectedTimeframe]);

  const handleEtfVisibilityChange = (etfKey: keyof EtfVisibility) => {
    setEtfVisibility(prev => ({ ...prev, [etfKey]: !prev[etfKey] }));
  };

  const renderPortfolioChart = () => {
    if (isLoadingPerformance) {
      return <div className="chart-loading">Loading portfolio performance...</div>;
    }
    
    if (performanceError) {
      return <div className="chart-error">Error: {performanceError}</div>;
    }
    
    if (!portfolioPerformance.performanceData || portfolioPerformance.performanceData.length === 0) {
      return <div className="chart-no-data">No performance data available</div>;
    }
    
    // Format data for Recharts - using normalized values for comparison
    const chartData = portfolioPerformance.performanceData.map((d: any) => ({
      date: d.date,
      portfolio: d.portfolio_normalized || 100,
      spy: d.spy_normalized || null,
      qqq: d.qqq_normalized || null,
      iwm: d.iwm_normalized || null,
      gld: d.gld_normalized || null,
      dbc: d.dbc_normalized || null,
      eem: d.eem_normalized || null,
      portfolioValue: d.value,
      displayDate: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }));
    
    // Check if we have ETF data
    const hasSpyData = chartData.some((d: any) => d.spy !== null);
    const hasQqqData = chartData.some((d: any) => d.qqq !== null);
    const hasIwmData = chartData.some((d: any) => d.iwm !== null);
    const hasGldData = chartData.some((d: any) => d.gld !== null);
    const hasDbcData = chartData.some((d: any) => d.dbc !== null);
    const hasEemData = chartData.some((d: any) => d.eem !== null);
    
    // Custom tooltip component
    const CustomTooltip = ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        const portfolioData = payload.find((p: any) => p.dataKey === 'portfolio');
        const spyData = payload.find((p: any) => p.dataKey === 'spy');
        const qqqData = payload.find((p: any) => p.dataKey === 'qqq');
        const iwmData = payload.find((p: any) => p.dataKey === 'iwm');
        const gldData = payload.find((p: any) => p.dataKey === 'gld');
        const dbcData = payload.find((p: any) => p.dataKey === 'dbc');
        const eemData = payload.find((p: any) => p.dataKey === 'eem');
        const portfolioValue = payload[0]?.payload?.portfolioValue;
        
        return (
          <div className="custom-tooltip">
            <p className="tooltip-date">{new Date(label).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
            {portfolioData && (
              <p className="tooltip-portfolio">
                Portfolio: ${portfolioValue?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                <span className="tooltip-change"> ({((portfolioData.value - 100)).toFixed(2)}%)</span>
              </p>
            )}
            {spyData && spyData.value !== null && (
              <p className="tooltip-spy">
                S&P 500: <span className="tooltip-change">{((spyData.value - 100)).toFixed(2)}%</span>
              </p>
            )}
            {qqqData && qqqData.value !== null && (
              <p className="tooltip-qqq">
                QQQ: <span className="tooltip-change">{((qqqData.value - 100)).toFixed(2)}%</span>
              </p>
            )}
            {iwmData && iwmData.value !== null && (
              <p className="tooltip-iwm">
                IWM: <span className="tooltip-change">{((iwmData.value - 100)).toFixed(2)}%</span>
              </p>
            )}
            {gldData && gldData.value !== null && (
              <p className="tooltip-gld">
                GLD: <span className="tooltip-change">{((gldData.value - 100)).toFixed(2)}%</span>
              </p>
            )}
            {dbcData && dbcData.value !== null && (
              <p className="tooltip-dbc">
                DBC: <span className="tooltip-change">{((dbcData.value - 100)).toFixed(2)}%</span>
              </p>
            )}
            {eemData && eemData.value !== null && (
              <p className="tooltip-eem">
                EEM: <span className="tooltip-change">{((eemData.value - 100)).toFixed(2)}%</span>
              </p>
            )}
          </div>
        );
      }
      return null;
    };
    
    // Format Y-axis values as percentage change
    const formatYAxis = (value: number) => {
      return `${((value - 100)).toFixed(0)}%`;
    };
    
    return (
      <div className="recharts-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart 
            data={chartData}
            margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              interval="preserveStartEnd"
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              tickFormatter={formatYAxis}
              domain={['dataMin - 5', 'dataMax + 5']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="portfolio"
              stroke="#000000"
              strokeWidth={2.5}
              dot={false}
              name={`Portfolio (${portfolioPerformance.totalReturn >= 0 ? '+' : ''}${portfolioPerformance.totalReturn}%)`}
              activeDot={{ r: 6 }}
            />
            {hasSpyData && etfVisibility.spy && (
              <Line
                type="monotone"
                dataKey="spy"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name={`S&P 500 (${portfolioPerformance.spyTotalReturn >= 0 ? '+' : ''}${portfolioPerformance.spyTotalReturn ?? 0}%)`}
                activeDot={{ r: 6 }}
              />
            )}
            {hasQqqData && etfVisibility.qqq && (
              <Line
                type="monotone"
                dataKey="qqq"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
                name={`QQQ (${portfolioPerformance.qqqTotalReturn >= 0 ? '+' : ''}${portfolioPerformance.qqqTotalReturn ?? 0}%)`}
                activeDot={{ r: 6 }}
              />
            )}
            {hasIwmData && etfVisibility.iwm && (
              <Line
                type="monotone"
                dataKey="iwm"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
                name={`IWM (${portfolioPerformance.iwmTotalReturn >= 0 ? '+' : ''}${portfolioPerformance.iwmTotalReturn ?? 0}%)`}
                activeDot={{ r: 6 }}
              />
            )}
            {hasGldData && etfVisibility.gld && (
              <Line
                type="monotone"
                dataKey="gld"
                stroke="#d1a11e"
                strokeWidth={2}
                dot={false}
                name={`GLD (${portfolioPerformance.gldTotalReturn >= 0 ? '+' : ''}${portfolioPerformance.gldTotalReturn ?? 0}%)`}
                activeDot={{ r: 6 }}
              />
            )}
            {hasDbcData && etfVisibility.dbc && (
              <Line
                type="monotone"
                dataKey="dbc"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                name={`DBC (${portfolioPerformance.dbcTotalReturn >= 0 ? '+' : ''}${portfolioPerformance.dbcTotalReturn ?? 0}%)`}
                activeDot={{ r: 6 }}
              />
            )}
            {hasEemData && etfVisibility.eem && (
              <Line
                type="monotone"
                dataKey="eem"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={false}
                name={`EEM (${portfolioPerformance.eemTotalReturn >= 0 ? '+' : ''}${portfolioPerformance.eemTotalReturn ?? 0}%)`}
                activeDot={{ r: 6 }}
              />
            )}
            <Legend 
              verticalAlign="bottom" 
              height={36}
              iconType="line"
              wrapperStyle={{
                paddingTop: '10px',
                fontSize: '14px'
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const renderMainContent = () => {
    switch (activeView) {
      case 'portfolio':
        return <Portfolio />;
      case 'manager':
        return <AiInsightsPage />;
      case 'builder':
        return <Portfolio />;
      case 'prophitgpt':
        return <ProphitGpt />;
      case 'backtest':
        return <Portfolio />;
      case 'asset-universe':
        return <Portfolio />;
      case 'news':
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
                  <span className="metric-icon total-value-icon-bg">
                    <FontAwesomeIcon icon={faDollarSign} />
                  </span>
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
                  <span className="metric-icon overall-return-icon-bg">
                    <FontAwesomeIcon icon={faChartLine} />
                  </span>
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
                  <span className="metric-icon ai-risk-icon-bg">
                    <FontAwesomeIcon icon={faRobot} />
                  </span>
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
                  <span className="metric-icon optimization-icon-bg">
                    <FontAwesomeIcon icon={faBalanceScale} />
                  </span>
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
                    {/* ETF Filter on the left */}
                    <div className="etf-filter-container">
                      <Menu>
                        <MenuButton className="etf-filter-btn">
                          <FontAwesomeIcon icon={faFilter} />
                          ETFs
                        </MenuButton>
                        <MenuItems 
                          anchor="bottom start"
                          className="etf-dropdown-menu"
                        >
                          {(Object.keys(etfVisibility) as Array<keyof EtfVisibility>).map(etfKey => {
                            const etfName = etfKey.toUpperCase();
                            const totalReturnKey = `${etfKey}TotalReturn` as keyof typeof portfolioPerformance;
                            if (portfolioPerformance.hasOwnProperty(totalReturnKey)) {
                              return (
                                <MenuItem key={etfKey}>
                                  {({ focus }) => (
                                    <label 
                                      className={clsx(
                                        'etf-dropdown-item',
                                        focus && 'focus'
                                      )}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <input 
                                        type="checkbox"
                                        checked={etfVisibility[etfKey]}
                                        onChange={() => handleEtfVisibilityChange(etfKey)}
                                        onClick={(e) => e.stopPropagation()}
                                      />
                                      {etfName}
                                    </label>
                                  )}
                                </MenuItem>
                              );
                            }
                            return null;
                          })}
                        </MenuItems>
                      </Menu>
                    </div>

                    {/* Time selector on the right */}
                    <div className="time-selector ml-auto">
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
                  </div>
                </div>
                <div className="chart-body" ref={performanceChartContainerRef}>
                  {renderPortfolioChart()}
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
                      <circle cx="100" cy="100" r="80" fill="none" stroke="#f3f4f6" strokeWidth="35" />
                      
                      {/* Sector segments */}
                      {(() => {
                        if (isLoadingAllocation) return null; // Or a loading spinner for the chart
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
                              strokeWidth={hoveredSector === sector.name ? "40" : "35"}
                              strokeDasharray={`${strokeLength} ${circumference}`}
                              strokeDashoffset={`-${currentOffset}`}
                              transform="rotate(-90 100 100)"
                              className="donut-segment"
                              onMouseEnter={() => handleHoverChange(sector.name)}
                              onMouseLeave={() => handleHoverChange(null)}
                              style={{
                                cursor: 'pointer',
                                transition: 'all 0.2s ease', // Reduced transition time for quicker response
                                opacity: hoveredSector && hoveredSector !== sector.name ? 0.6 : 1
                              }}
                            />
                          );
                        });
                      })()}
                    </svg>
                    
                    {/* Center text */}
                    <div className="donut-center">
                      {isLoadingAllocation ? (
                        <div className="center-label">Loading...</div>
                      ) : hoveredSector ? (
                        <>
                          <div className="center-value">{sectors.find(s => s.name === hoveredSector)?.percentage}%</div>
                          <div className="center-label">{hoveredSector}</div>
                        </>
                      ) : (
                        <>
                          <div className="center-value">{sectors.length}</div>
                          <div className="center-label">Sectors</div>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="allocation-legend">
                    {isLoadingAllocation && <p>Loading allocation data...</p>}
                    {allocationError && <p style={{ color: 'red' }}>Error: {allocationError}</p>}
                    {!isLoadingAllocation && !allocationError && sectors.map(sector => (
                      <div 
                        key={sector.name}
                        className={`legend-item ${hoveredSector === sector.name ? 'active' : ''}`}
                        onMouseEnter={() => handleHoverChange(sector.name)}
                        onMouseLeave={() => handleHoverChange(null)}
                      >
                        <span className="legend-color" style={{background: sector.color}}></span>
                        <span className="legend-text">{sector.name} ({sector.percentage}%)</span>
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
            <span className="nav-icon"><FontAwesomeIcon icon={faChartLine} /></span>
            <span className="nav-text">Dashboard</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'portfolio' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('portfolio'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faTasks} /></span>
            <span className="nav-text">Portfolio</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'manager' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('manager'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faCog} /></span>
            <span className="nav-text">Manager</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'optimizer' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('optimizer'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faSlidersH} /></span>
            <span className="nav-text">Optimizer</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'builder' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('builder'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faPlus} /></span>
            <span className="nav-text">Builder</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'prophitgpt' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('prophitgpt'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faRobot} /></span>
            <span className="nav-text">ProphitGPT</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'risk-analysis' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('risk-analysis'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faExclamationTriangle} /></span>
            <span className="nav-text">Risk Analysis</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'backtest' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('backtest'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faHistory} /></span>
            <span className="nav-text">Backtest</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'asset-universe' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('asset-universe'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faChartPie} /></span>
            <span className="nav-text">Asset Universe</span>
          </a>
          <a 
            href="#" 
            className={`nav-item ${activeView === 'news' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); setActiveView('news'); }}
          >
            <span className="nav-icon"><FontAwesomeIcon icon={faLightbulb} /></span>
            <span className="nav-text">News</span>
          </a>
          <a href="#" className="nav-item">
            <span className="nav-icon"><FontAwesomeIcon icon={faCog} /></span>
            <span className="nav-text">Settings</span>
          </a>
        </nav>

        {/* <div className="sidebar-section">
          <a href="#" className="nav-item account-item">
            <img src={ibkrLogo} alt="Interactive Brokers" className="broker-logo" />
            <span className="nav-text">Interactive Brokers</span>
            <span className="account-status">Connected</span>
          </a>
        </div> */}
        
        <div className="sidebar-actions">
          <button className="btn-upload">
            <span className="btn-icon"><FontAwesomeIcon icon={faUpload} /></span>
            Upload Portfolio
          </button>
          <button className="btn-add-asset">
            <span className="btn-icon"><FontAwesomeIcon icon={faPlus} /></span>
            Add Asset
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="dashboard-header">
          <div className="search-container">
            <span className="search-icon"><FontAwesomeIcon icon={faSearch} /></span>
            <input 
              type="text" 
              placeholder="Search for stocks, assets..." 
              className="search-input"
            />
          </div>
          <div className="header-right">
            <div className="broker-status-container">
              <img src={ibkrLogo} alt="Interactive Brokers" className="broker-logo-header" />
              <span className="broker-status-text connected">Connected</span>
            </div>
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