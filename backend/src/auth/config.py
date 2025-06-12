import os
from dotenv import load_dotenv
from workos import WorkOSClient

load_dotenv()

# Initialize WorkOS client
workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"),
    client_id=os.getenv("WORKOS_CLIENT_ID")
)

# Configuration
REDIRECT_URI = os.getenv("WORKOS_REDIRECT_URI")
COOKIE_PASSWORD = os.getenv("WORKOS_COOKIE_PASSWORD")