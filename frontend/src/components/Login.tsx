import React from 'react';
import './Login.css';
import logo from '../assets/logo.png';

const Login: React.FC = () => {
  const handleLogin = () => {
    // Redirect to the backend login endpoint which will then redirect to WorkOS
    window.location.href = 'http://localhost:8000/auth/login';
  };

  return (
    <>
      {/* Navigation Header */}
      <nav className="nav-header">
        <div className="nav-container">
          <div className="nav-left">
            <img src={logo} alt="ProphitAI" className="nav-logo" />
          </div>
          <div className="nav-right">
            <a href="#" className="nav-link">Home</a>
            <a href="#" className="nav-link">Services</a>
            <a href="#" className="nav-link">About</a>
            <a href="#" className="nav-link">Contact</a>
            <button className="nav-login-btn" onClick={handleLogin}>Login</button>
            <button className="nav-signup-btn">Sign Up</button>
          </div>
        </div>
      </nav>

      <div className="login-container">
        <div className="login-left">
          <div className="login-form-container">
            <h1 className="login-title">Welcome</h1>
            <p className="login-subtitle">Log in to access your portfolio dashboard</p>
            
            <button onClick={handleLogin} className="login-button">
              Sign In
            </button>
            
            <p className="signup-link" style={{ marginTop: '2rem' }}>
              Don't have an account? <a href="#">Sign up</a>
            </p>
          </div>
        </div>
        
        <div className="login-right">
          <div className="right-content">
            <div className="floating-elements">
              <div className="floating-circle circle-1"></div>
              <div className="floating-circle circle-2"></div>
              <div className="floating-circle circle-3"></div>
            </div>
            
            <h2 className="right-title">AI-Powered Portfolio Management</h2>
            <p className="right-subtitle">
              Advanced analytics and insights for optimizing your investment strategy
            </p>
            
            <div className="stats-container">
              <div className="stat-item">
                <div className="stat-value">$2.4B+</div>
                <div className="stat-label">Assets Managed</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">98%</div>
                <div className="stat-label">Client Satisfaction</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">24/7</div>
                <div className="stat-label">AI Monitoring</div>
              </div>
            </div>
            
            <div className="chart-container">
              <div className="chart-header">
                <span className="chart-title">Portfolio vs S&P 500</span>
                <span className="chart-percentage">+24.3%</span>
              </div>
              <div className="chart-preview">
                <svg className="performance-chart" viewBox="0 0 400 200">
                  <defs>
                    <linearGradient id="portfolioGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="rgba(74, 222, 128, 0.3)" />
                      <stop offset="100%" stopColor="rgba(74, 222, 128, 0)" />
                    </linearGradient>
                    <linearGradient id="sp500Gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="rgba(255, 255, 255, 0.2)" />
                      <stop offset="100%" stopColor="rgba(255, 255, 255, 0)" />
                    </linearGradient>
                  </defs>
                  
                  {/* S&P 500 Line */}
                  <path
                    className="sp500-line"
                    d="M 0,140 Q 50,135 100,130 T 200,120 Q 250,115 300,110 T 400,100"
                    fill="none"
                    stroke="rgba(255, 255, 255, 0.5)"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                  <path
                    className="sp500-area"
                    d="M 0,140 Q 50,135 100,130 T 200,120 Q 250,115 300,110 T 400,100 L 400,200 L 0,200 Z"
                    fill="url(#sp500Gradient)"
                  />
                  
                  {/* Portfolio Line */}
                  <path
                    className="chart-line"
                    d="M 0,150 Q 50,140 100,120 T 200,90 Q 250,70 300,40 T 400,20"
                    fill="none"
                    stroke="#4ade80"
                    strokeWidth="3"
                  />
                  <path
                    className="chart-area"
                    d="M 0,150 Q 50,140 100,120 T 200,90 Q 250,70 300,40 T 400,20 L 400,200 L 0,200 Z"
                    fill="url(#portfolioGradient)"
                  />
                  
                  {/* Data Points for Portfolio */}
                  <circle className="chart-point" cx="100" cy="120" r="5" fill="#4ade80" />
                  <circle className="chart-point" cx="200" cy="90" r="5" fill="#4ade80" />
                  <circle className="chart-point" cx="300" cy="40" r="5" fill="#4ade80" />
                  <circle className="chart-point" cx="400" cy="20" r="5" fill="#4ade80" />
                </svg>
                <div className="chart-grid">
                  <div className="grid-line"></div>
                  <div className="grid-line"></div>
                  <div className="grid-line"></div>
                  <div className="grid-line"></div>
                </div>
                
                {/* Legend */}
                <div className="chart-legend">
                  <div className="legend-item">
                    <span className="legend-dot portfolio"></span>
                    <span className="legend-label">Your Portfolio</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot sp500"></span>
                    <span className="legend-label">S&P 500</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="ai-particles">
            <div className="particle particle-1"></div>
            <div className="particle particle-2"></div>
            <div className="particle particle-3"></div>
            <div className="particle particle-4"></div>
            <div className="particle particle-5"></div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Login; 