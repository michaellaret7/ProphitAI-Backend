import React, { useState } from 'react';
import './Optimize.css';

const Optimize: React.FC = () => {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleOptimize = async () => {
    setIsOptimizing(true);
    setError(null);
    setOptimizationResult(null);

    try {
      const response = await fetch('http://localhost:8000/api/runner/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setOptimizationResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="optimize-container">
      <section className="optimize-header">
        <h1 className="optimize-title">
          Portfolio <span className="optimize-accent">Optimization</span>
        </h1>
        <p className="optimize-subtitle">
          Advanced AI-powered portfolio construction and optimization
        </p>
      </section>

      <section className="optimize-content">
        <div className="optimize-card">
          <div className="optimize-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
            </svg>
          </div>
          
          <h2 className="optimize-card-title">Intelligent Portfolio Optimization</h2>
          <p className="optimize-card-description">
            Click the button below to start the AI-driven optimization process
          </p>

          <button 
            className={`optimize-button ${isOptimizing ? 'optimizing' : ''}`}
            onClick={handleOptimize}
            disabled={isOptimizing}
          >
            {isOptimizing ? (
              <>
                <span className="button-spinner"></span>
                Optimizing...
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Optimize Portfolio
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="result-container error">
            <h3>Error</h3>
            <pre>{error}</pre>
          </div>
        )}

        {optimizationResult && (
          <div className="result-container">
            <div className="result-header">
              <h3>Optimization Results</h3>
              <span className="result-badge">Complete</span>
            </div>
            <pre className="result-json">{JSON.stringify(optimizationResult, null, 2)}</pre>
          </div>
        )}
      </section>
    </div>
  );
};

export default Optimize; 