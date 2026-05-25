from pydantic import BaseModel, Field
from typing import Literal, Optional

class TriageDecision(BaseModel):
    risk_level: Literal["Low", "Moderate", "High"] = Field(
        description="The assessed risk level of the patient based on their symptoms and history."
    )
    reasons: list[str] = Field(
        ...,
        description="A list of detailed sentences assessing the user's symptoms, explaining how they relate to tuberculosis risk according to the context guidelines, and providing the non-diagnostic triage rationale. Must be in the user's language."
    )
    next_steps: list[str] = Field(
        ...,
        description="Actionable, clinical next steps for the user to take (e.g. visiting a DOTS center, consulting a doctor, taking a test). Must be in the user's language."
    )
    sources: list[str] = Field(
        ...,
        description="Citations/sources used to support this decision, matching the names of the source documents in the format [Source N]."
    )
    requires_immediate_attention: bool = Field(
        default=False,
        description="Whether the user needs immediate emergency medical attention."
    )

class SDUIComponent(BaseModel):
    type: str
    label: str
    action: Optional[str] = None
    options: Optional[list[str]] = None