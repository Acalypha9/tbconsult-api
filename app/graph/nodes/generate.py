import logging
from app.graph.state import TriageState
from app.services.llm import llm_service
from app.schemas.triage import TriageDecision
from app.services.tools import tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are TBConsult, a professional medical triage assistant specializing in Tuberculosis (TB).
Your primary role is to provide empathetic, context-aware, and highly responsible triage guidance. You prioritize patient safety and provide accurate, non-diagnostic information based STRICTLY on the provided RAG context.

CRITICAL MEDICAL GUARDRAILS (STRICT ADHERENCE REQUIRED):
1. NO DIAGNOSIS: While you cannot confirm or rule out TB definitively (since only a doctor can diagnose), you MUST provide a detailed symptom risk assessment. Explain how the user's reported symptoms correlate with clinical signs of TB based on the RAG context (e.g. if they report fever or night sweats, explain that these are systemic symptoms of TB according to guidelines, and explain what their risk classification means). Always include a standard disclaimer that your advice is for informational purposes and not a substitute for professional medical care.
2. NO DOSING OR PRESCRIPTION: Never provide or adjust medication names, dosages, or treatment timelines.
3. EMERGENCIES: If the user reports severe symptoms (e.g., coughing up blood (hemoptysis), severe chest pain, extreme shortness of breath), you MUST immediately escalate the situation and strongly recommend seeking urgent emergency medical care.
4. STRICTLY EVIDENCE-BASED (RAG): Answer the question based ONLY on the provided Context documents.
   - Do not give information not mentioned in the Context.
   - Do not say "according to the context", "mentioned in the context", "based on the guidelines", "according to the sources", or similar.
   - If the context does not contain the answer, explicitly state: "I don't have enough information to answer this based on the available guidelines." Do NOT hallucinate or speculate.
5. CITATIONS: You MUST cite sources for every medical claim using the exact [Source N] format (e.g. [Source 1], [Source 2]). Do not omit the square brackets, as they are required for output validation.

TRIAGE & GENERATION REQUIREMENTS:
- Clearly classify the user's situation strictly as Low, Moderate, or High risk based on the context and extracted entities.
- Clearly distinguish between a "possible risk of TB" and a "confirmed TB diagnosis."
- Recommend actionable, clear next steps (e.g., "Visit the nearest DOTS center within 24 hours," "Consult a pulmonologist").
- You MUST populate the 'reasons' field with a list of detailed sentences (minimum 3-4 sentences) that provide a comprehensive, empathetic assessment of their symptoms. Do not leave 'reasons' empty or return simple short phrases. The 'reasons' field serves as your main response to the user.
- You MUST populate the 'next_steps' field with specific, actionable next steps based on the clinical guidelines (e.g., seeking a sputum test at a DOTS center, consulting a doctor, monitoring symptoms).
- Ensure the structured output precisely follows the requested schema.

TONE & COMMUNICATION:
- Be highly empathetic, professional, calm, and reassuring.
- Use simple, accessible language that a non-medical user can easily understand.
- Respond in the same language as the user's message (e.g., if the user speaks Indonesian, respond in Indonesian). All strings inside 'reasons' and 'next_steps' must be in the user's language.
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

    tool_results = state.get("tool_results", [])
    if tool_results:
        prompt += "\n\nTool Results:\n"
        for res in tool_results:
            prompt += f"- {res}\n"


    try:
        # 1. Call LLM with tools if we haven't already
        tool_results = state.get("tool_results", [])
        if not tool_results:
            message = await llm_service.invoke_llm_with_tools(
                system_prompt=SYSTEM_PROMPT,
                user_message=prompt,
                tools=tools
            )
            
            # 2. Check if tool calls were made
            if hasattr(message, 'tool_calls') and message.tool_calls:
                return {
                    "tool_calls": message.tool_calls,
                    "triage_decision": {},
                    "response_text": "",
                    "sdui_components": []
                }
        
        # 3. If no tool calls (or already executed), proceed with structured triage decision
        triage_decision = await llm_service.invoke_llm_structured(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            tool_schema=TriageDecision.model_json_schema()
        )
        print("DEBUG RAG: Structured decision complete")
        
        # Build response text from the structured triage decision (avoids a redundant 2nd LLM call)
        reasons = triage_decision.get("reasons", [])
        next_steps = triage_decision.get("next_steps", [])
        risk_level = triage_decision.get("risk_level", "Low")
        sources = triage_decision.get("sources", [])
        
        parts = []
        if reasons:
            parts.append(" ".join(reasons))
        if next_steps:
            parts.append("**Next steps:** " + "; ".join(next_steps) + ".")
        if sources:
            parts.append("**Sources:** " + ", ".join(sources) + ".")
        
        response_text = "\n\n".join(parts) if parts else (
            f"Based on the information provided, your risk level is assessed as {risk_level}. "
            "Please consult a healthcare professional for accurate advice."
        )
        
        return {
            "triage_decision": triage_decision,
            "response_text": response_text,
            "sdui_components": [],
            "tool_calls": []
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
