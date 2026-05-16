from typing import Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import redis.asyncio as redis
import time
from app.db.session import get_db
from app.core.security import verify_token
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    if not token:
        return {"user_id": "anonymous"}
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

async def rate_limiter(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    identifier = current_user.get("user_id", request.client.host)
    current_minute = int(time.time() / 60)
    redis_key = f"rate_limit:{identifier}:{current_minute}"

    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        count = await redis_client.incr(redis_key)
        if count == 1:
            await redis_client.expire(redis_key, 60)
        await redis_client.close()

        if count > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
    except HTTPException:
        raise
    except Exception:
        pass
