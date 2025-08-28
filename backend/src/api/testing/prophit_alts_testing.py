import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestProphitAltsEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
    
    def test_get_fund_final_positions_with_valid_fund_name(self):
        """Test fund final positions retrieval with valid fund name"""
        response = self.client.get("/api/prophit-alts/fund/consumer_staples_fund/final-positions")
        print(f"\n--- Test: Valid Fund Name ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            json_response = response.json()
            print(f"Parsed JSON Response: {json_response}")
            self.assertIn("status", json_response)
            self.assertIn("data", json_response)
            self.assertIn("message", json_response)
            self.assertEqual(json_response["status"], 200)
            
            # Check that positions data structure is correct
            data = json_response["data"]
            self.assertIsInstance(data, list)
            if len(data) > 0:
                position = data[0]
                self.assertIn("id", position)
                self.assertIn("fund_id", position)
                self.assertIn("ticker_name", position)
                self.assertIn("position", position)
                self.assertIn("industry", position)
                self.assertIn("risk_allocation", position)
                self.assertIn("portfolio_allocation", position)
                self.assertIn("reasoning", position)
                self.assertIn("date_created", position)
                self.assertIn("date_updated", position)
        elif response.status_code == 404:
            print("Fund final positions not found - this may be expected if no positions exist")
    
    def test_get_fund_final_positions_with_invalid_fund_name(self):
        """Test fund final positions retrieval with invalid fund name"""
        response = self.client.get("/api/prophit-alts/fund/nonexistent_fund/final-positions")
        print(f"\n--- Test: Invalid Fund Name ---")
        print(f"Status Code: {response.status_code}")
        
        self.assertEqual(response.status_code, 404)
        
        json_response = response.json()
        print(f"Parsed JSON Response: {json_response}")
        self.assertIn("detail", json_response)
        # The error message should contain information about the fund
        self.assertIn("nonexistent_fund", json_response["detail"].lower())
    
    def test_get_fund_final_positions_with_empty_fund_name(self):
        """Test fund final positions retrieval with empty fund name"""
        response = self.client.get("/api/prophit-alts/fund//final-positions")
        print(f"\n--- Test: Empty Fund Name ---")
        print(f"Status Code: {response.status_code}")
        
        # This should return a 404 or 422 depending on FastAPI routing
        self.assertIn(response.status_code, [404, 422])
    
    def test_get_fund_landing_page_metrics_with_valid_fund_name(self):
        """Test fund metrics retrieval with valid fund name"""
        response = self.client.get("/api/prophit-alts/fund/consumer_staples_fund/metrics")
        print(f"\n--- Test: Fund Metrics Valid Fund Name ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            json_response = response.json()
            print(f"Parsed JSON Response: {json_response}")
            self.assertIn("status", json_response)
            self.assertIn("data", json_response)
            self.assertIn("message", json_response)
            self.assertEqual(json_response["status"], 200)
            
            # Check that metrics data structure is correct
            metrics = json_response["data"]
            self.assertIsInstance(metrics, dict)
            
            # Verify all expected metrics are present
            expected_metrics = [
                "ytd_return", "gross_exposure", "net_exposure",
                "sharpe_ratio", "sortino_ratio", "max_drawdown",
                "beta", "var_95"
            ]
            for metric in expected_metrics:
                self.assertIn(metric, metrics, f"Missing metric: {metric}")
                
        elif response.status_code == 404:
            print("Fund metrics not found - this may be expected if fund doesn't exist")
    
    def test_get_fund_landing_page_metrics_with_invalid_fund_name(self):
        """Test fund metrics retrieval with invalid fund name"""
        response = self.client.get("/api/prophit-alts/fund/nonexistent_fund/metrics")
        print(f"\n--- Test: Fund Metrics Invalid Fund Name ---")
        print(f"Status Code: {response.status_code}")
        
        self.assertIn(response.status_code, [404, 500])
        
        json_response = response.json()
        print(f"Parsed JSON Response: {json_response}")
        self.assertIn("detail", json_response)

if __name__ == "__main__":
    unittest.main(buffer=False)
