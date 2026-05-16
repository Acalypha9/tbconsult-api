from app.graph.nodes.red_flag import detect_red_flags

def _make_state(message: str) -> dict:
    return {"user_message": message, "session_id": "test"}

def test_red_flag_hemoptysis():
    result = detect_red_flags(_make_state("I am coughing up blood"))
    assert result["is_red_flag"] is True
    assert "coughing up blood" in result["red_flags"]

def test_red_flag_chest_pain():
    result = detect_red_flags(_make_state("chest pain when breathing"))
    assert result["is_red_flag"] is True

def test_red_flag_dyspnea():
    result = detect_red_flags(_make_state("I can't breathe"))
    assert result["is_red_flag"] is True

def test_red_flag_indonesian_batuk_darah():
    result = detect_red_flags(_make_state("batuk darah"))
    assert result["is_red_flag"] is True

def test_red_flag_indonesian_sesak_napas():
    result = detect_red_flags(_make_state("sesak napas"))
    assert result["is_red_flag"] is True

def test_no_red_flag_mild_cough():
    result = detect_red_flags(_make_state("I have a mild cough"))
    assert result["is_red_flag"] is False
    assert result["red_flags"] == []

def test_no_red_flag_past_fever():
    result = detect_red_flags(_make_state("I had a fever last week but it's gone"))
    assert result["is_red_flag"] is False

def test_no_red_flag_headache():
    result = detect_red_flags(_make_state("headache and runny nose"))
    assert result["is_red_flag"] is False

def test_red_flag_multiple():
    result = detect_red_flags(_make_state("I'm coughing blood and can't breathe"))
    assert result["is_red_flag"] is True
    assert len(result["red_flags"]) >= 2

def test_red_flag_indonesian_demam_tinggi():
    result = detect_red_flags(_make_state("demam tinggi dan lemas"))
    assert result["is_red_flag"] is True

def test_edge_case_empty_string():
    result = detect_red_flags(_make_state(""))
    assert result["is_red_flag"] is False

def test_edge_case_very_long_input():
    result = detect_red_flags(_make_state("a" * 10000))
    assert result["is_red_flag"] is False

def test_edge_case_special_characters():
    result = detect_red_flags(_make_state("!@#$%^&*()"))
    assert result["is_red_flag"] is False

def test_red_flag_mixed_case():
    result = detect_red_flags(_make_state("CoUgHiNg Up BlOoD"))
    assert result["is_red_flag"] is True

def test_red_flag_with_punctuation():
    result = detect_red_flags(_make_state("I am coughing up blood!!!"))
    assert result["is_red_flag"] is True

def test_red_flag_indonesian_nyeri_dada():
    result = detect_red_flags(_make_state("nyeri dada"))
    assert result["is_red_flag"] is True

def test_no_red_flag_tired():
    result = detect_red_flags(_make_state("I feel very tired today"))
    assert result["is_red_flag"] is False
