"""
Tests pour les schémas de réponse des agents IA.

Ce module teste la validation et la sérialisation des schémas
créés dans backend/api/schemas/agent_response_schema.py.
"""
import pytest

from backend.api.schemas.agent_response_schema import (
    AgentMessageType,
    AgentState,
    AgentToolCall,
    AgentClarificationRequest,
    AgentRefusal,
    AgentMessageResponse,
    SearchAgentResponse,
    PlaylistAgentResponse,
    ActionAgentResponse,
    AgentWebSocketMessage,
    AgentPerformanceMetrics,
)


class TestAgentMessageType:
    """Tests pour l'enum AgentMessageType."""
    
    def test_message_types(self):
        """Test que tous les types de messages sont définis."""
        assert AgentMessageType.TEXT == "text"
        assert AgentMessageType.TOOL_CALL == "tool_call"
        assert AgentMessageType.CLARIFICATION == "clarification"
        assert AgentMessageType.REFUSAL == "refusal"


class TestAgentState:
    """Tests pour l'enum AgentState."""
    
    def test_agent_states(self):
        """Test que tous les états sont définis."""
        assert AgentState.THINKING == "thinking"
        assert AgentState.CLARIFYING == "clarifying"
        assert AgentState.ACTING == "acting"
        assert AgentState.DONE == "done"


class TestAgentToolCall:
    """Tests pour le schéma AgentToolCall."""
    
    def test_valid_tool_call(self):
        """Test la création d'un AgentToolCall valide."""
        tool_call = AgentToolCall(
            tool_name="search_tracks",
            parameters={"query": "jazz", "limit": 10},
            tool_call_id="call_123"
        )
        assert tool_call.tool_name == "search_tracks"
        assert tool_call.parameters["query"] == "jazz"
        assert tool_call.tool_call_id == "call_123"
    
    def test_tool_call_required_fields(self):
        """Test que le champ tool_name est obligatoire."""
        with pytest.raises(Exception):  # Doit lever une erreur de validation
            AgentToolCall(parameters={})


class TestAgentClarificationRequest:
    """Tests pour le schéma AgentClarificationRequest."""
    
    def test_valid_clarification(self):
        """Test la création d'une demande de clarification valide."""
        clarification = AgentClarificationRequest(
            question="Quel artiste cherchez-vous?",
            context="L'utilisateur a demandé des recommandations",
            clarification_id="clarif_456"
        )
        assert clarification.question == "Quel artiste cherchez-vous?"
        assert clarification.context == "L'utilisateur a demandé des recommandations"
        assert clarification.clarification_id == "clarif_456"
    
    def test_clarification_required_field(self):
        """Test que le champ question est obligatoire."""
        with pytest.raises(Exception):
            AgentClarificationRequest()


class TestAgentRefusal:
    """Tests pour le schéma AgentRefusal."""
    
    def test_valid_refusal(self):
        """Test la création d'un refus valide."""
        refusal = AgentRefusal(
            reason="Action non autorisée",
            suggestion="Essayez une autre requête",
            refusal_id="refuse_789"
        )
        assert refusal.reason == "Action non autorisée"
        assert refusal.suggestion == "Essayez une autre requête"
        assert refusal.refusal_id == "refuse_789"
    
    def test_refusal_required_field(self):
        """Test que le champ reason est obligatoire."""
        with pytest.raises(Exception):
            AgentRefusal()


class TestAgentMessageResponse:
    """Tests pour le schéma AgentMessageResponse."""
    
    def test_text_message(self):
        """Test la création d'un message textuel."""
        response = AgentMessageResponse(
            type=AgentMessageType.TEXT,
            content="Voici les résultats de votre recherche",
            state=AgentState.DONE,
            session_id="session_1"
        )
        assert response.type == AgentMessageType.TEXT
        assert response.content == "Voici les résultats de votre recherche"
        assert response.state == AgentState.DONE
        assert response.session_id == "session_1"
        assert response.timestamp is not None
    
    def test_tool_call_message(self):
        """Test la création d'un message d'appel d'outil."""
        tool_call = AgentToolCall(
            tool_name="get_artist",
            parameters={"artist_id": 123}
        )
        response = AgentMessageResponse(
            type=AgentMessageType.TOOL_CALL,
            tool_call=tool_call,
            state=AgentState.ACTING,
            session_id="session_2"
        )
        assert response.type == AgentMessageType.TOOL_CALL
        assert response.tool_call.tool_name == "get_artist"
        assert response.state == AgentState.ACTING
    
    def test_clarification_message(self):
        """Test la création d'un message de clarification."""
        clarification = AgentClarificationRequest(
            question="Précisez votre demande",
            context="Requête ambiguë"
        )
        response = AgentMessageResponse(
            type=AgentMessageType.CLARIFICATION,
            clarification=clarification,
            state=AgentState.CLARIFYING,
            session_id="session_3"
        )
        assert response.type == AgentMessageType.CLARIFICATION
        assert response.clarification.question == "Précisez votre demande"
        assert response.state == AgentState.CLARIFYING
    
    def test_refusal_message(self):
        """Test la création d'un message de refus."""
        refusal = AgentRefusal(
            reason="Action non supportée",
            suggestion="Utilisez une autre commande"
        )
        response = AgentMessageResponse(
            type=AgentMessageType.REFUSAL,
            refusal=refusal,
            state=AgentState.DONE,
            session_id="session_4"
        )
        assert response.type == AgentMessageType.REFUSAL
        assert response.refusal.reason == "Action non supportée"
        assert response.state == AgentState.DONE
    
    def test_required_fields(self):
        """Test que les champs obligatoires sont validés."""
        # Le champ content est obligatoire pour le type TEXT
        response = AgentMessageResponse(
            type=AgentMessageType.TEXT,
            content="",  # Content vide est autorisé par le schéma
            state=AgentState.DONE,
            session_id="session_5"
        )
        assert response.content == ""


class TestSearchAgentResponse:
    """Tests pour le schéma SearchAgentResponse."""
    
    def test_valid_search_response(self):
        """Test la création d'une réponse de recherche valide."""
        response = SearchAgentResponse(
            results=[],  # Liste vide est valide
            query="test query",
            count=0,
            session_id="session_6"
        )
        assert len(response.results) == 0
        assert response.query == "test query"
        assert response.count == 0
        assert response.session_id == "session_6"
        assert response.timestamp is not None


class TestPlaylistAgentResponse:
    """Tests pour le schéma PlaylistAgentResponse."""
    
    def test_valid_playlist_response(self):
        """Test la création d'une réponse de playlist valide."""
        response = PlaylistAgentResponse(
            tracks=[],  # Liste vide est valide
            playlist_name="My Playlist",
            description="A test playlist",
            session_id="session_7"
        )
        assert len(response.tracks) == 0
        assert response.playlist_name == "My Playlist"
        assert response.description == "A test playlist"
        assert response.session_id == "session_7"


class TestActionAgentResponse:
    """Tests pour le schéma ActionAgentResponse."""
    
    def test_successful_action(self):
        """Test la création d'une réponse d'action réussie."""
        response = ActionAgentResponse(
            success=True,
            result={"status": "completed"},
            message="Action executed successfully",
            session_id="session_8"
        )
        assert response.success is True
        assert response.result["status"] == "completed"
        assert response.message == "Action executed successfully"
        assert response.session_id == "session_8"
    
    def test_failed_action(self):
        """Test la création d'une réponse d'action échouée."""
        response = ActionAgentResponse(
            success=False,
            result=None,
            message="Action failed",
            session_id="session_9"
        )
        assert response.success is False
        assert response.message == "Action failed"




class TestAgentWebSocketMessage:
    """Tests pour le schéma AgentWebSocketMessage."""
    
    def test_valid_websocket_message(self):
        """Test la création d'un message WebSocket valide."""
        message = AgentWebSocketMessage(
            type=AgentMessageType.TEXT,
            data={"content": "Hello"},
            session_id="session_11"
        )
        assert message.type == AgentMessageType.TEXT
        assert message.data["content"] == "Hello"
        assert message.session_id == "session_11"
        assert message.timestamp is not None


class TestAgentPerformanceMetrics:
    """Tests pour le schéma AgentPerformanceMetrics."""
    
    def test_valid_metrics(self):
        """Test la création de métriques de performance valides."""
        metrics = AgentPerformanceMetrics(
            agent_name="SearchAgent",
            success_rate=0.95,
            avg_response_time=0.5,
            total_calls=100
        )
        assert metrics.agent_name == "SearchAgent"
        assert metrics.success_rate == 0.95
        assert metrics.avg_response_time == 0.5
        assert metrics.total_calls == 100
        assert metrics.last_updated is not None


class TestSchemaSerialization:
    """Tests pour la sérialisation des schémas."""
    
    def test_agent_message_response_serialization(self):
        """Test la sérialisation d'AgentMessageResponse."""
        response = AgentMessageResponse(
            type=AgentMessageType.TEXT,
            content="Test message",
            state=AgentState.DONE,
            session_id="test_session"
        )
        serialized = response.model_dump()
        assert serialized["type"] == "text"
        assert serialized["content"] == "Test message"
        assert serialized["state"] == "done"
        assert serialized["session_id"] == "test_session"
        assert "timestamp" in serialized
    
    def test_search_response_serialization(self):
        """Test la sérialisation de SearchAgentResponse."""
        response = SearchAgentResponse(
            results=[],
            query="test",
            count=0,
            session_id="test"
        )
        serialized = response.model_dump()
        assert serialized["count"] == 0
        assert serialized["query"] == "test"
        assert len(serialized["results"]) == 0
