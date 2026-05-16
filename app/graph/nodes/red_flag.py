from app.graph.state import TriageState

RED_FLAG_KEYWORDS = [
    "coughing blood", "cough blood", "hemoptysis", "blood in sputum",
    "can't breathe", "cannot breathe", "difficulty breathing", "shortness of breath", "sesak napas",
    "chest pain", "nyeri dada",
    "coughing up blood", "batuk darah",
    "confusion", "altered consciousness",
    "severe weakness", "very weak", "lemas",
    "high fever", "demam tinggi"
]

def detect_red_flags(state: TriageState) -> dict:
    user_message = state.get("user_message", "").lower()
    
    detected_flags = []
    for keyword in RED_FLAG_KEYWORDS:
        if keyword in user_message:
            detected_flags.append(keyword)
            
    return {
        "red_flags": detected_flags,
        "is_red_flag": len(detected_flags) > 0
    }
