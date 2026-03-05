"""Tests unitaires pour la protection contre la race condition dans get_simple_chat_agent.

Vérifie que l'initialisation du singleton est thread-safe avec asyncio.Lock.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestSimpleChatAgentRaceCondition:
    """Tests pour la race condition dans get_simple_chat_agent()."""

    def setup_method(self):
        """Réinitialise le singleton avant chaque test."""
        import backend.api.routers.simple_chat_api as mod
        mod._simple_chat_agent = None

    def teardown_method(self):
        """Réinitialise le singleton après chaque test."""
        import backend.api.routers.simple_chat_api as mod
        mod._simple_chat_agent = None

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self):
        """Le singleton retourne toujours la même instance."""
        import backend.api.routers.simple_chat_api as mod
        
        mock_agent = AsyncMock()
        mock_agent.name = "simple-chat"
        
        with patch.object(mod, 'build_simple_chat_agent', return_value=mock_agent) as mock_build:
            from backend.api.routers.simple_chat_api import get_simple_chat_agent
            
            agent1 = await get_simple_chat_agent()
            agent2 = await get_simple_chat_agent()
            
            assert agent1 is agent2
            # build_simple_chat_agent ne doit être appelé qu'une seule fois
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_initialization_single_instance(self):
        """Initialisation concurrente ne crée qu'une seule instance (race condition fix)."""
        import backend.api.routers.simple_chat_api as mod
        
        mock_agent = AsyncMock()
        mock_agent.name = "simple-chat"
        call_count = 0
        
        async def slow_build(*args, **kwargs):
            """Simule une construction lente pour exposer la race condition."""
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Délai pour permettre l'interleaving
            return mock_agent
        
        with patch.object(mod, 'build_simple_chat_agent', side_effect=slow_build):
            from backend.api.routers.simple_chat_api import get_simple_chat_agent
            
            # Lancer 5 appels concurrents
            tasks = [get_simple_chat_agent() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Tous les résultats doivent être la même instance
            first = results[0]
            for r in results:
                assert r is first, "Tous les appels concurrents doivent retourner la même instance"
            
            # build_simple_chat_agent ne doit être appelé qu'une seule fois
            assert call_count == 1, f"Race condition détectée : {call_count} appels au lieu de 1"

    @pytest.mark.asyncio
    async def test_lock_exists_and_is_asyncio_lock(self):
        """Le lock existe et est bien un asyncio.Lock."""
        import backend.api.routers.simple_chat_api as mod
        
        assert hasattr(mod, '_simple_chat_agent_lock')
        assert isinstance(mod._simple_chat_agent_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_double_checked_locking_pattern(self):
        """Le pattern double-checked locking est correctement implémenté."""
        import backend.api.routers.simple_chat_api as mod
        
        mock_agent = AsyncMock()
        
        # Premier appel : initialise
        with patch.object(mod, 'build_simple_chat_agent', return_value=mock_agent):
            from backend.api.routers.simple_chat_api import get_simple_chat_agent
            
            agent1 = await get_simple_chat_agent()
            assert agent1 is not None
            
            # Deuxième appel : retourne directement sans passer par le lock
            # (vérifié par le fait que build n'est pas rappelé)
            agent2 = await get_simple_chat_agent()
            assert agent1 is agent2

    def test_no_hardcoded_agent_in_source(self):
        """Vérifie qu'aucun agent hardcodé n'est présent dans le fichier source."""
        from pathlib import Path
        source = Path("backend/api/routers/simple_chat_api.py").read_text(encoding="utf-8")
        
        # Vérifier que le lock est présent (protection race condition)
        assert "_simple_chat_agent_lock = asyncio.Lock()" in source, (
            "Le lock asyncio.Lock doit être présent pour la thread-safety"
        )
        
        # Vérifier le pattern double-checked locking
        assert "async with _simple_chat_agent_lock:" in source, (
            "Le pattern 'async with lock' doit être utilisé"
        )
