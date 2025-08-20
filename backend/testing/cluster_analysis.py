"""
Market Theme Identification via Clustering
==========================================
Uses hierarchical clustering to identify groups of stocks that move together,
revealing market themes and hidden relationships.

NOTE: Requires these functions in your environment:
- get_price_data_daily(ticker, start_date, end_date)
- get_price_data_15_mins(ticker, start_date, end_date)
- get_price_data_hourly(ticker, start_date, end_date)
"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers


def identify_market_themes(tickers, start_date, end_date, num_clusters=None, min_cluster_size=2):
    """
    Identify market themes by clustering stocks based on correlation.
    
    Parameters:
    -----------
    tickers : list
        List of ticker symbols
    start_date : str
        Start date 'YYYY-MM-DD'
    end_date : str
        End date 'YYYY-MM-DD'
    num_clusters : int
        Number of themes to identify (None for automatic)
    min_cluster_size : int
        Minimum stocks required to form a theme
    
    Returns:
    --------
    dict with cluster/theme information
    """
    
    # Fetch data and calculate returns
    price_data = fetch_bulk_price_data_for_tickers(tickers, start_date, end_date)
    prices_df = pd.DataFrame(price_data)
    returns = prices_df.pct_change().dropna()
    
    # Calculate correlation and distance matrices
    corr_matrix = returns.corr()
    distance_matrix = np.sqrt(0.5 * (1 - corr_matrix))
    
    # Hierarchical clustering
    condensed_dist = squareform(distance_matrix)
    linkage_matrix = linkage(condensed_dist, method='ward')
    
    # Determine clusters
    if num_clusters is None:
        num_clusters = max(3, min(int(np.sqrt(len(tickers))), 15))
    
    clusters = fcluster(linkage_matrix, num_clusters, criterion='maxclust')
    
    # Analyze each theme
    themes = {}
    for cluster_id in range(1, max(clusters) + 1):
        cluster_tickers = [t for t, c in zip(tickers, clusters) if c == cluster_id]
        
        if len(cluster_tickers) < min_cluster_size:
            continue
            
        cluster_returns = returns[cluster_tickers]
        
        # Calculate theme characteristics
        theme_stats = {
            'tickers': cluster_tickers,
            'size': len(cluster_tickers),
            'avg_correlation': cluster_returns.corr().values[np.triu_indices_from(
                cluster_returns.corr().values, k=1)].mean(),
            'avg_return': cluster_returns.mean().mean() * 252,
            'avg_volatility': cluster_returns.std().mean() * np.sqrt(252),
        }
        
        themes[f'Theme_{cluster_id}'] = theme_stats
    
    return themes, corr_matrix


def analyze_theme_relationships(themes, corr_matrix):
    """
    Analyze relationships between identified themes.
    """
    theme_correlations = []
    
    for theme1_name, theme1_data in themes.items():
        for theme2_name, theme2_data in themes.items():
            if theme1_name >= theme2_name:
                continue
            
            # Calculate average correlation between themes
            cross_correlations = []
            for t1 in theme1_data['tickers']:
                for t2 in theme2_data['tickers']:
                    cross_correlations.append(corr_matrix.loc[t1, t2])
            
            avg_cross_corr = np.mean(cross_correlations)
            theme_correlations.append({
                'theme1': theme1_name,
                'theme2': theme2_name,
                'correlation': avg_cross_corr
            })
    
    return pd.DataFrame(theme_correlations).sort_values('correlation', ascending=False)


def print_theme_analysis(tickers, start_date, end_date, num_clusters=None):
    """
    Run complete theme analysis and print results.
    """
    themes, corr_matrix = identify_market_themes(tickers, start_date, end_date, num_clusters)
    
    print("=" * 60)
    print("MARKET THEME IDENTIFICATION")
    print("=" * 60)
    print(f"Analyzed {len(tickers)} stocks")
    print(f"Identified {len(themes)} distinct themes\n")
    
    # Print each theme
    for theme_name, theme_data in themes.items():
        print(f"\n{theme_name}")
        print("-" * 30)
        print(f"Stocks ({theme_data['size']}): {', '.join(theme_data['tickers'])}")
        print(f"Internal Correlation: {theme_data['avg_correlation']:.3f}")
        print(f"Avg Annual Return: {theme_data['avg_return']:.1%}")
        print(f"Avg Annual Volatility: {theme_data['avg_volatility']:.1%}")
    
    # Print theme relationships
    theme_relationships = analyze_theme_relationships(themes, corr_matrix)
    if not theme_relationships.empty:
        print("\n" + "=" * 60)
        print("THEME RELATIONSHIPS (Cross-Theme Correlations)")
        print("=" * 60)
        for _, row in theme_relationships.head(10).iterrows():
            print(f"{row['theme1']} <-> {row['theme2']}: {row['correlation']:.3f}")
    
    # Identify most distinctive themes
    print("\n" + "=" * 60)
    print("THEME CHARACTERISTICS")
    print("=" * 60)
    
    # Find most correlated theme (tight group)
    tightest = max(themes.items(), key=lambda x: x[1]['avg_correlation'])
    print(f"Most Cohesive Theme: {tightest[0]} (correlation: {tightest[1]['avg_correlation']:.3f})")
    
    # Find highest return theme
    best_return = max(themes.items(), key=lambda x: x[1]['avg_return'])
    print(f"Best Performing Theme: {best_return[0]} (return: {best_return[1]['avg_return']:.1%})")
    
    # Find lowest volatility theme
    lowest_vol = min(themes.items(), key=lambda x: x[1]['avg_volatility'])
    print(f"Most Stable Theme: {lowest_vol[0]} (volatility: {lowest_vol[1]['avg_volatility']:.1%})")
    
    return themes


# Example usage
if __name__ == "__main__":
    # Consumer staples portfolio tickers
    tickers = [
        'CASY', 'CELH', 'ODC', 'ODD', 'PM', 'VITL', 'WMT', 'BJ', 'SFM', 'COCO', 
        'MNST', 'CL', 'IPAR', 'DOLE', 'PPC', 'INGR', 'KO', 'CENT', 'WBA', 'ANDE', 
        'TGT', 'STZ', 'PEP', 'SAM', 'MGPI', 'ENR', 'SPB', 'COTY', 'KVUE', 'REYN', 
        'EL', 'EPC', 'UVV'
    ]
    
    # Identify themes
    themes = print_theme_analysis(
        tickers=tickers,
        start_date='2022-01-01',
        end_date='2024-01-01',
        num_clusters=None  # Let algorithm decide
    )