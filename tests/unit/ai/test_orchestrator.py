"""
Tests unitaires pour backend/ai/orchestrator.py et backend/api/routers/ws_ai.py.

Couvre :
- Initialisation synchrone de l'Orchestrateur (self.agents = {})
- Initialisation asynchrone via init() (await load_enabled_agents)
- Erreur RuntimeError si agent 'orchestrator' absent
- Gestion WebSocketDisconnect dans ws_ai.py
- Gestion RuntimeError d'initialisation dans ws_ai.py
- Gestion d'erreur inattendue dans ws_ai.py
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import AsyncIterator

from backend.ai.orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_mock_session() -> MagicMock:
    """Retourne un mock de AsyncSession."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


def _make_mock_agents(include_orchestrator: bool = True) -> dict:
    """Retourne un dictionnaire d'agents mockés."""
    agents = {
        "search_agent": MagicMock(),
        "playlist_agent": MagicMock(),
        "smalltalk_agent": MagicMock(),
    }
    if include_orchestrator:
        agents["orchestrator"] = MagicMock()
    return agents


# ---------------------------------------------------------------------------
# Tests : Orchestrator.__init__
# ---------------------------------------------------------------------------

class TestOrchestratorInit:
    """Tests pour l'initialisation synchrone de l'Orchestrateur."""

    def test_init_agents_is_empty_dict(self):
        """
        Vérifie que __init__ initialise self.agents comme un dict vide
        et NON comme une coroutine.
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        assert isinstance(orchestrator.agents, dict), (
            "self.agents doit être un dict vide après __init__, pas une coroutine"
        )
        assert len(orchestrator.agents) == 0, (
            "self.agents doit être vide avant l'appel à init()"
        )

    def test_init_agents_is_not_coroutine(self):
        """
        Vérifie que self.agents n'est pas une coroutine (bug original).
        """
        import inspect
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        assert not inspect.iscoroutine(orchestrator.agents), (
            "self.agents ne doit PAS être une coroutine — "
            "load_enabled_agents() ne doit pas être appelé sans await dans __init__"
        )

    def test_init_session_stored(self):
        """Vérifie que la session est correctement stockée."""
        session = _make_mock_session()
        orchestrator = Orchestrator(session)
        assert orchestrator.session is session

    def test_init_stats_initialized(self):
        """Vérifie que les statistiques sont initialisées correctement."""
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        assert orchestrator._stats["total_requests"] == 0
        assert orchestrator._stats["successful_requests"] == 0
        assert orchestrator._stats["failed_requests"] == 0
        assert orchestrator._stats["avg_response_time"] == 0.0
        assert isinstance(orchestrator._stats["agent_selections"], dict)

    def test_init_runtime_cache_empty(self):
        """Vérifie que le cache runtime est vide à l'initialisation."""
        session = _make_mock_session()
        orchestrator = Orchestrator(session)
        assert orchestrator._runtime_cache == {}


# ---------------------------------------------------------------------------
# Tests : Orchestrator.init() — initialisation asynchrone
# ---------------------------------------------------------------------------

class TestOrchestratorAsyncInit:
    """Tests pour la méthode async init() de l'Orchestrateur."""

    @pytest.mark.asyncio
    async def test_init_loads_agents_successfully(self):
        """
        Vérifie que init() charge les agents via await load_enabled_agents().
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        mock_agents = _make_mock_agents(include_orchestrator=True)

        with patch.object(
            orchestrator.loader,
            "load_enabled_agents",
            new_callable=AsyncMock,
            return_value=mock_agents
        ):
            await orchestrator.init()

        assert orchestrator.agents == mock_agents
        assert "orchestrator" in orchestrator.agents
        assert len(orchestrator.agents) == 4

    @pytest.mark.asyncio
    async def test_init_raises_if_orchestrator_agent_missing(self):
        """
        Vérifie que init() lève RuntimeError si l'agent 'orchestrator' est absent.
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        mock_agents = _make_mock_agents(include_orchestrator=False)

        with patch.object(
            orchestrator.loader,
            "load_enabled_agents",
            new_callable=AsyncMock,
            return_value=mock_agents
        ):
            with pytest.raises(RuntimeError, match="orchestrator"):
                await orchestrator.init()

    @pytest.mark.asyncio
    async def test_init_raises_if_no_agents_at_all(self):
        """
        Vérifie que init() lève RuntimeError si aucun agent n'est chargé.
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        with patch.object(
            orchestrator.loader,
            "load_enabled_agents",
            new_callable=AsyncMock,
            return_value={}
        ):
            with pytest.raises(RuntimeError, match="orchestrator"):
                await orchestrator.init()

    @pytest.mark.asyncio
    async def test_init_awaits_load_enabled_agents(self):
        """
        Vérifie que init() appelle bien await sur load_enabled_agents().
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        mock_agents = _make_mock_agents(include_orchestrator=True)
        mock_load = AsyncMock(return_value=mock_agents)

        with patch.object(orchestrator.loader, "load_enabled_agents", mock_load):
            await orchestrator.init()

        mock_load.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_agents_populated_after_init(self):
        """
        Vérifie que self.agents est bien peuplé après init() et non avant.
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        # Avant init() : agents vide
        assert orchestrator.agents == {}

        mock_agents = _make_mock_agents(include_orchestrator=True)

        with patch.object(
            orchestrator.loader,
            "load_enabled_agents",
            new_callable=AsyncMock,
            return_value=mock_agents
        ):
            await orchestrator.init()

        # Après init() : agents peuplés
        assert orchestrator.agents == mock_agents

    @pytest.mark.asyncio
    async def test_init_can_be_called_multiple_times(self):
        """
        Vérifie que init() peut être appelé plusieurs fois (rechargement).
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        mock_agents_v1 = _make_mock_agents(include_orchestrator=True)
        mock_agents_v2 = {**_make_mock_agents(include_orchestrator=True), "new_agent": MagicMock()}

        with patch.object(
            orchestrator.loader,
            "load_enabled_agents",
            new_callable=AsyncMock,
            side_effect=[mock_agents_v1, mock_agents_v2]
        ):
            await orchestrator.init()
            assert len(orchestrator.agents) == 4

            await orchestrator.init()
            assert len(orchestrator.agents) == 5


# ---------------------------------------------------------------------------
# Tests : WebSocket endpoint ws_ai.py
# ---------------------------------------------------------------------------

class TestWsAiEndpoint:
    """Tests pour l'endpoint WebSocket /ws/chat."""

    @pytest.mark.asyncio
    async def test_websocket_accepts_connection(self):
        """
        Vérifie que le WebSocket accepte la connexion.
        """
        from backend.api.routers.ws_ai import chat

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=Exception("stop_loop"))

        mock_agents = _make_mock_agents(include_orchestrator=True)

        with patch("backend.api.routers.ws_ai.AsyncSessionLocal") as mock_session_ctx, \
             patch("backend.api.routers.ws_ai.Orchestrator") as mock_orch_cls:

            mock_db = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_orch = AsyncMock()
            mock_orch.init = AsyncMock()
            mock_orch.handle_stream = AsyncMock(return_value=iter([]))
            mock_orch_cls.return_value = mock_orch

            try:
                await chat(mock_ws)
            except Exception:
                pass

        mock_ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_websocket_calls_orchestrator_init(self):
        """
        Vérifie que le WebSocket appelle bien await orchestrator.init().
        """
        from backend.api.routers.ws_ai import chat
        from fastapi.websockets import WebSocketDisconnect

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        with patch("backend.api.routers.ws_ai.AsyncSessionLocal") as mock_session_ctx, \
             patch("backend.api.routers.ws_ai.Orchestrator") as mock_orch_cls:

            mock_db = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_orch = AsyncMock()
            mock_orch.init = AsyncMock()
            mock_orch_cls.return_value = mock_orch

            await chat(mock_ws)

        mock_orch.init.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_websocket_handles_disconnect_gracefully(self):
        """
        Vérifie que WebSocketDisconnect est géré proprement sans exception.
        """
        from backend.api.routers.ws_ai import chat
        from fastapi.websockets import WebSocketDisconnect

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        with patch("backend.api.routers.ws_ai.AsyncSessionLocal") as mock_session_ctx, \
             patch("backend.api.routers.ws_ai.Orchestrator") as mock_orch_cls:

            mock_db = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_orch = AsyncMock()
            mock_orch.init = AsyncMock()
            mock_orch_cls.return_value = mock_orch

            # Ne doit pas lever d'exception
            await chat(mock_ws)

        # Le WebSocket ne doit pas être fermé avec un code d'erreur
        mock_ws.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_websocket_sends_chunks_from_handle_stream(self):
        """
        Vérifie que les chunks de handle_stream sont envoyés via send_json.
        """
        from backend.api.routers.ws_ai import chat
        from fastapi.websockets import WebSocketDisconnect

        mock_ws = AsyncMock()
        # Premier appel retourne un message, deuxième déconnecte
        mock_ws.receive_text = AsyncMock(
            side_effect=["Bonjour", WebSocketDisconnect()]
        )

        chunks = [
            {"type": "text", "content": "Bonjour", "state": "streaming"},
            {"type": "final", "content": "Réponse complète", "state": "done"},
        ]

        async def mock_stream(msg):
            for chunk in chunks:
                yield chunk

        with patch("backend.api.routers.ws_ai.AsyncSessionLocal") as mock_session_ctx, \
             patch("backend.api.routers.ws_ai.Orchestrator") as mock_orch_cls:

            mock_db = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_orch = AsyncMock()
            mock_orch.init = AsyncMock()
            mock_orch.handle_stream = mock_stream
            mock_orch_cls.return_value = mock_orch

            await chat(mock_ws)

        # Vérifie que send_json a été appelé pour chaque chunk
        assert mock_ws.send_json.await_count == 2
        calls = mock_ws.send_json.await_args_list
        assert calls[0][0][0] == chunks[0]
        assert calls[1][0][0] == chunks[1]

    @pytest.mark.asyncio
    async def test_websocket_handles_runtime_error_on_init(self):
        """
        Vérifie que RuntimeError lors de init() envoie un message d'erreur
        et ferme le WebSocket avec code 1011.
        """
        from backend.api.routers.ws_ai import chat

        mock_ws = AsyncMock()

        with patch("backend.api.routers.ws_ai.AsyncSessionLocal") as mock_session_ctx, \
             patch("backend.api.routers.ws_ai.Orchestrator") as mock_orch_cls:

            mock_db = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_orch = AsyncMock()
            mock_orch.init = AsyncMock(
                side_effect=RuntimeError("Agent 'orchestrator' manquant")
            )
            mock_orch_cls.return_value = mock_orch

            await chat(mock_ws)

        # Doit envoyer un message d'erreur
        mock_ws.send_json.assert_awaited_once()
        error_payload = mock_ws.send_json.await_args[0][0]
        assert error_payload["type"] == "error"
        assert "erreur" in error_payload["content"].lower() or "initialisation" in error_payload["content"].lower()

        # Doit fermer avec code 1011
        mock_ws.close.assert_awaited_once_with(code=1011)

    @pytest.mark.asyncio
    async def test_websocket_handles_unexpected_exception(self):
        """
        Vérifie que les exceptions inattendues sont gérées proprement.
        """
        from backend.api.routers.ws_ai import chat

        mock_ws = AsyncMock()

        with patch("backend.api.routers.ws_ai.AsyncSessionLocal") as mock_session_ctx, \
             patch("backend.api.routers.ws_ai.Orchestrator") as mock_orch_cls:

            mock_db = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Erreur inattendue de connexion DB")
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_orch_cls.return_value = AsyncMock()

            # Ne doit pas propager l'exception
            await chat(mock_ws)

        # Doit tenter d'envoyer un message d'erreur
        mock_ws.send_json.assert_awaited_once()
        error_payload = mock_ws.send_json.await_args[0][0]
        assert error_payload["type"] == "error"


# ---------------------------------------------------------------------------
# Tests : Régression — TypeError original
# ---------------------------------------------------------------------------

class TestOrchestratorRegressionTypeError:
    """
    Tests de régression pour le bug original :
    TypeError: argument of type 'coroutine' is not iterable
    """

    def test_no_type_error_on_instantiation(self):
        """
        Vérifie qu'aucun TypeError n'est levé lors de l'instanciation.
        C'est le bug original : 'coroutine' is not iterable.
        """
        session = _make_mock_session()

        try:
            orchestrator = Orchestrator(session)
        except TypeError as e:
            pytest.fail(
                f"TypeError levé lors de l'instanciation de Orchestrator : {e}\n"
                "Cause probable : load_enabled_agents() appelé sans await dans __init__"
            )

    def test_agents_supports_in_operator_after_init(self):
        """
        Vérifie que l'opérateur 'in' fonctionne sur self.agents après init().
        C'est exactement l'opération qui échouait avec le bug original.
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        # Avant init() : dict vide, 'in' doit fonctionner sans TypeError
        try:
            result = "orchestrator" in orchestrator.agents
            assert result is False
        except TypeError as e:
            pytest.fail(
                f"TypeError lors de 'in' sur self.agents avant init() : {e}\n"
                "self.agents est probablement une coroutine non-awaitée"
            )

    @pytest.mark.asyncio
    async def test_agents_supports_in_operator_after_async_init(self):
        """
        Vérifie que l'opérateur 'in' fonctionne après await init().
        """
        session = _make_mock_session()
        orchestrator = Orchestrator(session)

        mock_agents = _make_mock_agents(include_orchestrator=True)

        with patch.object(
            orchestrator.loader,
            "load_enabled_agents",
            new_callable=AsyncMock,
            return_value=mock_agents
        ):
            await orchestrator.init()

        # Après init() : doit fonctionner sans TypeError
        try:
            assert "orchestrator" in orchestrator.agents
            assert "search_agent" in orchestrator.agents
            assert "unknown_agent" not in orchestrator.agents
        except TypeError as e:
            pytest.fail(f"TypeError lors de 'in' sur self.agents après init() : {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
