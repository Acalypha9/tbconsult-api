import time
from langgraph.graph import StateGraph, END
from app.graph.state import TriageState
from app.graph.nodes.red_flag import detect_red_flags
from app.graph.nodes.nlu import extract_entities
from app.graph.nodes.retrieval import retrieve_documents
from app.graph.nodes.web_search import search_web
from app.graph.nodes.rerank import rerank_documents
from app.graph.nodes.generate import generate_triage
from app.graph.nodes.guardrail import validate_output

def should_extract(state: TriageState) -> str:
    if state.get("is_red_flag"):
        return "end"
    return "nlu_extraction"

def should_search_web(state: TriageState) -> str:
    retrieved_docs = state.get("retrieved_docs", [])
    if len(retrieved_docs) < 3:
        return "web_search"
    return "rerank"

workflow = StateGraph(TriageState)

workflow.add_node("red_flag_check", detect_red_flags)
workflow.add_node("nlu_extraction", extract_entities)
workflow.add_node("retrieval", retrieve_documents)
workflow.add_node("web_search", search_web)
workflow.add_node("rerank", rerank_documents)
workflow.add_node("generate", generate_triage)
workflow.add_node("guardrail", validate_output)

workflow.set_entry_point("red_flag_check")

workflow.add_conditional_edges(
    "red_flag_check",
    should_extract,
    {
        "end": END,
        "nlu_extraction": "nlu_extraction"
    }
)

workflow.add_edge("nlu_extraction", "retrieval")

workflow.add_conditional_edges(
    "retrieval",
    should_search_web,
    {
        "web_search": "web_search",
        "rerank": "rerank"
    }
)

workflow.add_edge("web_search", "rerank")
workflow.add_edge("rerank", "generate")
workflow.add_edge("generate", "guardrail")
workflow.add_edge("guardrail", END)

graph = workflow.compile()

async def run_triage(user_message: str, session_id: str) -> TriageState:
    initial_state = {
        "user_message": user_message,
        "session_id": session_id,
        "processing_start_ms": int(time.time() * 1000)
    }
    
    result = await graph.ainvoke(initial_state)
    
    if result.get("is_red_flag"):
        result["response_text"] = "URGENT: Your symptoms indicate a potential medical emergency. Please visit the nearest emergency room or contact emergency services immediately."
        result["triage_decision"] = {
            "risk_level": "High",
            "next_steps": ["Visit emergency room immediately"],
            "requires_immediate_attention": True
        }
        
    return result
