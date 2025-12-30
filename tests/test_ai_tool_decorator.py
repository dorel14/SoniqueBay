import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.utils.decorators import ai_tool, _validate_session_parameter, _validate_function_parameters, _track_tool_usage
from backend.ai.utils.registry import ToolRegistry


class TestAIToolDecorator:
    """Tests pour le décorateur @ai_tool."""

    def test_ai_tool_decorator_basic(self):
        """Test du décorateur avec paramètres basiques."""
        
        @ai_tool(
            name="test_tool",
            description="Test tool description",
            category="test"
        )
        def test_function():
            return "test_result"
        
        # Vérification des métadonnées
        assert hasattr(test_function, '_ai_tool_metadata')
        metadata = test_function._ai_tool_metadata
        assert metadata['name'] == "test_tool"
        assert metadata['description'] == "Test tool description"
        assert metadata['category'] == "test"
        assert metadata['validate_params'] == True
        assert metadata['track_usage'] == True
        assert metadata['is_async'] == False

    def test_ai_tool_decorator_async(self):
        """Test du décorateur avec fonction async."""
        
        @ai_tool(
            name="async_test_tool",
            description="Async test tool",
            category="test"
        )
        async def async_test_function():
            return "async_result"
        
        # Vérification des métadonnées
        assert hasattr(async_test_function, '_ai_tool_metadata')
        metadata = async_test_function._ai_tool_metadata
        assert metadata['is_async'] == True

    def test_ai_tool_decorator_with_session(self):
        """Test du décorateur avec validation de session."""
        
        @ai_tool(
            name="session_tool",
            description="Tool requiring session",
            requires_session=True
        )
        def session_function(session: AsyncSession):
            return "session_result"
        
        metadata = session_function._ai_tool_metadata
        assert metadata['requires_session'] == True

    def test_ai_tool_decorator_validation_errors(self):
        """Test des validations du décorateur."""
        
        # Nom invalide
        with pytest.raises(ValueError, match="Le nom du tool doit être une chaîne non vide"):
            @ai_tool(name="", description="test")
            def invalid_name():
                pass
        
        # Description invalide
        with pytest.raises(ValueError, match="La description doit être une chaîne non vide"):
            @ai_tool(name="test", description="")
            def invalid_description():
                pass
        
        # Timeout invalide
        with pytest.raises(ValueError, match="Le timeout doit être un entier positif"):
            @ai_tool(name="test", description="test", timeout=-1)
            def invalid_timeout():
                pass
        
        # Agents autorisés invalides
        with pytest.raises(ValueError, match="Les noms d'agents doivent être des chaînes non vides"):
            @ai_tool(name="test", description="test", allowed_agents=[""])
            def invalid_agents():
                pass

    @pytest.mark.asyncio
    async def test_ai_tool_execution_sync(self):
        """Test de l'exécution d'un tool synchrone."""
        
        @ai_tool(
            name="sync_execution_test",
            description="Sync execution test",
            category="test"
        )
        def sync_function(x: int, y: str = "default"):
            return f"result: {x}, {y}"
        
        # Test d'exécution normale
        result = sync_function(42, y="test")
        assert result == "result: 42, test"
        
        # Vérification dans le registry
        tool_metadata = ToolRegistry.get("sync_execution_test")
        assert tool_metadata is not None
        assert tool_metadata.call_count == 1
        assert tool_metadata.success_count == 1

    @pytest.mark.asyncio
    async def test_ai_tool_execution_async(self):
        """Test de l'exécution d'un tool asynchrone."""
        
        @ai_tool(
            name="async_execution_test",
            description="Async execution test",
            category="test"
        )
        async def async_function(x: int, y: str = "default"):
            await asyncio.sleep(0.01)  # Simuler un traitement async
            return f"async_result: {x}, {y}"
        
        # Test d'exécution normale
        result = await async_function(42, y="test")
        assert result == "async_result: 42, test"
        
        # Vérification dans le registry
        tool_metadata = ToolRegistry.get("async_execution_test")
        assert tool_metadata is not None
        assert tool_metadata.call_count == 1
        assert tool_metadata.success_count == 1

    @pytest.mark.asyncio
    async def test_ai_tool_session_validation(self):
        """Test de la validation de session."""
        
        @ai_tool(
            name="session_validation_test",
            description="Session validation test",
            requires_session=True
        )
        def function_with_session(session: AsyncSession, data: str):
            return f"processed: {data}"
        
        # Mock de session
        mock_session = Mock(spec=AsyncSession)
        
        # Test avec session fournie
        result = function_with_session(mock_session, "test_data")
        assert result == "processed: test_data"
        
        # Test sans session (doit lever une exception)
        with pytest.raises(ValueError, match="nécessite une session de base de données"):
            function_with_session(data="test_data")

    @pytest.mark.asyncio
    async def test_ai_tool_timeout(self):
        """Test du timeout sur les tools."""
        
        @ai_tool(
            name="timeout_test",
            description="Timeout test",
            timeout=1
        )
        async def slow_function():
            await asyncio.sleep(2)  # Plus long que le timeout
            return "should_not_reach"
        
        # Test timeout
        with pytest.raises(asyncio.TimeoutError):
            await slow_function()

    @pytest.mark.asyncio
    async def test_ai_tool_error_handling(self):
        """Test de la gestion des erreurs."""
        
        @ai_tool(
            name="error_test",
            description="Error handling test"
        )
        def error_function():
            raise ValueError("Test error")
        
        # Test gestion d'erreur
        with pytest.raises(ValueError, match="Test error"):
            error_function()
        
        # Vérification des statistiques d'erreur
        tool_metadata = ToolRegistry.get("error_test")
        assert tool_metadata.error_count == 1
        assert tool_metadata.call_count == 1
        assert tool_metadata.success_count == 0


class TestValidationHelpers:
    """Tests pour les fonctions d'aide à la validation."""

    def test_validate_session_parameter(self):
        """Test de la validation des paramètres de session."""
        
        def func_with_session(session: AsyncSession, data: str):
            pass
        
        def func_without_session(data: str):
            pass
        
        mock_session = Mock(spec=AsyncSession)
        
        # Cas valide avec session en positionnel
        _validate_session_parameter(func_with_session, (mock_session, "test"), {})
        
        # Cas valide avec session en nommé
        _validate_session_parameter(func_with_session, (), {"session": mock_session, "data": "test"})
        
        # Cas invalide - pas de session
        with pytest.raises(ValueError, match="nécessite une session"):
            _validate_session_parameter(func_with_session, ("test",), {})
        
        # Cas valide - fonction sans session requise
        _validate_session_parameter(func_without_session, ("test",), {})

    def test_validate_function_parameters(self):
        """Test de la validation des paramètres de fonction."""
        
        def func_typed(x: int, y: str = "default"):
            pass
        
        def func_untyped(x, y=None):
            pass
        
        # Cas valide avec types correspondants
        _validate_function_parameters(func_typed, (42, "test"), {})
        
        # Cas avec type incorrect (doit logger un warning mais ne pas lever d'exception)
        with patch('backend.ai.utils.decorators.logger') as mock_logger:
            _validate_function_parameters(func_typed, ("not_int", "test"), {})
            mock_logger.warning.assert_called_once()

    def test_track_tool_usage(self):
        """Test du tracking de l'utilisation des tools."""
        
        with patch('backend.ai.utils.decorators.logger') as mock_logger:
            # Test succès
            _track_tool_usage("test_tool", "test_agent", 0.0, success=True)
            
            # Vérification du logging
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert "Tool exécuté: test_tool" in call_args[0][0]
            assert call_args[1]['extra']['success'] == True
            
            # Test échec avec erreur
            _track_tool_usage("test_tool", "test_agent", 0.0, success=False, error="Test error")
            
            # Vérification du logging d'erreur
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert call_args[1]['extra']['success'] == False
            assert call_args[1]['extra']['error'] == "Test error"


class TestRegistryIntegration:
    """Tests d'intégration avec le registry."""

    def test_tool_registration(self):
        """Test de l'enregistrement des tools dans le registry."""
        
        @ai_tool(
            name="registry_test",
            description="Registry integration test",
            category="test",
            tags=["integration", "test"]
        )
        def registry_function():
            return "registry_result"
        
        # Vérification de l'enregistrement
        tool_metadata = ToolRegistry.get("registry_test")
        assert tool_metadata is not None
        assert tool_metadata.description == "Registry integration test"
        assert tool_metadata.category == "test"
        assert "integration" in tool_metadata.tags
        assert "test" in tool_metadata.tags

    def test_tool_access_control(self):
        """Test du contrôle d'accès aux tools."""
        
        @ai_tool(
            name="access_control_test",
            description="Access control test",
            allowed_agents=["allowed_agent"]
        )
        def access_function():
            return "access_result"
        
        # Test accès autorisé
        assert ToolRegistry.validate_access("access_control_test", "allowed_agent") == True
        
        # Test accès refusé
        assert ToolRegistry.validate_access("access_control_test", "forbidden_agent") == False
        
        # Test accès libre (pas de restriction)
        @ai_tool(
            name="free_access_test",
            description="Free access test"
        )
        def free_function():
            return "free_result"
        
        assert ToolRegistry.validate_access("free_access_test", "any_agent") == True

    def test_tool_statistics(self):
        """Test des statistiques de tools."""
        
        @ai_tool(
            name="stats_test",
            description="Statistics test"
        )
        def stats_function(success: bool = True):
            if not success:
                raise ValueError("Test error")
            return "stats_result"
        
        # Exécutions mixtes succès/échec
        stats_function(success=True)
        stats_function(success=True)
        try:
            stats_function(success=False)
        except ValueError:
            pass
        
        # Vérification des statistiques
        tool_metadata = ToolRegistry.get("stats_test")
        assert tool_metadata.call_count == 3
        assert tool_metadata.success_count == 2
        assert tool_metadata.error_count == 1
        assert tool_metadata.success_rate == 2/3

    def test_tool_health_report(self):
        """Test du rapport de santé des tools."""
        
        # Enregistrer quelques tools
        @ai_tool(name="healthy_tool", description="Healthy tool")
        def healthy_function():
            return "healthy"
        
        @ai_tool(name="error_tool", description="Error tool")
        def error_function():
            raise ValueError("Error")
        
        # Exécuter plusieurs fois pour générer des statistiques
        for _ in range(5):
            healthy_function()
        
        for _ in range(15):  # Plus de 10 appels pour déclencher l'alerte
            try:
                error_function()
            except ValueError:
                pass
        
        # Générer le rapport de santé
        health_report = ToolRegistry.get_health_report()
        
        assert "global_stats" in health_report
        assert "issues" in health_report
        assert "recommendations" in health_report
        
        # Vérifier qu'une issue est détectée pour le tool avec erreur
        issues = health_report["issues"]
        error_issues = [issue for issue in issues if issue["type"] == "high_error_rate"]
        assert len(error_issues) > 0
        assert error_issues[0]["tool"] == "error_tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])