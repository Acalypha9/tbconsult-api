from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Any


# ── Auth Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    profile_photo: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_photo: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    history: list[ChatMessage] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ChatResponse(BaseModel):
    risk_level: str
    response_text: str
    red_flags: list[str]
    sources: list[str]
    sdui: Optional[dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    dependencies: dict[str, str]