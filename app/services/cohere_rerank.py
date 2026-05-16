import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class CohereRerankService:
    def __init__(self):
        self.api_key = settings.COHERE_API_KEY
        self.endpoint = "https://api.cohere.com/v2/rerank"
        self.model = "rerank-v3.5"

    async def rerank(self, query: str, documents: list[str], top_k: int = 5) -> list[dict]:
        if not self.api_key:
            logger.warning("COHERE_API_KEY not set, skipping reranking")
            return [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:top_k])]

        if not documents:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": top_k,
            "return_documents": True
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    score = item.get("relevance_score", 0.0)
                    if score >= 0.3:
                        results.append({
                            "index": item.get("index"),
                            "relevance_score": score,
                            "text": item.get("document", {}).get("text", "")
                        })
                
                return results
        except httpx.HTTPError as e:
            logger.error(f"Cohere rerank failed: {e}")
            return [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:top_k])]
        except Exception as e:
            logger.error(f"Unexpected error in Cohere rerank: {e}")
            return [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:top_k])]

cohere_rerank_service = CohereRerankService()
