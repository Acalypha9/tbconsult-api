import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.api import ChatRequest, ChatResponse
from app.graph.workflow import run_triage
from app.services.audit import AuditService
from app.core.exceptions import LLMUnavailableError, RetrievalError
from app.api.deps import get_current_user
from app.db.session import get_db

router = APIRouter()

SAFE_FALLBACK_MESSAGE = (
    "Our triage system is currently experiencing issues. "
    "If you are having severe symptoms such as coughing blood, "
    "difficulty breathing, or chest pain, please seek immediate "
    "medical attention at your nearest health facility."
)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process user message through TB triage pipeline and return structured response."""
    start_time = time.time()
    session_id = request.session_id or "anonymous"

    try:
        state = await run_triage(request.message, session_id)
        processing_time_ms = int((time.time() - start_time) * 1000)

        triage_decision = state.get("triage_decision", {})
        risk_level = triage_decision.get("risk_level", "Low")
        red_flags = state.get("red_flags", [])
        sources = triage_decision.get("sources", [])
        response_text = state.get("response_text", "")

        if state.get("is_red_flag"):
            risk_level = "High"
            response_text = (
                "URGENT: Your symptoms indicate a potential medical emergency. "
                "Please visit the nearest emergency room or contact emergency services immediately."
            )

        response = ChatResponse(
            risk_level=risk_level,
            response_text=response_text,
            red_flags=red_flags,
            disclaimer="This is not a medical diagnosis. Please consult a healthcare professional.",
            sources=sources,
            sdui={"components": state.get("sdui_components", [])} if state.get("sdui_components") else None,
        )

        await AuditService.log_triage(
            db=db,
            session_id=session_id,
            user_query=request.message,
            extracted_entities=state.get("extracted_entities"),
            red_flags_detected=bool(red_flags),
            risk_level=risk_level,
            retrieved_doc_ids=[str(d.get("id", "")) for d in state.get("reranked_docs", []) if d.get("id")],
            llm_response=response_text,
            processing_time_ms=processing_time_ms,
        )

        return response

    except LLMUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SAFE_FALLBACK_MESSAGE,
        )

    except RetrievalError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SAFE_FALLBACK_MESSAGE,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=SAFE_FALLBACK_MESSAGE,
        )
