"""
LearnHub LMS - Main FastAPI Application
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI(
    title="LearnHub LMS",
    description="Learning Management System with AI Tutoring",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key")
ALGORITHM = "HS256"

# ============================================
# SCHEMAS
# ============================================

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user_id: int
    username: str

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def read_root():
    return {"message": "LearnHub API is running", "status": "ok"}

@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    return LoginResponse(
        token="dummy_token_123",
        user_id=1,
        username="student1"
    )

@app.get("/courses")
def get_courses(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    return {"courses": []}

@app.get("/dashboard")
def get_dashboard(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    return {"user_id": 1, "username": "student1", "courses": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)