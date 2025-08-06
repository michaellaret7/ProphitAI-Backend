from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers, get_price_data_15_mins
import pandas as pd
import numpy as np
from backend.src.calculations.risk_calculations.ticker_risk_calculations import calculate_up_down_beta
from scipy.spatial.distance import squareform
from scipy.cluster import hierarchy

def calculate_correlation_matrix(price_data: dict = None, start_date_str: str = None, end_date_str: str = None, frequency: str = None, tickers: list[str] = None, position_weights: dict = None):
    """
    Calculate the correlation matrix for the given price data, accounting for position sizes and directions.
    
    Parameters:
    - price_data: Dict mapping ticker symbols to price Series
    - start_date_str: Start date for the price data
    - end_date_str: End date for the price data
    - frequency: Frequency of the price data
    - tickers: List of ticker symbols
    - position_weights: Dict mapping ticker symbols to position weights (negative for short, positive for long)
    Returns:
    - pd.DataFrame: Weighted correlation matrix accounting for position sizes and directions
    """

    if not price_data:
        price_data = fetch_bulk_price_data_for_tickers(tickers=tickers, start_date_str=start_date_str, end_date_str=end_date_str, frequency=frequency)

    # Convert dict of Series to DataFrame
    price_df = pd.DataFrame(price_data)
    
    # Calculate returns for correlation (using percentage change)
    returns_df = price_df.pct_change().dropna()
    
    # Calculate correlation matrix
    correlation_matrix = returns_df.corr()

    # Apply position weights if provided
    if position_weights:
        # Ensure all tickers in correlation matrix have weights
        for ticker in correlation_matrix.columns:
            if ticker not in position_weights:
                position_weights[ticker] = 0
        
        # Create weight adjustment matrix
        for i, ticker_i in enumerate(correlation_matrix.columns):
            for j, ticker_j in enumerate(correlation_matrix.columns):
                if i != j:
                    weight_i = position_weights.get(ticker_i, 0)
                    weight_j = position_weights.get(ticker_j, 0)
                    
                    # Adjust correlation for long/short positions
                    # If positions have opposite signs, negate the correlation
                    if weight_i * weight_j < 0:
                        correlation_matrix.iloc[i, j] *= -1
                    
                    # Weight the correlation by absolute position sizes
                    correlation_matrix.iloc[i, j] *= abs(weight_i) * abs(weight_j)

    np.fill_diagonal(correlation_matrix.values, np.nan)
        
    return correlation_matrix

def correlation_matrix_analysis(correlation_matrix: pd.DataFrame):
    """
    Analyze the correlation matrix.
    
    Parameters:
    - correlation_matrix: pd.DataFrame - The correlation matrix to analyze
    Returns:
    - dict: Dictionary containing the analysis results
    """

    min_correlation = correlation_matrix.min().min()
    max_correlation = correlation_matrix.max().max()
    mean_correlation = correlation_matrix.mean().mean()
    std_correlation = correlation_matrix.std().std()
    
    return {
        'min_correlation': float(round(min_correlation, 4)),
        'max_correlation': float(round(max_correlation, 4)),
        'mean_correlation': float(round(mean_correlation, 4)),
        'std_correlation': float(round(std_correlation, 4))
    }

def cluster_analysis(correlation_matrix: pd.DataFrame, n_clusters: int = 3):
    """
    Perform hierarchical clustering to identify groups of correlated positions.
    
    Parameters:
    - correlation_matrix: pd.DataFrame - The correlation matrix
    - n_clusters: int - Number of clusters to identify
    Returns:
    - dict: Clusters and their risk concentration metrics
    """
    
    # Convert correlation to distance matrix
    distance_matrix = 1 - correlation_matrix.fillna(0)
    
    # Ensure diagonal is zero for squareform
    np.fill_diagonal(distance_matrix.values, 0)
    
    # Perform hierarchical clustering
    condensed_distances = squareform(distance_matrix)
    linkage_matrix = hierarchy.linkage(condensed_distances, method='average')
    
    # Get cluster assignments
    clusters = hierarchy.fcluster(linkage_matrix, n_clusters, criterion='maxclust')
    
    # Organize tickers by cluster
    tickers = correlation_matrix.columns.tolist()
    cluster_dict = {}
    for i, cluster_id in enumerate(clusters):
        if cluster_id not in cluster_dict:
            cluster_dict[cluster_id] = []
        cluster_dict[cluster_id].append(tickers[i])
    
    # Calculate within-cluster correlations
    cluster_analysis_results = {}
    for cluster_id, cluster_tickers in cluster_dict.items():
        if len(cluster_tickers) > 1:
            cluster_corr = correlation_matrix.loc[cluster_tickers, cluster_tickers]
            np.fill_diagonal(cluster_corr.values, np.nan)
            avg_corr = np.nanmean(cluster_corr.values)
            
            cluster_analysis_results[f'cluster_{cluster_id}'] = {
                'tickers': cluster_tickers,
                'size': len(cluster_tickers),
                'avg_correlation': float(round(avg_corr, 4)),
                'concentration_risk': 'High' if avg_corr > 0.6 else 'Medium' if avg_corr > 0.4 else 'Low'
            }
        else:
            cluster_analysis_results[f'cluster_{cluster_id}'] = {
                'tickers': cluster_tickers,
                'size': 1,
                'avg_correlation': None,
                'concentration_risk': 'None'
            }
    
    # Identify the highest risk cluster
    max_risk_cluster = max(cluster_analysis_results.items(), 
                           key=lambda x: x[1]['avg_correlation'] if x[1]['avg_correlation'] is not None else -1)
    
    return {
        'clusters': cluster_analysis_results,
        'highest_risk_cluster': max_risk_cluster[0],
        'total_clusters': len(cluster_dict)
    }
    
if __name__ == "__main__":
    tickers = ['SPY', 'AAPL', 'MSFT', 'META', 'NVDA', 'TSLA', 'AMZN', 'HYG']

    # correlation_matrix_low_vol = calculate_correlation_matrix(start_date_str='2023-07-01', end_date_str='2023-08-01', frequency='15mins', tickers=tickers)
    # correlation_matrix_stress = calculate_correlation_matrix(start_date_str='2023-03-09', end_date_str='2023-03-13', frequency='15mins', tickers=tickers)

    # correlation_matrix_analysis_low_vol = correlation_matrix_analysis(correlation_matrix_low_vol)
    # correlation_matrix_analysis_stress = correlation_matrix_analysis(correlation_matrix_stress)

    # print(correlation_matrix_analysis_low_vol)
    # print(correlation_matrix_analysis_stress)

    correlation_matrix_low_vol = calculate_correlation_matrix(start_date_str='2023-07-01', end_date_str='2023-08-01', frequency='15mins', tickers=tickers)
    # cluster_analysis_low_vol = cluster_analysis(correlation_matrix_low_vol)
    # print(cluster_analysis_low_vol)

    position_weights = {
        'AAPL': .1,
        'MSFT': .1,
        'TSLA': -.1,
        'META': -.1
    }
    correlation_matrix_low_vol_weighted = calculate_correlation_matrix(start_date_str='2023-07-01', end_date_str='2023-08-01', frequency='15mins', tickers=tickers, position_weights=position_weights)

    print(correlation_matrix_low_vol_weighted)



