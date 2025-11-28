#!/usr/bin/env python3
"""
Tests d'intégration pour la fonctionnalité SSE (Server-Sent Events)
pour la progression du scan.
"""

import pytest


class TestSSEIntegration:
    """Tests d'intégration pour les SSE."""

    def test_sse_handler_registration(self):
        """Test de l'enregistrement des handlers SSE."""
        # Importer ici pour éviter les problèmes d'import au niveau module
        from frontend.websocket_manager.ws_client import register_sse_handler, sse_handlers

        # Nettoyer les handlers existants
        sse_handlers.clear()

        def test_handler(data):
            pass

        register_sse_handler(test_handler)

        assert len(sse_handlers) == 1
        assert test_handler in sse_handlers

    def test_sse_handler_execution(self):
        """Test de l'exécution des handlers SSE."""
        from frontend.websocket_manager.ws_client import register_sse_handler, sse_handlers

        sse_handlers.clear()

        received_data = []

        def test_handler(data):
            received_data.append(data)

        register_sse_handler(test_handler)

        # Simuler un message SSE
        test_message = {
            "type": "progress",
            "task_id": "test-task-123",
            "step": "Test en cours",
            "current": 50,
            "total": 100,
            "percent": 50
        }

        # Appeler le handler directement
        test_handler(test_message)

        assert len(received_data) == 1
        assert received_data[0] == test_message

    def test_progress_handler_format(self):
        """Test du format des messages de progression."""
        from frontend.theme.layout import make_progress_handler

        # Test que le handler est créé correctement
        handler = make_progress_handler("test-task-123")

        # Test message de progression valide
        progress_data = {
            "type": "progress",
            "task_id": "test-task-123",
            "step": "Extraction en cours",
            "current": 25,
            "total": 100,
            "percent": 25
        }

        # Le handler ne devrait pas lever d'exception
        try:
            handler(progress_data)
        except Exception as e:
            pytest.fail(f"Handler a levé une exception: {e}")

    def test_progress_handler_filtering(self):
        """Test du filtrage des messages de progression."""
        from frontend.theme.layout import make_progress_handler

        handler = make_progress_handler("test-task-123")

        # Test message avec mauvais type - ne devrait pas lever d'exception
        wrong_type_data = {
            "type": "other",
            "task_id": "test-task-123",
            "step": "Test"
        }

        try:
            handler(wrong_type_data)
        except Exception as e:
            pytest.fail(f"Handler a levé une exception pour mauvais type: {e}")

        # Test message avec mauvais task_id - ne devrait pas lever d'exception
        wrong_task_data = {
            "type": "progress",
            "task_id": "other-task",
            "step": "Test"
        }

        try:
            handler(wrong_task_data)
        except Exception as e:
            pytest.fail(f"Handler a levé une exception pour mauvais task_id: {e}")


def test_websocket_compatibility():
    """Test que les WebSockets existants fonctionnent toujours."""
    from frontend.websocket_manager.ws_client import register_ws_handler, handlers

    # Nettoyer les handlers existants
    handlers.clear()

    def test_ws_handler(data):
        pass

    register_ws_handler(test_ws_handler)

    assert len(handlers) == 1
    assert test_ws_handler in handlers


def test_sse_vs_websocket_separation():
    """Test que SSE et WebSocket sont bien séparés."""
    from frontend.websocket_manager.ws_client import (
        register_ws_handler, handlers,
        register_sse_handler, sse_handlers
    )

    # Nettoyer les handlers
    handlers.clear()
    sse_handlers.clear()

    def ws_handler(data):
        pass

    def sse_handler(data):
        pass

    register_ws_handler(ws_handler)
    register_sse_handler(sse_handler)

    # Vérifier la séparation
    assert len(handlers) == 1
    assert len(sse_handlers) == 1
    assert ws_handler in handlers
    assert sse_handler in sse_handlers
    assert ws_handler not in sse_handlers
    assert sse_handler not in handlers


if __name__ == "__main__":
    # Exécuter les tests
    import pytest
    pytest.main([__file__, "-v"])