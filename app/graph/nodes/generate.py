import logging
from app.graph.state import TriageState
from app.services.llm import llm_service
from app.schemas.triage import TriageDecision

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a tuberculosis (TB) triage assistant. You are NOT a doctor.
You MUST NOT diagnose any condition.
You MUST classify the user's situation as Low, Moderate, or High risk.
You MUST recommend next steps (e.g., "Visit a DOTS center within 24 hours").
You MUST cite sources for every medical claim using [Source N] format.
You MUST separate "possible risk" from "confirmed diagnosis."
If evidence is insufficient, say so explicitly.
Do NOT provide medication dosing.
Do NOT speculate.
Respond in the same language as the user's message.
"""

async def generate_triage(state: TriageState) -> dict:
    reranked_docs = state.get("reranked_docs", [])
    
    if not reranked_docs:
        return {
            "triage_decision": {
                "risk_level": "Low",
                "next_steps": ["Please consult a healthcare professional for accurate advice."],
                "requires_immediate_attention": False
            },
            "response_text": "I don't have enough specific information to provide a detailed assessment. Please consult a healthcare professional or visit a clinic for proper evaluation.",
            "sdui_components": []
        }
        
    context_text = "\n\n".join([f"[Source {i+1}] {doc.get('text')}" for i, doc in enumerate(reranked_docs)])
    user_message = state.get("user_message", "")
    extracted_entities = state.get("extracted_entities", {})
    
    prompt = f"""
Context:
{context_text}

Extracted Entities:
{extracted_entities}

User Message:
{user_message}
"""

    try:
        schema = TriageDecision.model_json_schema()
        triage_decision = await llm_service.invoke_llm_structured(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            tool_schema=schema
        )
        
        response_text = await llm_service.invoke_llm(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            temperature=1.0
        )
        
        return {
            "triage_decision": triage_decision,
            "response_text": response_text,
            "sdui_components": []
        }
    except Exception as e:
        logger.error(f"Triage generation failed: {e}")
        return {
            "triage_decision": {
                "risk_level": "Low",
                "next_steps": ["Please consult a healthcare professional."],
                "requires_immediate_attention": False
            },
            "response_text": "I encountered an error while processing your request. Please consult a healthcare professional.",
            "sdui_components": []
        }
