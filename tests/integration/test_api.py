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
async def test_chat_with_images(client: AsyncClient):
    mock_analysis = "The image shows a chest X-ray with possible abnormalities."
    mock_state = {
        "user_message": "[System Note: User attached images. Image Analysis: The image shows a chest X-ray with possible abnormalities.]\n\nUser message: What do you see?",
        "session_id": "test_session",
        "red_flags": [],
        "is_red_flag": False,
        "extracted_entities": {},
        "retrieved_docs": [],
        "web_results": [],
        "reranked_docs": [],
        "triage_decision": {"risk_level": "Moderate", "next_steps": ["Consult a doctor"], "sources": [], "reasons": []},
        "response_text": "I see possible abnormalities in the chest X-ray. Please consult a doctor.",
        "sdui_components": [],
        "processing_start_ms": 0,
    }

    with patch("app.api.routes.triage.GeminiService.analyze_images", new_callable=AsyncMock, return_value=mock_analysis):
        with patch("app.api.routes.triage.run_triage", new_callable=AsyncMock, return_value=mock_state) as mock_triage:
            with patch("app.services.audit.AuditService.log_triage", new_callable=AsyncMock):
                response = await client.post(
                    "/v1/triage/chat",
                    json={
                        "session_id": "test_session",
                        "message": "What do you see?",
                        "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="],
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["response_text"] == "I see possible abnormalities in the chest X-ray. Please consult a doctor."
                assert data["risk_level"] == "Moderate"

                call_args = mock_triage.call_args
                assert "System Note: User attached images" in call_args[0][0]


@pytest.mark.asyncio
async def test_chat_with_images_gemini_failure(client: AsyncClient):
    mock_state = {
        "user_message": "What do you see?",
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

    with patch("app.api.routes.triage.GeminiService.analyze_images", new_callable=AsyncMock, side_effect=Exception("Gemini unavailable")):
        with patch("app.api.routes.triage.run_triage", new_callable=AsyncMock, return_value=mock_state) as mock_triage:
            with patch("app.services.audit.AuditService.log_triage", new_callable=AsyncMock):
                response = await client.post(
                    "/v1/triage/chat",
                    json={
                        "session_id": "test_session",
                        "message": "What do you see?",
                        "images": ["invalid_base64"],
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["risk_level"] == "Low"

                call_args = mock_triage.call_args
                assert call_args[0][0] == "What do you see?"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data

