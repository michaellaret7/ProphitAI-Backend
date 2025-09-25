import unittest
from fastapi.testclient import TestClient
from main import app


class TestPortfolioEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_user_portfolio_list_with_valid_email(self):
        """Test user portfolio list retrieval with valid email"""
        response = self.client.get("/api/user/portfolios?email=michaellaret7@gmail.com")
        print(f"\n--- Test: Valid Email - Portfolio List ---")
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
                p = data["payload"][0]
                self.assertIn("portfolioId", p)
                self.assertIn("isCurrent", p)
        elif response.status_code == 404:
            print("User not found - this is expected for test email")

    def test_get_user_portfolio_list_without_email(self):
        """Test user portfolio list endpoint without email parameter"""
        response = self.client.get("/api/user/portfolios")
        print(f"\n--- Test: No Email Parameter - Portfolio List ---")
        print(f"Status Code: {response.status_code}")

        self.assertIn(response.status_code, [400, 404])


if __name__ == "__main__":
    unittest.main(buffer=False)
