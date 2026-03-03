"""
Tests pour l'endpoint de chat simple.
"""
import pytest
from fastapi.testclient import TestClient
from backend.api.api_app import app

client = TestClient(app)


def test_simple_chat_health():
    """Test que le endpoint health fonctionne."""
    response = client.get("/api/simple-chat/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_simple_chat_message():
    """Test qu'un message simple reçoit une réponse."""
    response = client.post(
        "/api/simple-chat/",
        json={"message": "coucou", "session_id": "test-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
