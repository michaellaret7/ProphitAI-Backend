import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.src.auth.sso import router as auth_router
from backend.src.api.user import router as user_router
from backend.src.api.prophit_alts import router as prophit_alts_router
from backend.src.api.response_envelope import error_envelope

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

# Global exception handler for unhandled errors (keeps HTTPException defaults)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    content = error_envelope(code=500, message=f"Internal server error: {str(exc)}")
    return JSONResponse(status_code=500, content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 