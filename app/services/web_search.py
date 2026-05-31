import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.endpoint = "https://api.tavily.com/search"
        self.allowed_domains = ["cdc.gov", "who.int", "nih.gov"]

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        if not self.api_key:
            if self.gemini_api_key:
                logger.info("TAVILY_API_KEY not set. Using built-in Gemini search grounding fallback.")
                return await self._gemini_search(query, max_results)
            logger.warning("Neither TAVILY_API_KEY nor GEMINI_API_KEY is set, skipping web search")
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

    async def _gemini_search(self, query: str, max_results: int = 5) -> list[dict]:
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set, cannot use built-in search")
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"Search the web and list key health info about: {query}"}
                    ]
                }
            ],
            "tools": [
                {"google_search": {}}
            ]
        }

        try:
            timeout = settings.WEB_SEARCH_TIMEOUT_MS / 1000.0
            # Ensure at least 8.0s timeout for web grounding search
            timeout = max(timeout, 8.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    logger.warning("Gemini search grounding returned no candidates")
                    return []

                candidate = candidates[0]
                grounding_metadata = candidate.get("groundingMetadata", {})
                chunks = grounding_metadata.get("groundingChunks", [])
                supports = grounding_metadata.get("groundingSupports", [])

                results = []
                # Map chunk indices to supporting text segments
                chunk_contents = {}
                for support in supports:
                    segment_text = support.get("segment", {}).get("text", "")
                    for idx in support.get("groundingChunkIndices", []):
                        if idx not in chunk_contents:
                            chunk_contents[idx] = []
                        chunk_contents[idx].append(segment_text)

                for i, chunk in enumerate(chunks[:max_results]):
                    web = chunk.get("web", {})
                    if not web:
                        continue

                    # Join all matching support text segments as content, or fall back to candidate output
                    content = " ".join(chunk_contents.get(i, []))
                    if not content:
                        content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")

                    results.append({
                        "title": web.get("title", ""),
                        "url": web.get("uri", ""),
                        "content": content[:1000].strip(),
                        "score": 1.0
                    })
                return results
        except httpx.HTTPError as e:
            logger.error(f"Gemini search HTTP request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Gemini search: {e}")
            return []

web_search_service = WebSearchService()
