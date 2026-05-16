from fastapi import APIRouter, Depends
from app.schemas.api import HealthResponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    Checks postgres, redis, and digitalocean inference dependencies.
    """
    dependencies = {
        "postgres": "down",
        "redis": "down",
        "digitalocean": "down"
    }
    
    # Check Postgres
    try:
        await db.execute(text("SELECT 1"))
        dependencies["postgres"] = "up"
    except Exception:
        pass
        
    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        dependencies["redis"] = "up"
        await redis_client.close()
    except Exception:
        pass
        
    # Check DigitalOcean Inference (just check if credentials exist for now to save tokens)
    try:
        if settings.DIGITALOCEAN_API_KEY:
            dependencies["digitalocean"] = "up"
    except Exception:
        pass
        
    status = "ok"
    if any(v == "down" for v in dependencies.values()):
        status = "degraded"
    if all(v == "down" for v in dependencies.values()):
        status = "down"
        
    return HealthResponse(
        status=status,
        dependencies=dependencies
    )
