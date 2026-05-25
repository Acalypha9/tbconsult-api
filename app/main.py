from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.exceptions import TriageServiceError
from app.db.session import async_engine
from app.api.routes.medication import router as medication_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logger = logging.getLogger("app.main")
    from app.db.models import Base
    try:
        # Tables should be created via alembic migrations, not startup auto-creation
        logger.info("Database connection initialized.")
    except Exception as e:
        logger.warning(
            f"Database connection failed: {e}. Running server in degraded/offline-database mode."
        )
    yield
    try:
        await async_engine.dispose()
    except Exception:
        pass

app = FastAPI(
    title="TBConsult Backend",
    description="TB Medical Triage Chatbot Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")
app.include_router(medication_router, prefix="/v1")

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

# Root /health removed — use /v1/health which checks DB connectivity