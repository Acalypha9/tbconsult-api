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
from app.graph.nodes.tool_execution import execute_tools

def should_extract(state: TriageState) -> str:
    if state.get("is_red_flag"):
        return "end"
    return "nlu_extraction"

def should_retrieve(state: TriageState) -> str:
    from app.graph.nodes.generate import _count_bot_turns, _is_informational_question, _is_hospital_query
    
    user_msg = state.get("user_message", "")
    if _is_hospital_query(user_msg):
        return "generate"
        
    if _is_informational_question(user_msg):
        return "retrieval"
        
    bot_turns = _count_bot_turns(state.get("chat_history", []))
    if bot_turns < 5:
        return "generate"
    return "retrieval"

def should_search_web(state: TriageState) -> str:
    retrieved_docs = state.get("retrieved_docs", [])
    if len(retrieved_docs) < 3:
        return "web_search"
    return "rerank"

def should_execute_tools(state: TriageState) -> str:
    if state.get("tool_calls"):
        return "tool_execution"
    return "guardrail"

workflow = StateGraph(TriageState)

workflow.add_node("red_flag_check", detect_red_flags)
workflow.add_node("nlu_extraction", extract_entities)
workflow.add_node("retrieval", retrieve_documents)
workflow.add_node("web_search", search_web)
workflow.add_node("rerank", rerank_documents)
workflow.add_node("tool_execution", execute_tools)
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

workflow.add_conditional_edges(
    "nlu_extraction",
    should_retrieve,
    {
        "generate": "generate",
        "retrieval": "retrieval"
    }
)

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

workflow.add_conditional_edges(
    "generate",
    should_execute_tools,
    {
        "tool_execution": "tool_execution",
        "guardrail": "guardrail" 
    }
)

workflow.add_edge("tool_execution", "generate")
workflow.add_edge("guardrail", END)

graph = workflow.compile()

async def run_triage(
    user_message: str,
    session_id: str,
    db=None,
    chat_history: list[dict] = None,
    latitude: float = None,
    longitude: float = None,
) -> TriageState:
    initial_state = {
        "user_message": user_message,
        "session_id": session_id,
        "processing_start_ms": int(time.time() * 1000),
        "db_session": db,
        "chat_history": chat_history or [],
        "latitude": latitude,
        "longitude": longitude,
    }
    
    result = await graph.ainvoke(initial_state)
    
    if result.get("is_red_flag"):
        from app.graph.nodes.generate import _detect_indonesian
        is_indonesian = _detect_indonesian(user_message)
        
        response_text = (
            "DARURAT: Gejala Anda menunjukkan kemungkinan kondisi darurat medis. Silakan segera kunjungi unit gawat darurat terdekat atau hubungi layanan darurat."
            if is_indonesian else
            "URGENT: Your symptoms indicate a potential medical emergency. Please visit the nearest emergency room or contact emergency services immediately."
        )
        
        next_steps = ["Segera kunjungi unit gawat darurat"] if is_indonesian else ["Visit emergency room immediately"]
        button_label = "Cari Rumah Sakit Terdekat" if is_indonesian else "Find Nearest Hospital"
        
        result["response_text"] = response_text
        result["triage_decision"] = {
            "risk_level": "High",
            "next_steps": next_steps,
            "requires_immediate_attention": True
        }
        result["sdui_components"] = [
            {
                "type": "button",
                "label": button_label,
                "action": "visit_dots"
            }
        ]
        
    return result
