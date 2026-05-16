from typing import TypedDict

class TriageState(TypedDict):
    user_message: str
    session_id: str
    
    red_flags: list[str]
    is_red_flag: bool
    
    extracted_entities: dict
    
    retrieved_docs: list[dict]
    web_results: list[dict]
    
    reranked_docs: list[dict]
    
    triage_decision: dict
    response_text: str
    
    sdui_components: list[dict]
    processing_start_ms: int
