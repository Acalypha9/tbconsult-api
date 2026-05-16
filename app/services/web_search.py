import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.endpoint = "https://api.tavily.com/search"
        self.allowed_domains = ["cdc.gov", "who.int", "nih.gov"]

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set, skipping web search")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "include_domains": self.allowed_domains,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False
        }

        try:
            timeout = settings.WEB_SEARCH_TIMEOUT_MS / 1000.0
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0)
                    })
                
                return results
        except httpx.HTTPError as e:
            logger.error(f"Tavily web search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in web search: {e}")
            return []

web_search_service = WebSearchService()
