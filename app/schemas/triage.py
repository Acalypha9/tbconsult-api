from pydantic import BaseModel, Field
from typing import Literal, Optional

class TriageDecision(BaseModel):
    needs_more_info: bool = Field(
        default=False,
        description="Set to true ONLY if critical information is still missing after the interview phase and you need to ask one more question before making a confident assessment. Maximum 10 total questions."
    )
    interview_question: str = Field(
        default="",
        description="When needs_more_info is true, provide exactly ONE short follow-up question here in the patient's language. Leave empty when needs_more_info is false."
    )
    risk_level: Literal["Low", "Moderate", "High"] = Field(
        description="The assessed risk level of the patient based on their symptoms and history."
    )
    reasons: list[str] = Field(
        ...,
        description="EXACTLY THREE short strings in the patient's language: 1) A direct symptom-based assessment (e.g. 'Your current symptoms do not match the typical pattern for Tuberculosis (TB).'), 2) A list/summary of current symptoms (e.g. 'A cold and a 5-day cough.'), 3) An explanation of the presence/absence of high-risk indicators (e.g. 'You have no accompanying symptoms commonly linked to TB, such as night sweats, unexplained weight loss, or a persistent fever.'). Do NOT include prefixes like 'Current Symptoms:' or 'Absence of High-Risk Indicators:'."
    )
    next_steps: list[str] = Field(
        ...,
        description="Actionable, friendly and informal next steps for the user to take. Keep them detailed but friendly/informal, formatted like 'Title: Description' (e.g. 'Monitor Your Symptoms: Keep an eye on how you feel...'). Provide 2-3 items in the patient's language."
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
