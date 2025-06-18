├── backend/
│   ├── __init__.py --> Marks the backend directory as a Python package.
│   ├── main.py --> The main FastAPI application file that sets up the API, CORS middleware, and includes all the API routers.
│   ├── README.md --> Provides setup and execution instructions for the backend API, including environment variables and available endpoints.
│   ├── jobs/
│   │   ├── update_database_prices_schema.py --> A script to extract the schema of all price-related databases and save it to a JSON file.
│   │   ├── update_database_schema.py --> Contains a script to recreate the `database_schemas.json` file by inspecting the live database structure.
│   │   ├── update_fundamental_predictions.py --> Fetches quarterly fundamental estimates for all tickers from Interactive Brokers and updates them in the database.
│   │   ├── update_fundamentals.py --> Fetches and displays comprehensive financial data (income statements, balance sheets, cash flow, and metrics) for a given ticker from the financialdatasets.ai API.
│   │   └── update_stock_data.py --> Updates the historical stock price database by fetching the latest data from Interactive Brokers.
│   ├── output/
│   │   └── portfolio_optimization_*.txt --> Daily portfolio optimization output files containing optimization results and recommendations.
│   └── src/
│       ├── __init__.py --> Exposes key data management functions from various modules within the data package.
│       ├── agents/
│       │   ├── __init__.py --> Marks the agents directory as a Python package.
│       │   └── stress_test_agent/
│       │       ├── stress_test_agent_class.py --> Defines a `StressTestAgent` class that uses a large language model and a set of tools to perform stress testing on a portfolio.
│       │       ├── stress_test_agent_run.py --> This script runs the `StressTestAgent` with a detailed prompt to identify the weakest holding in a portfolio under various stress scenarios.
│       │       └── tools/
│       │           ├── __init__.py --> Marks the tools directory as a Python package.
│       │           ├── get_data.py --> A set of tools for the stress test agent to retrieve financial data, such as tickers, portfolio returns, and historical stock data.
│       │           └── tool_registry.py --> Registers all the available data retrieval tools with the stress test agent.
│       ├── analysts/
│       │   ├── __init__.py --> Exposes key analyst functions from the equity and macro analyst modules for easy importing.
│       │   ├── analyst_research/
│       │   │   ├── cache_research.py --> A script to run all the research analyst functions and store their output in the database, effectively caching the research.
│       │   │   ├── equity_research_analysts.py --> Contains functions that generate comprehensive research reports for various equity sectors using an LLM.
│       │   │   └── macro_research_analyst.py --> Contains functions that generate comprehensive research reports for various macroeconomic asset classes using an LLM.
│       │   ├── equity_analysts.py --> Provides functions to retrieve equity sector research reports from the database for various industries.
│       │   └── macro_analysts.py --> Provides functions to retrieve macro-economic research reports and market data for various asset classes.
│       ├── api/
│       │   ├── __init__.py --> Marks the directory as a Python package for the ProphitAI API.
│       │   ├── runner.py --> Defines API endpoints for running the portfolio optimization workflow, including a streaming endpoint for live logs.
│       │   ├── portfolio.py --> Defines API endpoints for retrieving portfolio data, including allocations, holdings, and historical performance.
│       │   └── prophitgpt.py --> Provides a chat endpoint that uses a large language model with tool-calling capabilities to answer user queries about their portfolio and financial data.
│       ├── auth/
│       │   ├── __init__.py --> Initializes the auth module and exposes the router.
│       │   ├── routes.py --> Defines authentication routes for login, logout, and user callbacks using WorkOS.
│       │   ├── models.py --> Defines Pydantic models for User and UserSession data structures.
│       │   ├── dependencies.py --> Provides dependency injection functions for authenticating users.
│       │   └── config.py --> Contains configuration settings for the authentication service.
│       ├── backtest/
│       │   ├── backtest_helpers.py --> Contains helper functions for backtesting, including fetching historical data, calculating portfolio returns, and preparing data from the database.
│       │   └── backtest_run.py --> Main script for executing portfolio backtests, generating performance metrics, and visualizing results against benchmarks.
│       ├── data/
│       │   ├── __init__.py --> Exposes key data management functions from various modules within the data package.
│       │   ├── user_information.py --> Provides a function to retrieve a hardcoded user profile with financial and risk tolerance information.
│       │   ├── database/
│       │   │   ├── database_schemas.json --> Contains the JSON definitions for the fundamental data database schemas.
│       │   │   └── database_schemas_prices.json --> Contains the JSON definitions for the price data database schemas.
│       │   ├── final_portfolio_data/
│       │   │   ├── __init__.py --> Exposes functions for storing final portfolio data, including sector allocations and user information.
│       │   │   ├── store_final_portfolio.py --> Stores the detailed, ticker-level final portfolio recommendations into the database.
│       │   │   ├── store_portfolio_sector_allocations.py --> Stores the sector-level allocation recommendations from the first phase of portfolio optimization into the database.
│       │   │   └── store_user_information.py --> Stores user profile information, linking it to a specific portfolio in the database.
│       │   ├── fundamental_report/
│       │   │   ├── __init__.py --> An empty file that marks the directory as a Python package.
│       │   │   ├── generate_and_store_sector_averages.py --> Calculates and stores the average financial metrics for each sector in the database.
│       │   │   ├── generate_fundamental_report.py --> Generates a fundamental analysis report for a given ticker by comparing its metrics to sector averages using an LLM.
│       │   │   └── store_fundamental_report.py --> A script to generate and store fundamental analysis reports for all tickers in a given sector.
│       │   └── user_portfolio_data/
│       │       ├── __init__.py --> An empty file that marks the directory as a Python package.
│       │       ├── fetch_ibkr_holdings.py --> Fetches the current portfolio positions from Interactive Brokers and formats them into a list of dictionaries.
│       │       ├── retrieve_and_store_portfolio_data.py --> Orchestrates fetching portfolio data from Interactive Brokers and storing it in the database.
│       │       ├── store_user_positions.py --> Stores or updates user portfolio positions in the database with upsert logic.
│       │       └── update_user_holdings.py --> Updates a user's portfolio in the database with the latest data from Interactive Brokers.
│       ├── portfolio_builder/
│       ├── portfolio_optimization/
│       │   ├── __init__.py --> Exposes the main functions from phase one and phase two of the portfolio optimization process and provides backward compatibility shims.
│       │   ├── runner.py --> A command-line script that executes the full two-phase portfolio optimization workflow.
│       │   ├── phase_one/
│       │   │   ├── __init__.py --> Exposes key functions from the phase one modules, including formatting, optimization, and validation.
│       │   │   ├── phase_one_formatting.py --> Formats comprehensive portfolio data, including holdings and performance metrics, into a JSON structure for the first phase of optimization.
│       │   │   ├── phase_one_prompts.py --> Contains the system and user prompt templates used for the first phase of portfolio optimization with an LLM.
│       │   │   ├── phase_one_run.py --> Executes the first phase of portfolio optimization by interacting with an LLM and a suite of analyst tools to generate a draft portfolio.
│       │   │   └── phase_one_validation.py --> Provides helper functions to parse, validate, and fix the portfolio data returned by the LLM in phase one.
│       │   └── phase_two/
│       │       ├── __init__.py --> Exposes key functions from the phase two modules, including data retrieval, calculations, and the main run function.
│       │       ├── data_retrieval.py --> A data retrieval module for the second phase of portfolio optimization, providing functions to get prices, fundamentals, and tickers.
│       │       ├── phase_two_calculations.py --> Contains functions to calculate a wide range of financial and risk metrics for stocks, and to rank them using composite scores.
│       │       ├── phase_two_prompts.py --> Contains the system and user prompt templates used for the second phase of portfolio optimization with an LLM.
│       │       ├── phase_two_run.py --> Executes the second phase of portfolio optimization, which involves selecting top tickers within asset classes and generating detailed recommendations.
│       │       └── retrieve_fundamental_report.py --> Provides functions to retrieve pre-generated fundamental analysis reports for a given ticker from the database.
│       ├── prophitai_gpt/
│       │   ├── gpt.py --> An interactive chat application that uses a large language model with financial tools to answer user prompts.
│       │   ├── dataRetrievalTools/
│       │   │   ├── __init__.py --> Marks the directory as a Python package for data retrieval utility modules.
│       │   │   └── retrieve_financial_metrics.py --> A utility to retrieve time-series financial metric data for a specific stock from the database.
│       │   ├── functionSchemas/
│       │   │   └── tools.py --> Defines the function schemas for the tools available to the ProphitAI GPT, enabling it to call functions for data retrieval.
│       │   └── placeOrders/
│       │       ├── exitPosition.py --> Contains functions to exit a position by placing a market sell order on Interactive Brokers.
│       │       └── longOrder.py --> Contains functions to place long bracket orders with take-profit and stop-loss levels on Interactive Brokers.
│       └── utils/
│           ├── __init__.py --> Exposes various utility functions for database connections, file operations, formatting, and model/client selection.
│           ├── caching.py --> Provides a simple in-memory caching decorator to avoid re-running expensive functions.
│           ├── choose_model_and_client.py --> Provides helper functions to create and configure clients for various large language model APIs.
│           ├── data_retrieval.py --> A centralized utility for fetching price and fundamental data from the database, with caching capabilities.
│           ├── database.py --> A collection of utility functions for managing PostgreSQL database connections, schemas, and executing queries.
│           ├── determine_etf.py --> A utility function to determine if a given asset class is an ETF by checking the database schema.
│           ├── file_utils.py --> Provides utility functions for common file operations, such as getting project root, schema paths, and ensuring directories exist.
│           ├── financial_calculations.py --> A library of functions for calculating various financial metrics, such as volatility, beta, Sharpe ratio, and more.
│           ├── formatting.py --> A set of utility functions for formatting data into human-readable strings, such as dollar amounts, percentages, and Markdown tables.
│           ├── ib_utils.py --> Provides utility functions for managing a singleton connection to Interactive Brokers.
│           ├── logging_config.py --> Provides utilities for configuring logging and redirecting `print` statements to the logging system.
│           ├── portfolio_analysis.py --> Provides functions to fetch and analyze portfolio data from Interactive Brokers, including holdings, performance metrics, diversification, and correlation analysis.
│           ├── push_full_hist_data.py --> A utility to connect to Interactive Brokers and fetch up to 5 years of historical 15-minute interval stock data for a given symbol.
│           ├── retrieve_portfolio_from_db.py --> Provides functions to retrieve various types of portfolio information from the database.
│           ├── retrieve_user_auth_data.py --> Provides a function to retrieve user authentication data from the database.
│           └── ticker_utils.py --> Provides a utility function to convert a company name into its stock ticker symbol using OpenAI and yfinance.
│   └── testing/
│       ├── All_US_ETFs.xlsx --> An excel file containing a list of all US ETFs.
│       ├── buildDB.py --> A script for building and managing the database, including creating tables, fetching data from Interactive Brokers, and inserting it into the database. It also contains functions for exploring the database structure.
│       ├── react_agent_class.py --> Defines a `ReactAgent` class that uses a large language model and a set of tools to perform tasks based on a thought-action-observation loop.
│       ├── react_agent_run.py --> A script to run the `ReactAgent` for portfolio stress testing, defining the tools and the detailed query for the agent.
│       ├── repo.py --> Repository interface for database operations and data access patterns.
│       ├── repo_models.py --> Data models and structures used by the repository pattern for database interactions.
│       ├── test_price_data.py --> A script to test fetching last day's price data for a list of ETFs from Interactive Brokers.
│       └── hedge_fund_stuff/
│           ├── hedge_fund_portfolio_construction.py --> A script containing logic for constructing a hedge fund-style portfolio.
│           └── hedge_fund_risk_management.py --> A script containing logic for managing risk in a hedge fund-style portfolio.
├── frontend/
│   ├── eslint.config.js --> ESLint configuration file for code linting and style enforcement.
│   ├── index.html --> Main HTML template file for the React application.
│   ├── package.json --> Node.js package configuration with dependencies and scripts.
│   ├── package-lock.json --> Locked versions of npm dependencies for consistent installs.
│   ├── README.md --> Frontend setup and development instructions.
│   ├── public/
│   │   └── vite.svg --> Vite logo asset for the application.
│   ├── src/
│   │   ├── App.css --> Main application CSS styles.
│   │   ├── App.tsx --> Root React component that sets up routing and main application structure.
│   │   ├── index.css --> Global CSS styles for the application.
│   │   ├── main.tsx --> Entry point for the React application.
│   │   ├── vite-env.d.ts --> TypeScript definitions for Vite environment.
│   │   ├── assets/
│   │   │   ├── bird_logo_bg.png --> Bird logo with background for branding.
│   │   │   ├── bird_logo.png --> Bird logo without background.
│   │   │   ├── logo_bg.png --> Main logo with background.
│   │   │   ├── logo_smaller.png --> Smaller version of the main logo.
│   │   │   ├── logo.png --> Main application logo.
│   │   │   ├── react.svg --> React framework logo.
│   │   │   └── logos/
│   │   │       ├── ibkr-logo.png --> Interactive Brokers logo.
│   │   │       ├── icons8-amazon-48.png --> Amazon company icon.
│   │   │       ├── icons8-apple-logo-48.png --> Apple company icon.
│   │   │       ├── icons8-chatgpt-50.png --> ChatGPT AI model icon.
│   │   │       ├── icons8-deepseek-48.png --> DeepSeek AI model icon.
│   │   │       ├── icons8-google-logo-48.png --> Google company icon.
│   │   │       ├── icons8-grok-48.png --> Grok AI model icon.
│   │   │       └── icons8-nvidia-48.png --> NVIDIA company icon.
│   │   └── components/
│   │       ├── AiInsightsPage.css --> Styles for the AI Insights page component.
│   │       ├── AiInsightsPage.tsx --> React component for AI-powered portfolio insights and analysis.
│   │       ├── Dashboard.css --> Styles for the main dashboard component.
│   │       ├── Dashboard.tsx --> Main dashboard React component showing portfolio overview.
│   │       ├── Login.css --> Styles for the login page component.
│   │       ├── Login.tsx --> User authentication and login React component.
│   │       ├── Optimize.css --> Styles for the portfolio optimization page.
│   │       ├── Optimize.tsx --> React component for running portfolio optimization workflows.
│   │       ├── Portfolio.css --> Styles for the portfolio view component.
│   │       ├── Portfolio.tsx --> React component for displaying detailed portfolio information.
│   │       ├── ProphitAlts.css --> Styles for the alternative investments page.
│   │       ├── ProphitAlts.tsx --> React component for alternative investment options and analysis.
│   │       ├── ProphitGpt.css --> Styles for the AI chat interface.
│   │       └── ProphitGpt.tsx --> React component for the AI chat interface with financial tools.
│   ├── tsconfig.app.json --> TypeScript configuration for the main application.
│   ├── tsconfig.json --> Base TypeScript configuration file.
│   ├── tsconfig.node.json --> TypeScript configuration for Node.js tooling.
│   └── vite.config.ts --> Vite build tool configuration file.
├── file_structure.md --> This file, documenting the project structure and file purposes.
├── prompt_testing.md --> Documentation for testing AI prompts and model interactions.
├── README.md --> Main project documentation with setup and usage instructions.
├── requirements.txt --> Python dependencies list for the backend application.
└── roadmap.md --> Project roadmap and future development plans.