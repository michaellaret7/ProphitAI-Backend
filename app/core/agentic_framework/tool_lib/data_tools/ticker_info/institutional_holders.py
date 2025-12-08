from app.db.core.pull_fmp_data import FMP_API_DATA

def get_institutional_holders(ticker: str):
    """
    Retrieves institutional holders for a given ticker.
    """
    fmp_data = FMP_API_DATA()
    d = []

    for page in range(1, 10):
        data = fmp_data.get_institutional_holder_analytics(ticker, 2025, 3, page=page, limit=100)
        d.extend(data)

    return d

if __name__ == "__main__":
    data = get_institutional_holders("AAL")
    for firm in data:
        # print(firm)
        # break
        print(firm['investorName'])
    
    print(len(data))