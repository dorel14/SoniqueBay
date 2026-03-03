"""Tests unitaires pour frontend/utils/supabase_client.py.

Vérifie que get_supabase_client() lève une ValueError si SUPABASE_ANON_KEY
n'est pas définie, sans utiliser de clé JWT hardcodée en fallback.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest


class TestGetSupabaseClientFrontend:
    """Tests pour la fonction get_supabase_client() du frontend."""

    def setup_method(self):
        """Réinitialise le singleton avant chaque test."""
        import frontend.utils.supabase_client as mod
        mod._supabase_client = None

    def teardown_method(self):
        """Réinitialise le singleton après chaque test."""
        import frontend.utils.supabase_client as mod
        mod._supabase_client = None

    def test_raises_if_anon_key_missing(self):
        """ValueError levée si SUPABASE_ANON_KEY est absente."""
        env = {"SUPABASE_URL": "http://localhost:54321"}
        with patch.dict(os.environ, env, clear=False):
            # Supprimer la clé si elle existe
            os.environ.pop("SUPABASE_ANON_KEY", None)
            from frontend.utils.supabase_client import get_supabase_client
            with pytest.raises(ValueError, match="SUPABASE_ANON_KEY"):
                get_supabase_client()

    def test_raises_if_anon_key_empty_string(self):
        """ValueError levée si SUPABASE_ANON_KEY est une chaîne vide."""
        with patch.dict(os.environ, {"SUPABASE_ANON_KEY": "", "SUPABASE_URL": "http://localhost:54321"}):
            import frontend.utils.supabase_client as mod
            mod._supabase_client = None
            from frontend.utils.supabase_client import get_supabase_client
            with pytest.raises(ValueError, match="SUPABASE_ANON_KEY"):
                get_supabase_client()

    def test_no_hardcoded_jwt_in_source(self):
        """Vérifie qu'aucun JWT hardcodé n'est présent dans le fichier source."""
        from pathlib import Path
        source = Path("frontend/utils/supabase_client.py").read_text(encoding="utf-8")
        # Le token hardcodé précédent commençait par eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in source, (
            "Un JWT hardcodé a été détecté dans frontend/utils/supabase_client.py — "
            "ne jamais committer de credentials dans le code source"
        )

    def test_raises_not_falls_back_to_hardcoded_key(self):
        """Confirme que le comportement est fail-fast (ValueError) et non fallback silencieux."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SUPABASE_ANON_KEY", None)
            import frontend.utils.supabase_client as mod
            mod._supabase_client = None
            from frontend.utils.supabase_client import get_supabase_client
            # Doit lever, pas retourner silencieusement un client avec clé hardcodée
            with pytest.raises(ValueError):
                get_supabase_client()

    def test_initializes_with_valid_key(self):
        """Client créé correctement quand SUPABASE_ANON_KEY est définie."""
        mock_client = MagicMock()
        with patch.dict(os.environ, {
            "SUPABASE_ANON_KEY": "valid-test-key",
            "SUPABASE_URL": "http://localhost:54321"
        }):
            import frontend.utils.supabase_client as mod
            mod._supabase_client = None
            with patch("frontend.utils.supabase_client.create_client", return_value=mock_client) as mock_create:
                from frontend.utils.supabase_client import get_supabase_client
                client = get_supabase_client()
                mock_create.assert_called_once_with("http://localhost:54321", "valid-test-key")
                assert client is mock_client

    def test_singleton_returns_same_instance(self):
        """get_supabase_client() retourne toujours la même instance (singleton)."""
        mock_client = MagicMock()
        with patch.dict(os.environ, {
            "SUPABASE_ANON_KEY": "valid-test-key",
            "SUPABASE_URL": "http://localhost:54321"
        }):
            import frontend.utils.supabase_client as mod
            mod._supabase_client = None
            with patch("frontend.utils.supabase_client.create_client", return_value=mock_client):
                from frontend.utils.supabase_client import get_supabase_client
                c1 = get_supabase_client()
                c2 = get_supabase_client()
                assert c1 is c2

    def test_reset_clears_singleton(self):
        """reset_supabase_client() force la réinitialisation du singleton."""
        import frontend.utils.supabase_client as mod
        mod._supabase_client = MagicMock()
        from frontend.utils.supabase_client import reset_supabase_client
        reset_supabase_client()
        assert mod._supabase_client is None
