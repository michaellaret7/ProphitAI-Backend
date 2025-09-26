<p align="left">
  <img src="frontend/src/assets/logo_smaller.png" alt="ProphitAI Logo"/>
</p>

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/michaellaret7/ProphitAI)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![Frontend](https://img.shields.io/badge/frontend-React-cyan)](https://react.dev/)

> An AI-powered, comprehensive platform for institutional-grade portfolio management and optimization.

ProphitAI is a sophisticated financial tool that leverages AI to provide in-depth portfolio analysis, backtesting, and personalized optimization strategies. It's designed to help users make informed investment decisions by providing access to powerful data analysis and machine learning-driven insights.

## ✨ Key Features

-   **🤖 AI-Powered Portfolio Optimization:** Utilizes Large Language Models (LLMs) for a two-phase portfolio optimization process.
-   **📊 Comprehensive Analytics:** In-depth analysis of portfolio holdings, performance metrics, diversification, and correlation.
-   **🔬 Stress Testing:** Employs an AI agent to stress test portfolios against various market scenarios.
-   **📈 Advanced Backtesting:** Powerful backtesting engine to evaluate strategies against historical data.
-   **🔗 Interactive Brokers Integration:** Seamlessly connect your IBKR account to fetch holdings and execute trades.
-   **💬 Conversational AI:** A GPT-powered chat assistant with financial data retrieval tools to answer your questions.
-   **🛡️ Secure Authentication:** User authentication powered by WorkOS.

## 🛠️ Technology Stack

**Backend:**
-   **Framework:** FastAPI
-   **Database:** PostgreSQL
-   **ORM:** SQLAlchemy, Peewee
-   **AI & Machine Learning:** OpenAI, Pandas, Numpy, Scipy
-   **API:** RESTful API with Pydantic data validation
-   **Brokerage:** ib-insync for Interactive Brokers

**Frontend:**
-   **Framework:** React (or similar, based on `frontend` folder)
-   **Styling:** (Not specified, but could be Material-UI, TailwindCSS, etc.)

## 🏛️ High-Level Architecture

ProphitAI is built with a modern backend that serves a RESTful API to a frontend application.

-   The **backend** is a FastAPI application that handles business logic, data processing, and communication with external services like OpenAI and Interactive Brokers.
-   The **database** (PostgreSQL) stores user data, portfolio information, research reports, and market data.
-   The **AI/ML components** are integrated throughout the backend for tasks like portfolio optimization, research generation, and conversational AI.

## 🚀 Getting Started

Follow these instructions to get the ProphitAI backend up and running on your local machine.

### Prerequisites

-   Python 3.9+
-   PostgreSQL
-   An Interactive Brokers account (for live data and trading)
-   API keys for OpenAI and other services (see `.env.example`)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ProphitAI.git
    cd ProphitAI
    ```

2.  **Install backend dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the `backend` directory and populate it with your credentials. You can use `backend/.env.example` as a template.
    ```
    DB_HOST=your_db_host
    DB_USER=your_db_user  
    DB_PASSWORD=your_db_password
    DB_PORT=your_db_port
    OPENAI_API_KEY=your_openai_api_key
    # ... other variables
    ```

### Running the Application

1.  **Start the backend server:**
    ```bash
    cd backend
    python main.py
    ```
    The API will be available at `http://localhost:8000`.

2.  **API Documentation:**
    Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## 📂 Project Structure

Here's a high-level overview of the project's structure:

```
ProphitAI/
├── backend/
│   ├── src/
│   │   ├── api/             # FastAPI endpoints
│   │   ├── analysts/        # AI-powered research analysts
│   │   ├── auth/            # User authentication
│   │   ├── backtest/        # Portfolio backtesting engine
│   │   ├── data/            # Data management and database interaction
│   │   ├── portfolio_optimization/ # Core AI portfolio optimization logic
│   │   ├── prophit_gpt/   # Conversational AI assistant
│   │   └── utils/           # Shared utility functions
│   └── main.py              # Backend application entrypoint
├── frontend/
│   └── src/                 # Frontend application source code
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🗺️ Roadmap

-   [ ] **Frontend Development:** Complete the user interface for all backend features.
-   [ ] **Enhanced Data Sources:** Integrate more financial data providers.
-   [ ] **Real-time Notifications:** Implement real-time alerts for market events and portfolio changes.
-   [ ] **Advanced Risk Models:** Incorporate more sophisticated risk management models.

## 🙌 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have ideas for improvements.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 

run frontend --> npm run dev
create venv --> .venv/Scripts/Activate.ps1  
run backend --> 

Branch Strategy
main - Production-ready code
develop - Integration branch for features
feature/* - New features
fix/* - Bug fixes
docs/* - Documentation updates
refactor/* - Code refactoring
test/* - Test additions or fixes