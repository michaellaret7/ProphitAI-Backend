import React from 'react';
import { AdvancedRealTimeChart } from "react-ts-tradingview-widgets";
import './AiInsightsPage.css'; // We'll create this file next for styling

const AiInsightsPage: React.FC = () => {
  return (
    <div className="ai-insights-page">
      <h1 className="ai-insights-title">AI Powered Insights & Chart</h1>
      <div className="tradingview-chart-container">
        <AdvancedRealTimeChart
          theme="light"
          symbol="AAPL"
          autosize
        ></AdvancedRealTimeChart>
      </div>
      {/* You can add more AI insight components here later */}
    </div>
  );
};

export default AiInsightsPage; 