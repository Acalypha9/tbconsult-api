import logging
from app.graph.state import TriageState
from app.services.web_search import web_search_service

logger = logging.getLogger(__name__)

async def search_web(state: TriageState) -> dict:
    extracted_entities = state.get("extracted_entities", {})
    symptoms = extracted_entities.get("symptoms", [])
    
    present_symptoms = [s.get("name") for s in symptoms if s.get("present")]
    
    if not present_symptoms:
        query_text = state.get("user_message", "")
    else:
        query_text = " ".join(present_symptoms) + " tuberculosis"
        
    try:
        results = await web_search_service.search(query_text)
        return {"web_results": results}
    except Exception as e:
        logger.error(f"Web search node failed: {e}")
        return {"web_results": []}
