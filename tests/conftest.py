import pytest
from httpx import AsyncClient, ASGITransport
from app.schemas.api import ChatRequest

@pytest.fixture
def app():
    from app.main import app as fastapi_app
    return fastapi_app

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_chat_request():
    return ChatRequest(
        session_id="test_session",
        message="I have a mild cough."
    )

@pytest.fixture
def sample_triage_state():
    return {
        "user_message": "I have a mild cough.",
        "session_id": "test_session",
        "red_flags": [],
        "is_red_flag": False,
        "extracted_entities": {},
        "retrieved_docs": [],
        "web_results": [],
        "reranked_docs": [],
        "triage_decision": {"risk_level": "Low", "next_steps": ["Rest and drink fluids"], "sources": ["guideline.md"], "reasons": []},
        "response_text": "You seem to have a mild cough. Please rest.",
        "sdui_components": [],
        "processing_start_ms": 0,
    }
