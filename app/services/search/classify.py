from typing import Literal
from pydantic import BaseModel
from app.utils.gpt_parser import parse_with_gpt
from app.db.core.pull_fmp_data import FMP_API_DATA
from typing import List, Optional

class ClassificationResult(BaseModel):
    classification: Literal["Name", "Ticker", "CUSIP", "ISIN", "CIK"]

SYSTEM_PROMPT = """
Determine whether the input string is a **Name**, **Ticker**, **CUSIP**, **ISIN**, or **CIK**.

-----------------------------------------
Name (Company Name)
-----------------------------------------
• Characters: Letters only (A-Z, case-insensitive), may include spaces  
• No digits or special characters  
• Length is variable  
• Examples:
  - "Apple"
  - "Microsoft"
  - "Tesla"
  - "Johnson & Johnson"  (still treated as a Name)

-----------------------------------------
Ticker (Stock Symbol)
-----------------------------------------
• Characters: 1-5 uppercase letters (A-Z)  
• No digits (except rare foreign tickers, but exclude for this classification)  
• Typically short and fully uppercase  
• Examples:
  - "AAPL"
  - "MSFT"
  - "T"
  - "GOOG"
  - "NVDA"

-----------------------------------------
CUSIP (U.S. Securities Identifier)
-----------------------------------------
• Characters: 9 total (but input may be 6-9 during lookup)  
• Pattern: Combination of digits + uppercase letters  
• Typically:
  - Positions 1-6: issuer code (can include letters or digits)
  - Positions 7-8: issue number (digits or letters)
  - Position 9: check digit (digit or X)
• Examples:
  - "037833100"
  - "594918104"
  - "17275R102"
  - "023135106"
  - Short/partial lookup forms:
    - "037833"
    - "59491810"

-----------------------------------------
ISIN (International Securities Identification Number)
-----------------------------------------
• Characters: Always 12 total  
• Pattern:
  - 2 letters (country code: US, GB, CA, etc.)
  - 9 alphanumeric characters (often derived from CUSIP or SEDOL)
  - 1 check digit (digit)
• No spaces or punctuation  
• Examples:
  - "US0378331005"
  - "US5949181045"
  - "GB0002634946"
  - "CA0641491075"

-----------------------------------------
CIK (SEC Central Index Key)
-----------------------------------------
• Characters: Digits only  
• Length: 8-10 digits  
• No letters, no punctuation  
• Leading zeros are common  
• Examples:
  - "0000320193"  (Apple)
  - "0000789019"  (Microsoft)
  - "0001652044"  (Alphabet)
  - "0001067983"  (NVIDIA)

-----------------------------------------
Return ONLY the type: Name, Ticker, CUSIP, ISIN, or CIK.
"""

class SearchService:
    def __init__(self):
        self.fmp = FMP_API_DATA()

    @staticmethod
    def verify_type(input: str) -> ClassificationResult:
        return parse_with_gpt(query=input, target_model=ClassificationResult, system_prompt=SYSTEM_PROMPT)
    
    def search(self, input: str):
        # 1. Get the Pydantic model instance
        result_model = SearchService.verify_type(input)
        
        # 2. Access the actual string value using .classification
        classification_str = result_model.classification

        if classification_str == "Ticker":
            return self.fmp.search_by_symbol(input)
        elif classification_str == "CUSIP":
            return self.fmp.search_by_cusip(input)
        elif classification_str == "ISIN":
            return self.fmp.search_by_isin(input)
        elif classification_str == "CIK":
            return self.fmp.search_by_cik(input)
        else:
            return self.fmp.search_by_name(input)
    
    def get_ticker_search_results(self, input: str):
        return self.fmp.search_by_symbol(input)

    def get_cusip_search_results(self, input: str):
        return self.fmp.search_by_cusip(input)

    def get_isin_search_results(self, input: str):
        return self.fmp.search_by_isin(input)

    def get_cik_search_results(self, input: str):
        return self.fmp.search_by_cik(input)

    def get_name_search_results(self, input: str):
        return self.fmp.search_by_name(input)



if __name__ == "__main__":
    search_service = SearchService()
    print(search_service.search(input="AAPL"))
    print(search_service.get_ticker_search_results(input="AAPL"))
    print(search_service.get_cusip_search_results(input="037833100"))
    print(search_service.get_isin_search_results(input="US0378331005"))
    print(search_service.get_cik_search_results(input="0000320193"))
    print(search_service.get_name_search_results(input="Apple"))

