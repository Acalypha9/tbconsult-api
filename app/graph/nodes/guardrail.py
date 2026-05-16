from app.graph.state import TriageState

DIAGNOSIS_KEYWORDS = [
    "you have tb", "you have tuberculosis", "diagnosed with",
    "you are infected", "you definitely have"
]

def validate_output(state: TriageState) -> dict:
    triage_decision = state.get("triage_decision", {})
    response_text = state.get("response_text", "")
    
    risk_level = triage_decision.get("risk_level")
    if risk_level not in ["Low", "Moderate", "High"]:
        triage_decision["risk_level"] = "Low"
        
    next_steps = triage_decision.get("next_steps", [])
    if not next_steps:
        triage_decision["next_steps"] = ["Please consult a healthcare professional."]
        
    response_lower = response_text.lower()
    has_diagnosis = any(keyword in response_lower for keyword in DIAGNOSIS_KEYWORDS)
    
    has_source = "[Source" in response_text
    
    if has_diagnosis or not has_source:
        safe_response = "Based on your symptoms, please consult a healthcare professional for a proper medical evaluation. I cannot provide a diagnosis."
        if has_source:
            safe_response += " " + " ".join([sentence for sentence in response_text.split(".") if "[Source" in sentence]) + "."
        return {
            "triage_decision": triage_decision,
            "response_text": safe_response
        }
        
    return {
        "triage_decision": triage_decision,
        "response_text": response_text
    }
