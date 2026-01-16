import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_stock_excel(filename="mock_stock_data.xlsx", num_days=100):
    tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    data = []

    # Generate dates for the last X days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='B') # Business days

    for ticker in tickers:
        # Starting price for the simulation
        current_price = np.random.uniform(100, 500)
        
        for date in date_range:
            # Simulate a daily price walk (random walk)
            change = np.random.normal(0, 0.02) # 2% standard deviation
            open_p = current_price * (1 + change)
            close_p = open_p * (1 + np.random.normal(0, 0.01))
            high_p = max(open_p, close_p) * (1 + abs(np.random.normal(0, 0.005)))
            low_p = min(open_p, close_p) * (1 - abs(np.random.normal(0, 0.005)))
            volume = np.random.randint(1000000, 10000000)

            data.append([
                ticker, 
                date.strftime('%Y-%m-%d'), 
                round(open_p, 2), 
                round(high_p, 2), 
                round(low_p, 2), 
                round(close_p, 2), 
                volume
            ])
            current_price = close_p # Next day starts where today ended

    # Create DataFrame
    df = pd.DataFrame(data, columns=["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"])

    # Save to Excel
    df.to_excel(filename, index=False)
    print(f"Successfully created '{filename}' with {len(df)} rows.")

if __name__ == "__main__":
    generate_mock_stock_excel()