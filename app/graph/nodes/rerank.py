import logging
from app.graph.state import TriageState
from app.services.cohere_rerank import cohere_rerank_service

logger = logging.getLogger(__name__)

async def rerank_documents(state: TriageState) -> dict:
    retrieved_docs = state.get("retrieved_docs", [])
    web_results = state.get("web_results", [])
    
    documents = []
    for doc in retrieved_docs:
        documents.append(doc.get("content", ""))
        
    for res in web_results:
        documents.append(res.get("content", ""))
        
    if not documents:
        return {"reranked_docs": []}
        
    user_message = state.get("user_message", "")
    extracted_entities = state.get("extracted_entities", {})
    symptoms = extracted_entities.get("symptoms", [])
    present_symptoms = [s.get("name") for s in symptoms if s.get("present")]
    
    query = user_message
    if present_symptoms:
        query += " " + " ".join(present_symptoms)
        
    try:
        reranked = await cohere_rerank_service.rerank(query, documents, top_k=5)
        return {"reranked_docs": reranked}
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        fallback = [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:5])]
        return {"reranked_docs": fallback}
