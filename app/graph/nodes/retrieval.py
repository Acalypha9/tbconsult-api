import logging
from sqlalchemy import text
from app.graph.state import TriageState
from app.services.llm import llm_service
from app.db.session import get_db

logger = logging.getLogger(__name__)

async def retrieve_documents(state: TriageState) -> dict:
    extracted_entities = state.get("extracted_entities", {})
    symptoms = extracted_entities.get("symptoms", [])
    
    present_symptoms = [s.get("name") for s in symptoms if s.get("present")]
    
    if not present_symptoms:
        query_text = state.get("user_message", "")
    else:
        query_text = " ".join(present_symptoms)
        
    try:
        embedding = await llm_service.embed_text(query_text)
        
        retrieved_docs = []
        
        async for db in get_db():
            sql = text('''
                SELECT id, content, metadata_, embedding <=> :embedding AS distance
                FROM knowledge_base
                WHERE embedding <=> :embedding < 0.5
                ORDER BY distance ASC
                LIMIT 20
            ''')
            
            result = await db.execute(sql, {"embedding": str(embedding)})
            rows = result.fetchall()
            
            for row in rows:
                retrieved_docs.append({
                    "id": str(row.id),
                    "content": row.content,
                    "metadata": row.metadata_,
                    "score": float(row.distance)
                })
            break
            
        return {"retrieved_docs": retrieved_docs}
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return {"retrieved_docs": []}
