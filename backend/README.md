# ProphitAI Backend API

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env` file:
```
DB_HOST=your_db_host
DB_USER=your_db_user  
DB_PASSWORD=your_db_password
DB_PORT=your_db_port
```

## Running the API

Start the FastAPI server:
```bash
python main.py
```

The API will be available at: http://localhost:8000

## API Documentation

Interactive API documentation is available at: http://localhost:8000/docs

## Endpoints

### Portfolio Allocation
- **GET** `/api/portfolio/{user_id}/allocation`
- Returns portfolio allocation data for the specified user
- Example: `/api/portfolio/one/allocation`

## Database Schema

The API expects:
- Database name: `portfolio_results`
- Schema format: `portfolio_{user_id}` (e.g., `portfolio_one`)
- Table name: `final_portfolio`
- Required columns: `asset_class`, `allocation` 