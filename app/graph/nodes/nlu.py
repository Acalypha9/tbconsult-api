import logging
from app.graph.state import TriageState
from app.services.llm import llm_service
from app.schemas.nlu import NLUExtraction

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a medical natural language understanding (NLU) assistant specializing in tuberculosis (TB).
Your task is to extract structured clinical entities from the user's message.

Instructions:
1. Extract symptoms with their present/absent status.
2. Map colloquialisms and Indonesian terms to standard clinical terms (e.g., "batuk" -> "cough", "keringat malam" -> "night sweats").
3. Extract duration, age, and location if mentioned.
4. Handle negation correctly (e.g., "I do NOT have fever" -> {name: "fever", present: false}).
"""

async def extract_entities(state: TriageState) -> dict:
    user_message = state.get("user_message", "")
    
    try:
        schema = NLUExtraction.model_json_schema()
        extracted_data = await llm_service.invoke_llm_structured(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            tool_schema=schema
        )
        return {"extracted_entities": extracted_data}
    except Exception as e:
        logger.error(f"NLU extraction failed: {e}")
        return {"extracted_entities": {}}
