import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestProphitAltsEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
    
    def test_get_fund_performance_data_with_valid_fund_name(self):
        """Test fund performance data retrieval with valid fund name"""
        response = self.client.get("/api/prophit-alts/fund/consumer_staples_fund/performance-data")
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
            
            # Check that envelope + payload structure is correct
            data = json_response["data"]
            self.assertIsInstance(data, dict)
            # envelope metadata presence
            self.assertIn("kind", data)
            self.assertIn("id", data)
            self.assertIn("selfLink", data)
            # collection counts present
            for k in ["currentItemCount", "itemsPerPage", "startIndex", "totalItems"]:
                self.assertIn(k, data)
            # payload presence
            self.assertIn("payload", data)
            payload = data.get("payload", {})
            self.assertIsInstance(payload, dict)
            self.assertIn("performanceData", payload)
            self.assertIn("metrics", payload)
            self.assertIsInstance(payload["performanceData"], list)
            if len(payload["performanceData"]) > 0:
                position = payload["performanceData"][0]
                # camelCase keys
                self.assertIn("tickerName", position)
                self.assertIn("position", position)
                self.assertIn("industry", position)
                self.assertIn("riskAllocation", position)
                self.assertIn("portfolioAllocation", position)
                # numeric types
                self.assertIsInstance(position.get("riskAllocation"), (int, float))
                self.assertIsInstance(position.get("portfolioAllocation"), (int, float))
            # metrics object exists when 200
            self.assertIn("metrics", payload)
            self.assertIsInstance(payload["metrics"], dict)
            # items removed to reduce payload size; payload is canonical
            self.assertNotIn("items", data)
        elif response.status_code == 404:
            print("Fund final positions not found - this may be expected if no positions exist")
    
    def test_get_fund_performance_data_with_invalid_fund_name(self):
        """Test fund performance data retrieval with invalid fund name"""
        response = self.client.get("/api/prophit-alts/fund/nonexistent_fund/performance-data")
        print(f"\n--- Test: Invalid Fund Name ---")
        print(f"Status Code: {response.status_code}")
        
        self.assertEqual(response.status_code, 404)
        
        json_response = response.json()
        print(f"Parsed JSON Response: {json_response}")
        self.assertIn("detail", json_response)
        # The error message should contain information about the fund
        self.assertIn("nonexistent_fund", json_response["detail"].lower())
    
    def test_get_fund_performance_data_with_empty_fund_name(self):
        """Test fund performance data retrieval with empty fund name"""
        response = self.client.get("/api/prophit-alts/fund//performance-data")
        print(f"\n--- Test: Empty Fund Name ---")
        print(f"Status Code: {response.status_code}")
        
        # This should return a 404 or 422 depending on FastAPI routing
        self.assertIn(response.status_code, [404, 422])
    
    

if __name__ == "__main__":
    unittest.main(buffer=False)
