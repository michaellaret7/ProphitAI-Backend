"""
ETF Historical Event Analysis
Analyzes how ETFs performed during specific historical events
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add the backend path to sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from src.repositories.price_data import fetch_bulk_price_data_for_tickers


def analyze_etf_performance(etfs, event_name, start_date, end_date):
    """
    Analyze ETF performance during a specific event period
    
    Returns a DataFrame with performance metrics for each ETF
    """
    # Fetch price data for all ETFs
    price_data = fetch_bulk_price_data_for_tickers(etfs, start_date, end_date, frequency='daily')
    
    results = []
    
    for etf in etfs:
        if etf not in price_data:
            print(f"Warning: No data found for {etf}")
            continue
            
        prices = price_data[etf]
        
        if len(prices) < 2:
            print(f"Warning: Insufficient data for {etf}")
            continue
        
        # Calculate metrics
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]
        max_price = prices.max()
        min_price = prices.min()
        
        # Calculate percentage changes
        total_return = ((end_price - start_price) / start_price) * 100
        max_gain = ((max_price - start_price) / start_price) * 100
        max_loss = ((min_price - start_price) / start_price) * 100
        
        # Determine if it spiked up or down
        spike_direction = "UP" if max_gain > abs(max_loss) else "DOWN"
        spike_magnitude = max_gain if spike_direction == "UP" else max_loss
        
        results.append({
            'ETF': etf,
            'Start Price': round(start_price, 2),
            'End Price': round(end_price, 2),
            'Max Price': round(max_price, 2),
            'Min Price': round(min_price, 2),
            'Total Return %': round(total_return, 2),
            'Max Gain %': round(max_gain, 2),
            'Max Loss %': round(max_loss, 2),
            'Spike Direction': spike_direction,
            'Spike Magnitude %': round(spike_magnitude, 2)
        })
    
    return pd.DataFrame(results)


def main():
    # Define ETFs to analyze
    etfs = ["SPY", "QQQ", "XLF", "XLU", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY"]
    
    # Define historical events
    events = [
        {
            'name': 'Trump Tariff Crash',
            'start_date': '2025-04-02',
            'end_date': '2025-04-05'
        },
        {
            'name': 'SVB Bank Collapse',
            'start_date': '2023-03-09',
            'end_date': '2023-03-13'
        },
        {
            'name': 'Tariff Pause Relief Rally',
            'start_date': '2025-04-08',
            'end_date': '2025-04-10'
        },
        {
            'name': 'Hot CPI Shock',
            'start_date': '2022-09-12',
            'end_date': '2022-09-14'
        },
        {
            'name': 'Powell Hawkish Jackson Hole Speech',
            'start_date': '2022-08-25',
            'end_date': '2022-08-27'
        },
        {
            'name': 'Japan Nikkei Black Monday',
            'start_date': '2024-08-05',
            'end_date': '2024-08-07'
        },
    ]
    
    # Store results for dictionary output at the end
    dict_outputs = []
    
    for event in events:
        print(f"\n{'='*70}")
        print(f"Event: {event['name']}")
        print(f"Period: {event['start_date']} to {event['end_date']}")
        print('='*70)
        
        df = analyze_etf_performance(
            etfs, 
            event['name'],
            event['start_date'],
            event['end_date']
        )
        
        if not df.empty:
            # Sort by spike magnitude to show biggest movers first
            df = df.sort_values('Spike Magnitude %', key=abs, ascending=False)
            
            # Display the results
            print("\nETF Performance Summary:")
            print("-" * 70)
            
            # Create a formatted output
            for _, row in df.iterrows():
                spike_indicator = "📈" if row['Spike Direction'] == "UP" else "📉"
                print(f"\n{row['ETF']} {spike_indicator}")
                print(f"  • Start: ${row['Start Price']:.2f} → End: ${row['End Price']:.2f}")
                print(f"  • Range: ${row['Min Price']:.2f} - ${row['Max Price']:.2f}")
                print(f"  • Total Return: {row['Total Return %']:+.2f}%")
                print(f"  • {row['Spike Direction']} Spike: {row['Spike Magnitude %']:+.2f}%")
                
                # Add interpretation
                if abs(row['Spike Magnitude %']) > 5:
                    print(f"  ⚠️ SIGNIFICANT {row['Spike Direction']} MOVEMENT")
                elif abs(row['Spike Magnitude %']) > 2:
                    print(f"  • Moderate {row['Spike Direction'].lower()} movement")
                else:
                    print(f"  • Relatively stable")
            
            # Create summary table
            print("\n" + "="*70)
            print("Summary Table:")
            print(df.to_string(index=False))
            
            # Store dictionary data for later output
            dict_outputs.append({
                'event': event,
                'df': df
            })
            
        else:
            print("No data available for this period")
    
    # Print all dictionary formats at the end
    if dict_outputs:
        print("\n" + "="*70)
        print("="*70)
        print("PYTHON DICTIONARY FORMAT FOR ALL EVENTS (for scenarios.py):")
        print("="*70)
        
        for output in dict_outputs:
            event = output['event']
            df = output['df']
            
            # Create event name variable
            event_var_name = event['name'].lower().replace(' ', '_')
            print(f"\n{event_var_name} = {{")
            
            # Print each ETF and its total return in decimal format
            for _, row in df.iterrows():
                etf = row['ETF']
                # Convert percentage to decimal (e.g., -3.8% becomes -0.038)
                return_decimal = row['Total Return %'] / 100
                print(f"    '{etf}': {return_decimal:.4f},")
            
            # Add date information
            print(f"\n    'start_date': '{event['start_date']}',")
            print(f"    'end_date': '{event['end_date']}',")
            print("}")


if __name__ == "__main__":
    main()
