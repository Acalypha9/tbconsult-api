from pydantic import BaseModel
from typing import Optional, Any

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    risk_level: str
    response_text: str
    red_flags: list[str]
    disclaimer: str
    sources: list[str]
    sdui: Optional[dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    dependencies: dict[str, str]