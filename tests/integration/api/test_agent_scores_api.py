"""Tests pour les endpoints de scores d'agents."""
import pytest
from fastapi.testclient import TestClient
from backend.api.api_app import create_api


@pytest.fixture(scope="module")
def client():
    """Client de test pour l'API."""
    app = create_api()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    """Configurer les données de test."""
    # Les données seront créées via les endpoints
    pass


def test_create_agent_score(client: TestClient):
    """Tester la création d'un score d'agent."""
    payload = {
        "agent_name": "test_agent",
        "intent": "test_intent",
        "score": 8.5,
        "usage_count": 0,
        "success_count": 0,
    }
    
    response = client.post("/api/agents/scores", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["agent_name"] == "test_agent"
    assert data["intent"] == "test_intent"
    assert data["score"] == 8.5
    assert "id" in data


def test_get_agent_score(client: TestClient):
    """Tester la récupération d'un score d'agent."""
    # Créer d'abord un score
    payload = {
        "agent_name": "test_agent_get",
        "intent": "test_intent_get",
        "score": 7.0,
    }
    client.post("/api/agents/scores", json=payload)
    
    # Récupérer le score
    response = client.get("/api/agents/scores/test_agent_get/test_intent_get")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_name"] == "test_agent_get"
    assert data["intent"] == "test_intent_get"


def test_list_agent_scores(client: TestClient):
    """Tester la liste des scores d'agents."""
    # Créer quelques scores
    for i in range(3):
        payload = {
            "agent_name": f"agent_{i}",
            "intent": "common_intent",
            "score": float(i + 5),
        }
        client.post("/api/agents/scores", json=payload)
    
    # Lister les scores
    response = client.get("/api/agents/scores")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "results" in data
    assert len(data["results"]) >= 3


def test_update_agent_score(client: TestClient):
    """Tester la mise à jour d'un score d'agent."""
    # Créer un score
    payload = {
        "agent_name": "test_agent_update",
        "intent": "test_intent_update",
        "score": 5.0,
    }
    client.post("/api/agents/scores", json=payload)
    
    # Mettre à jour le score
    update_payload = {
        "score": 9.0,
        "usage_count": 10,
        "success_count": 8,
    }
    response = client.put(
        "/api/agents/scores/test_agent_update/test_intent_update",
        json=update_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 9.0
    assert data["usage_count"] == 10
    assert data["success_count"] == 8


def test_increment_agent_score_usage(client: TestClient):
    """Tester l'incrémentation de l'utilisation d'un score."""
    # Créer un score
    payload = {
        "agent_name": "test_agent_increment",
        "intent": "test_intent_increment",
        "score": 7.0,
        "usage_count": 5,
        "success_count": 3,
    }
    client.post("/api/agents/scores", json=payload)
    
    # Incrémenter avec succès
    response = client.patch(
        "/api/agents/scores/test_agent_increment/test_intent_increment/usage?success=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["usage_count"] == 6
    assert data["success_count"] == 4
    
    # Incrémenter sans succès
    response = client.patch(
        "/api/agents/scores/test_agent_increment/test_intent_increment/usage?success=false"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["usage_count"] == 7
    assert data["success_count"] == 4  # Ne devrait pas augmenter


def test_delete_agent_score(client: TestClient):
    """Tester la suppression d'un score d'agent."""
    # Créer un score
    payload = {
        "agent_name": "test_agent_delete",
        "intent": "test_intent_delete",
        "score": 6.0,
    }
    client.post("/api/agents/scores", json=payload)
    
    # Supprimer le score
    response = client.delete("/api/agents/scores/test_agent_delete/test_intent_delete")
    assert response.status_code == 200
    
    # Vérifier qu'il n'existe plus
    response = client.get("/api/agents/scores/test_agent_delete/test_intent_delete")
    assert response.status_code == 404


def test_get_agent_scores_with_metrics(client: TestClient):
    """Tester la récupération des scores avec métriques."""
    # Créer des scores avec différents taux de succès
    test_data = [
        {"agent_name": "metric_agent_1", "intent": "test", "score": 8.0, "usage_count": 10, "success_count": 8},
        {"agent_name": "metric_agent_2", "intent": "test", "score": 6.0, "usage_count": 5, "success_count": 2},
        {"agent_name": "metric_agent_3", "intent": "test", "score": 9.0, "usage_count": 20, "success_count": 18},
    ]
    
    for payload in test_data:
        client.post("/api/agents/scores", json=payload)
    
    # Récupérer les scores avec métriques
    response = client.get("/api/agents/scores/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "results" in data
    
    # Vérifier que les métriques sont calculées
    for result in data["results"]:
        if result["agent_name"] == "metric_agent_1":
            assert result["success_rate"] == 0.8
        elif result["agent_name"] == "metric_agent_2":
            assert result["success_rate"] == 0.4
        elif result["agent_name"] == "metric_agent_3":
            assert result["success_rate"] == 0.9


def test_filter_agent_scores(client: TestClient):
    """Tester le filtrage des scores par agent_name et intent."""
    # Créer des scores avec différents filtres
    test_data = [
        {"agent_name": "filter_agent", "intent": "intent_a", "score": 7.0},
        {"agent_name": "filter_agent", "intent": "intent_b", "score": 8.0},
        {"agent_name": "other_agent", "intent": "intent_a", "score": 6.0},
    ]
    
    for payload in test_data:
        client.post("/api/agents/scores", json=payload)
    
    # Filtrer par agent_name
    response = client.get("/api/agents/scores?agent_name=filter_agent")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert all(s["agent_name"] == "filter_agent" for s in data["results"])
    
    # Filtrer par intent
    response = client.get("/api/agents/scores?intent=intent_a")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert all(s["intent"] == "intent_a" for s in data["results"])


def test_pagination_agent_scores(client: TestClient):
    """Tester la pagination des scores."""
    # Créer plusieurs scores
    for i in range(15):
        payload = {
            "agent_name": f"pagination_agent_{i}",
            "intent": "pagination_intent",
            "score": float(i + 1),
        }
        client.post("/api/agents/scores", json=payload)
    
    # Récupérer avec pagination
    response = client.get("/api/agents/scores?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 5
    assert data["count"] >= 15
    
    # Page suivante
    response = client.get("/api/agents/scores?limit=5&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 5
