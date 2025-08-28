import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.auth.sso import router as auth_router
from backend.src.api.user import router as user_router
from backend.src.api.prophit_alts import router as prophit_alts_router

app = FastAPI(title="ProphitAI API", version="1.0.0")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api/auth")
app.include_router(user_router, prefix="/api/user")
app.include_router(prophit_alts_router, prefix="/api/prophit-alts")

@app.get("/")
async def root():
    return {"message": "ProphitAI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 