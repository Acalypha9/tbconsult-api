from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.core.config import settings
from app.core.exceptions import TriageServiceError
from app.db.session import async_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.models import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()

app = FastAPI(
    title="TBConsult Backend",
    description="TB Medical Triage Chatbot Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")

@app.exception_handler(TriageServiceError)
async def triage_service_exception_handler(request, exc: TriageServiceError):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Our triage system is currently experiencing issues. "
            "If you are having severe symptoms such as coughing blood, difficulty breathing, "
            "or chest pain, please seek immediate medical attention at your nearest health facility."
        },
    )

@app.get("/health")
async def root_health():
    return {"status": "ok"}