from fastapi import APIRouter
from app.api.routes import triage, health, auth

api_router = APIRouter()
api_router.include_router(triage.router, prefix="/triage", tags=["triage"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
