from pydantic import BaseModel, EmailStr
from typing import Optional, Any


# ── Auth Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    risk_level: str
    response_text: str
    red_flags: list[str]
    sources: list[str]
    sdui: Optional[dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    dependencies: dict[str, str]