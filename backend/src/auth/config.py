import os
from workos import WorkOSClient
from dotenv import load_dotenv

load_dotenv()

# Initialize WorkOS client
workos_client = WorkOSClient(
    api_key=os.environ["WORKOS_API_KEY"],
    client_id=os.environ["WORKOS_CLIENT_ID"]
)

# Configuration constants
REDIRECT_URI = os.environ.get("WORKOS_REDIRECT_URI", "http://localhost:8000/auth/callback")
