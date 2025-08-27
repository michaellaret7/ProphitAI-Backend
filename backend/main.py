import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.api.portfolio import router as portfolio_router
from backend.src.api.prophitgpt import router as prophitgpt_router
from backend.src.api.runner import router as runner_router
from backend.src.auth.sso import router as auth_router

app = FastAPI(title="ProphitAI API", version="1.0.0")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(portfolio_router, prefix="/api")
app.include_router(prophitgpt_router, prefix="/api")
app.include_router(runner_router, prefix="/api")
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "ProphitAI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 