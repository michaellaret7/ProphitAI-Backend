"""
ProphitAI API entrypoint.

Thin runner that imports the FastAPI app and starts uvicorn.
Run with: uvicorn prophitai_api.app:app --host 0.0.0.0 --port 8000
"""

import uvicorn
from prophitai_api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
