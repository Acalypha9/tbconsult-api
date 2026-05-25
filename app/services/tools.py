from langchain_core.tools import tool
from pydantic import BaseModel, Field

class SymptomInput(BaseModel):
    symptom: str = Field(description="The symptom to check")

@tool("check_symptom_severity", args_schema=SymptomInput)
def check_symptom_severity(symptom: str):
    """Checks the severity of a given symptom."""
    # This is a placeholder implementation.
    # In a real scenario, this would query a database or an API.
    severity_map = {
        "cough": "Low",
        "fever": "Medium",
        "chest pain": "High",
        "coughing blood": "High"
    }
    return severity_map.get(symptom.lower(), "Unknown")

# List of tools to be passed to the LLM
tools = [check_symptom_severity]
