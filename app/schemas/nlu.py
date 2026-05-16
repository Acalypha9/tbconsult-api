from pydantic import BaseModel
from typing import Optional

class ExtractedSymptom(BaseModel):
    name: str
    present: bool
    duration: Optional[str] = None
    severity: Optional[str] = None

class NLUExtraction(BaseModel):
    symptoms: list[ExtractedSymptom]
    negations: list[str]
    age: Optional[str] = None
    location: Optional[str] = None
    additional_context: Optional[str] = None