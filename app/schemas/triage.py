from pydantic import BaseModel
from typing import Literal, Optional

class TriageDecision(BaseModel):
    risk_level: Literal["Low", "Moderate", "High"]
    reasons: list[str] = []
    next_steps: list[str] = []
    sources: list[str] = []
    requires_immediate_attention: bool = False

class SDUIComponent(BaseModel):
    type: str
    label: str
    action: Optional[str] = None
    options: Optional[list[str]] = None