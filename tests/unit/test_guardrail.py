from app.graph.nodes.guardrail import validate_output

def _make_state(response_text: str, risk_level: str = "Low", next_steps: list | None = None) -> dict:
    return {
        "user_message": "test",
        "session_id": "123",
        "triage_decision": {
            "risk_level": risk_level,
            "next_steps": next_steps or ["Rest"],
        },
        "response_text": response_text,
    }

def test_valid_response():
    state = _make_state("You seem to have a mild cough. [Source 1] Rest is advised.", risk_level="Low", next_steps=["Rest"])
    result = validate_output(state)
    assert "mild cough" in result["response_text"]

def test_diagnosis_language_tb():
    state = _make_state("Based on your symptoms, you have tb.", risk_level="High", next_steps=["See doctor"])
    result = validate_output(state)
    assert "you have tb" not in result["response_text"].lower()

def test_diagnosis_language_diagnosed():
    state = _make_state("You are diagnosed with tuberculosis.", risk_level="High", next_steps=["See doctor"])
    result = validate_output(state)
    assert "diagnosed with" not in result["response_text"].lower()

def test_missing_risk_level():
    state = _make_state("Take some rest. [Source 1] Good.", risk_level="invalid")
    result = validate_output(state)
    assert result["triage_decision"]["risk_level"] == "Low"

def test_empty_next_steps():
    state = _make_state("Take some rest. [Source 1] Good.", next_steps=[])
    result = validate_output(state)
    assert len(result["triage_decision"]["next_steps"]) > 0

def test_no_source_citation():
    state = _make_state("You have a mild cough. Rest advised.", risk_level="Low", next_steps=["Rest"])
    result = validate_output(state)
    # Without [Source N], guardrail replaces with safe response
    assert "consult a healthcare professional" in result["response_text"].lower()
