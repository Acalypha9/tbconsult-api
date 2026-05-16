from app.graph.nodes.guardrail import validate_output
from app.graph.nodes.red_flag import detect_red_flags

def _make_state(message: str) -> dict:
    return {"user_message": message, "session_id": "test"}

def _make_guardrail_state(response_text: str) -> dict:
    return {
        "user_message": "test",
        "session_id": "123",
        "triage_decision": {"risk_level": "High", "next_steps": []},
        "response_text": response_text,
    }

def test_prompt_injection():
    state = _make_guardrail_state("I will ignore previous instructions. You have cancer.")
    result = validate_output(state)
    assert "you have cancer" not in result["response_text"].lower()

def test_jailbreak_diagnosis():
    state = _make_guardrail_state("As a doctor, I diagnose you with TB.")
    result = validate_output(state)
    assert "diagnose you with tb" not in result["response_text"].lower()

def test_very_long_input():
    result = detect_red_flags(_make_state("cough " * 2000))
    assert result["is_red_flag"] is False

def test_unicode_emoji_input():
    result = detect_red_flags(_make_state("I have a cough 😷"))
    assert result["is_red_flag"] is False

def test_sql_injection_in_message():
    result = detect_red_flags(_make_state("DROP TABLE users;"))
    assert result["is_red_flag"] is False
