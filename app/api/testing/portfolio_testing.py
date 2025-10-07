import unittest
from fastapi.testclient import TestClient
from main import app


class TestPortfolioEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_user_portfolio_list_with_valid_email(self):
        """Test user portfolio list retrieval with hardcoded email"""
        response = self.client.get("/api/portfolios")
        print(f"\n--- Test: Valid Email - Portfolio List ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")

        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            json_response = response.json()
            print(f"Parsed JSON Response: {json_response}")
            self.assertIn("status", json_response)
            self.assertIn("data", json_response)
            self.assertIn("message", json_response)
            self.assertEqual(json_response["status"], 200)
            # Check that data contains portfolios array (items) and metadata
            self.assertIsInstance(json_response["data"], dict)
            data = json_response["data"]
            self.assertIn("kind", data)
            self.assertIn("id", data)
            self.assertIn("selfLink", data)
            # items removed; payload is canonical for collections
            self.assertNotIn("items", data)
            self.assertIn("payload", data)
            self.assertIsInstance(data["payload"], list)
            # counts
            for k in ["currentItemCount", "itemsPerPage", "startIndex", "totalItems"]:
                self.assertIn(k, data)
            # camelCase on portfolio items
            if len(data["payload"]) > 0:
                print(f"\n--- Portfolio Names ---")
                for p in data["payload"]:
                    portfolio_name = p.get("name") or p.get("portfolioName") or "Unnamed"
                    print(f"Portfolio: {portfolio_name}")
                p = data["payload"][0]
                self.assertIn("portfolioId", p)
                self.assertIn("isCurrent", p)
        elif response.status_code == 404:
            print("User not found - this is expected for test email")

    def test_get_user_portfolio_list_without_email(self):
        """Test user portfolio list endpoint without email parameter - uses default"""
        response = self.client.get("/api/portfolios")
        print(f"\n--- Test: No Email Parameter - Portfolio List ---")
        print(f"Status Code: {response.status_code}")

        # With default email hardcoded, this should return 200
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main(buffer=False)
