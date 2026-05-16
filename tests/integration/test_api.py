import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_chat_valid_message(client: AsyncClient):
    mock_state = {
        "user_message": "I have a mild cough",
        "session_id": "test_session",
        "red_flags": [],
        "is_red_flag": False,
        "extracted_entities": {},
        "retrieved_docs": [],
        "web_results": [],
        "reranked_docs": [],
        "triage_decision": {"risk_level": "Low", "next_steps": ["Rest"], "sources": [], "reasons": []},
        "response_text": "You have a mild cough. Please rest.",
        "sdui_components": [],
        "processing_start_ms": 0,
    }

    with patch("app.api.routes.triage.run_triage", new_callable=AsyncMock, return_value=mock_state):
        with patch("app.services.audit.AuditService.log_triage", new_callable=AsyncMock):
            response = await client.post("/v1/triage/chat", json={"session_id": "test_session", "message": "I have a mild cough"})
            assert response.status_code == 200
            data = response.json()
            assert data["response_text"] == "You have a mild cough. Please rest."
            assert data["risk_level"] == "Low"

@pytest.mark.asyncio
async def test_chat_red_flag(client: AsyncClient):
    mock_state = {
        "user_message": "I am coughing blood",
        "session_id": "test_session",
        "red_flags": ["coughing blood"],
        "is_red_flag": True,
        "extracted_entities": {},
        "retrieved_docs": [],
        "web_results": [],
        "reranked_docs": [],
        "triage_decision": {"risk_level": "High", "next_steps": ["Visit emergency room"], "sources": [], "reasons": []},
        "response_text": "URGENT: Your symptoms indicate a potential medical emergency.",
        "sdui_components": [],
        "processing_start_ms": 0,
    }

    with patch("app.api.routes.triage.run_triage", new_callable=AsyncMock, return_value=mock_state):
        with patch("app.services.audit.AuditService.log_triage", new_callable=AsyncMock):
            response = await client.post("/v1/triage/chat", json={"session_id": "test_session", "message": "I am coughing blood"})
            assert response.status_code == 200
            data = response.json()
            assert data["risk_level"] == "High"

@pytest.mark.asyncio
async def test_chat_empty_message(client: AsyncClient):
    response = await client.post("/v1/triage/chat", json={"session_id": "test_session", "message": ""})
    assert response.status_code in [200, 422]

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data

@pytest.mark.asyncio
async def test_auth_token(client: AsyncClient):
    response = await client.post("/v1/auth/token", json={"user_id": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
