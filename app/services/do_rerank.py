import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class RerankService:
    def __init__(self):
        self.api_key = settings.DIGITALOCEAN_API_KEY
        self.base_url = settings.DIGITALOCEAN_BASE_URL.rstrip('/')
        self.endpoint = f"{self.base_url}/rerank"
        self.model = settings.RERANKER_MODEL_ID

    async def rerank(self, query: str, documents: list[str], top_k: int = 5) -> list[dict]:
        if not self.api_key or not self.model:
            logger.warning("DigitalOcean credentials or Reranker model not set, skipping reranking")
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
            "return_documents": True
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Check if it's Cohere-compatible format
                if isinstance(data, dict) and "results" in data:
                    items = data["results"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                    
                results = []
                for idx, item in enumerate(items):
                    if isinstance(item, dict):
                        score = item.get("relevance_score", item.get("score", 0.0))
                        doc_text = ""
                        if "document" in item and isinstance(item["document"], dict):
                            doc_text = item["document"].get("text", documents[item.get("index", idx)])
                        else:
                            doc_text = item.get("text", documents[item.get("index", idx)])
                            
                        results.append({
                            "index": item.get("index", idx),
                            "relevance_score": score,
                            "text": doc_text
                        })
                
                # Sort and return top_k
                results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:top_k]
                return results
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Reranking request timed out or failed to connect: {e}")
            return [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:top_k])]
        except httpx.HTTPStatusError as e:
            logger.error(f"Reranking HTTP error: {e.response.status_code} - {e.response.text}")
            return [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:top_k])]
        except Exception as e:
            import traceback
            logger.error(f"Reranking failed: {repr(e)}\n{traceback.format_exc()}")
            return [{"index": i, "relevance_score": 1.0, "text": doc} for i, doc in enumerate(documents[:top_k])]

rerank_service = RerankService()
