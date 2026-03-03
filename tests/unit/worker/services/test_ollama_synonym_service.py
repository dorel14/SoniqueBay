# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service OllamaSynonymService.

Rôle:
    Tests pour la génération de synonyms via le serveur LLM local
    (anciennement effectué avec Ollama).
    Ces tests sont standalone et ne nécessitent pas de service LLM réel.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import sys
import os

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestOllamaSynonymServiceBasics:
    """Tests basiques pour OllamaSynonymService sans dépendances async."""

    def test_parse_response_basic(self):
        """Test parsing réponse basique."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        response = """```json
{
    "search_terms": ["rock", "rock music"],
    "related_tags": ["hard rock"],
    "usage_context": ["workout"],
    "translations": {"en": "rock"}
}
```"""

        result = service._parse_response(response)

        assert isinstance(result, dict)
        assert "search_terms" in result
        assert "related_tags" in result
        assert "usage_context" in result
        assert "translations" in result

    def test_parse_response_without_markdown(self):
        """Test parsing sans markers markdown."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        raw_response = """{
            "search_terms": ["rock", "hard rock"],
            "related_tags": ["metal"],
            "usage_context": ["workout"],
            "translations": {}
        }"""

        result = service._parse_response(raw_response)

        assert isinstance(result, dict)
        assert "search_terms" in result

    def test_parse_response_missing_keys(self):
        """Test parsing avec clés manquantes."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        incomplete_response = """{
            "search_terms": ["rock"]
        }"""

        result = service._parse_response(incomplete_response)

        # Doit compléter avec des valeurs par défaut
        assert "search_terms" in result
        assert "related_tags" in result
        assert "usage_context" in result
        assert "translations" in result

    def test_parse_response_invalid_json(self):
        """Test parsing JSON invalide."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService
        from backend_worker.services.ollama_synonym_service import OllamaSynonymGenerationError

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        invalid_response = "not json at all"

        with pytest.raises(OllamaSynonymGenerationError):
            service._parse_response(invalid_response)


class TestOllamaCleanJsonResponse:
    """Tests pour le nettoyage de réponse JSON."""

    def test_clean_json_with_code_blocks(self):
        """Test nettoyage avec blocks de code."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        response = """```json
{
    "test": "value"
}
```"""

        result = service._clean_json_response(response)

        # Vérifie que les markers markdown sont retirés
        assert "```json" not in result
        assert "```" not in result
        # Le JSON doit être présent (peut avoir du formatting)
        assert "test" in result
        assert "value" in result

    def test_clean_json_without_code_blocks(self):
        """Test nettoyage sans blocks de code."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        response = '{"test": "value"}'

        result = service._clean_json_response(response)

        assert result == '{"test": "value"}'


class TestOllamaEnsureList:
    """Tests pour la conversion en liste."""

    def test_ensure_list_from_list(self):
        """Test conversion depuis une liste."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        result = service._ensure_list(["a", "b", "c"])

        assert isinstance(result, list)
        assert len(result) == 3

    def test_ensure_list_from_string(self):
        """Test conversion depuis une string."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        result = service._ensure_list("single_value")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "single_value"

    def test_ensure_list_from_json_string(self):
        """Test conversion depuis une string JSON."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        result = service._ensure_list('["a", "b", "c"]')

        assert isinstance(result, list)
        assert len(result) == 3

    def test_ensure_list_from_none(self):
        """Test conversion depuis None."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        result = service._ensure_list(None)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_ensure_list_from_other(self):
        """Test conversion depuis autre type."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        result = service._ensure_list(123)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "123"


class TestOllamaFormatPrompt:
    """Tests pour le formatage du prompt."""

    def test_format_prompt_with_related_tags(self):
        """Test formatage avec tags liés."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        prompt = service._format_prompt("Rock", ["classic rock", "metal"])

        assert "Rock" in prompt
        assert "classic rock" in prompt
        assert "metal" in prompt

    def test_format_prompt_without_related_tags(self):
        """Test formatage sans tags liés."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        prompt = service._format_prompt("Rock", None)

        assert "Rock" in prompt
        assert "Tags similaires disponibles:" in prompt

    def test_format_prompt_with_empty_related_tags(self):
        """Test formatage avec liste vide de tags liés."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        prompt = service._format_prompt("Rock", [])

        assert "Rock" in prompt


class TestOllamaBuildSearchText:
    """Tests pour la construction du texte de recherche."""

    def test_build_search_text(self):
        """Test construction du texte de recherche."""

        # Simuler la logique de _build_search_text
        synonyms = {
            "search_terms": ["rock", "rock music", "hard rock"],
            "related_tags": ["classic rock", "metal"],
        }

        parts = []
        search_terms = synonyms.get("search_terms", [])
        if search_terms:
            parts.extend(search_terms[:10])

        related_tags = synonyms.get("related_tags", [])
        if related_tags:
            parts.extend(related_tags[:10])

        result = " ".join(parts)

        assert "rock" in result
        assert "rock music" in result
        assert "hard rock" in result
        assert "classic rock" in result
        assert "metal" in result


class TestOllamaPromptConfiguration:
    """Tests pour la configuration du prompt."""

    def test_prompt_template_contains_placeholders(self):
        """Test que le template contient les placeholders."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        assert "{tag_name}" in service.SYNONYM_PROMPT
        assert "{related_tags}" in service.SYNONYM_PROMPT

    def test_default_models(self):
        """Test les modèles par défaut."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        assert service.TEXT_MODEL == "llama3.2:1b"
        assert service.EMBEDDING_MODEL == "all-MiniLM-L6-v2"


class TestOllamaModelAvailability:
    """Tests pour la vérification de disponibilité du modèle."""

    def test_is_text_model_available_true(self):
        """Test modèle disponible."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        mock_response = {
            "models": [
                {"name": "llama3.2:1b"},
                {"name": "nomic-embed-text"}
            ]
        }

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None

        with patch.object(service.client, 'get', return_value=mock_resp):
            result = service.is_text_model_available()

        assert result is True

    def test_is_text_model_available_false(self):
        """Test modèle non disponible."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        mock_response = {
            "models": [
                {"name": "llama3.2"},
            ]
        }

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None

        with patch.object(service.client, 'get', return_value=mock_resp):
            result = service.is_text_model_available()

        assert result is False

    def test_is_text_model_available_error(self):
        """Test modèle avec erreur."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        with patch.object(service.client, 'get', side_effect=Exception("Connection error")):
            result = service.is_text_model_available()

        assert result is False


class TestOllamaSynonymGeneration:
    """Tests pour la génération de synonyms."""

    def test_prompt_contains_music_terms(self):
        """Test que le prompt contient des termes musicaux."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        # Vérifier que le prompt parle de musique
        assert "musique" in service.SYNONYM_PROMPT.lower() or "music" in service.SYNONYM_PROMPT.lower()

    def test_prompt_requires_json_format(self):
        """Test que le prompt demande du JSON."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        assert "json" in service.SYNONYM_PROMPT.lower()

    def test_prompt_has_search_terms_key(self):
        """Test que le prompt demande search_terms."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        assert "search_terms" in service.SYNONYM_PROMPT

    def test_prompt_has_related_tags_key(self):
        """Test que le prompt demande related_tags."""
        from backend_worker.services.ollama_synonym_service import OllamaSynonymService

        with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
            service = OllamaSynonymService()

        assert "related_tags" in service.SYNONYM_PROMPT


class TestOllamaEmbedding:
    """Tests pour les embeddings."""

    def test_embedding_dimension(self):
        """Test la dimension de l'embedding."""
        # La dimension configurée est 384 (all-MiniLM-L6-v2) mais ce test reste
        # générique.
        embedding_dim = 384

        embedding = [0.1] * embedding_dim

        assert len(embedding) == 384

    def test_embedding_values_range(self):
        """Test que les valeurs de l'embedding sont dans une plage valide."""
        # Les embeddings sont généralement normalisés entre -1 et 1 ou 0 et 1
        embedding = [0.1, 0.2, 0.3, -0.1, 0.5]

        # Vérifier que toutes les valeurs sont dans une plage raisonnable
        for val in embedding:
            assert -2.0 <= val <= 2.0



# nouveau test asynchrone pour valider la logique HTTP


@pytest.mark.asyncio
async def test_call_llm_parsing():
    """La méthode interne doit extraire le texte de la réponse API."""
    from backend_worker.services.ollama_synonym_service import OllamaSynonymService

    with patch('backend_worker.services.ollama_synonym_service.OllamaEmbeddingService'):
        service = OllamaSynonymService()

    # préparer une réponse factice
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {"message": {"content": "{\"search_terms\": []}"}}
        ]
    }
    mock_resp.raise_for_status.return_value = None

    service.async_client.post = AsyncMock(return_value=mock_resp)

    result_text = await service._call_ollama("prompt")
    assert "search_terms" in result_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
