from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
import time
from app.core.config import settings
from app.core.security import verify_token

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Redis-based rate limiting middleware.
        """
        # Skip rate limiting for health check
        if request.url.path == "/v1/health":
            return await call_next(request)
            
        # Extract user identifier
        identifier = request.client.host
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_token(token)
            if payload and "user_id" in payload:
                identifier = payload["user_id"]
                
        current_minute = int(time.time() / 60)
        redis_key = f"rate_limit:{identifier}:{current_minute}"
        
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            count = await redis_client.incr(redis_key)
            if count == 1:
                await redis_client.expire(redis_key, 60)
                
            await redis_client.close()
            
            if count > settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"}
                )
        except Exception:
            # Graceful degradation: if Redis is down, allow the request
            pass
            
        response = await call_next(request)
        return response
