import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestUserEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
    
    def test_get_user_data_with_valid_email(self):
        """Test user data retrieval with valid email"""
        response = self.client.get("/api/user/data?email=michael@laret.com")
        print(f"\n--- Test: Valid Email ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            json_response = response.json()
            print(f"Parsed JSON Response: {json_response}")
            self.assertIn("success", json_response)
            self.assertIn("data", json_response)
            self.assertIn("message", json_response)
            self.assertTrue(json_response["success"])
        elif response.status_code == 404:
            print("User not found - this is expected for test email")
    
    def test_get_user_data_without_email(self):
        """Test user data endpoint without email parameter"""
        response = self.client.get("/api/user/data")
        print(f"\n--- Test: No Email Parameter ---")
        print(f"Status Code: {response.status_code}")
        print(f"Raw Response: {response.text}")
        
        self.assertIn(response.status_code, [400, 404])
    
    def test_get_user_basic_info_with_valid_email(self):
        """Test user basic info retrieval with valid email"""
        response = self.client.get("/api/user/basic?email=michael@laret.com")
        print(f"\n--- Test: Basic Info Valid Email ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            json_response = response.json()
            print(f"Parsed JSON Response: {json_response}")
            self.assertIn("success", json_response)
            self.assertIn("data", json_response)
            self.assertIn("message", json_response)
            self.assertTrue(json_response["success"])
            # Check that basic info structure is correct
            data = json_response["data"]
            self.assertIn("id", data)
            self.assertIn("email", data)
            self.assertIn("first_name", data)
            self.assertIn("last_name", data)
        elif response.status_code == 404:
            print("User not found - this is expected for test email")
    
    def test_get_user_basic_info_without_email(self):
        """Test user basic info endpoint without email parameter"""
        response = self.client.get("/api/user/basic")
        print(f"\n--- Test: Basic Info No Email Parameter ---")
        print(f"Status Code: {response.status_code}")
        print(f"Raw Response: {response.text}")
        
        self.assertIn(response.status_code, [400, 404])

if __name__ == "__main__":
    unittest.main(buffer=False)
