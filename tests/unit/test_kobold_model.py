"""
Tests unitaires pour KoboldNativeModel et KoboldStreamedResponse.

Teste l'implémentation de l'interface pydantic-ai 1.x Model pour KoboldCPP :
- Requêtes non-streaming via /api/v1/generate
- Requêtes streaming via /api/extra/generate/stream (SSE natif)
- Formatage des messages en ChatML
- Construction du payload KoboldCPP
"""
import json
import pytest
from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from pydantic_ai.models import ModelRequestParameters

from backend.ai.models.kobold_model import KoboldNativeModel, KoboldStreamedResponse


# Paramètres de requête par défaut pour les tests (tous les champs ont des valeurs par défaut)
DEFAULT_MODEL_REQUEST_PARAMS = ModelRequestParameters()


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_model_message(role: str, content: str):
    """Crée un message pydantic-ai mocké avec part_kind."""
    part = MagicMock()
    part.part_kind = role
    part.content = content
    msg = MagicMock()
    msg.parts = [part]
    return msg


def make_sse_lines(tokens: list[str], done: bool = True) -> list[str]:
    """Génère des lignes SSE simulant la réponse KoboldCPP."""
    lines = []
    for token in tokens:
        data = json.dumps({"token": token, "finish_reason": None})
        lines.append(f"data: {data}")
    if done:
        lines.append("data: [DONE]")
    return lines


# ---------------------------------------------------------------------------
# Tests KoboldNativeModel.__init__
# ---------------------------------------------------------------------------

class TestKoboldNativeModelInit:
    """Tests d'initialisation du modèle."""

    def test_init_with_defaults(self):
        """Vérifie les valeurs par défaut depuis les variables d'environnement."""
        with patch.dict("os.environ", {
            "KOBOLDCPP_BASE_URL": "http://test-kobold:5001",
            "AGENT_MODEL": "test-model-q4",
        }):
            model = KoboldNativeModel()
            assert model.base_url == "http://test-kobold:5001"
            assert model._model_name == "test-model-q4"

    def test_init_with_explicit_params(self):
        """Vérifie que les paramètres explicites priment sur les env vars."""
        model = KoboldNativeModel(
            base_url="http://custom:5001",
            model_name="custom-model",
        )
        assert model.base_url == "http://custom:5001"
        assert model._model_name == "custom-model"

    def test_base_url_trailing_slash_stripped(self):
        """Vérifie que le slash final est supprimé de l'URL."""
        model = KoboldNativeModel(base_url="http://kobold:5001/")
        assert model.base_url == "http://kobold:5001"

    def test_model_name_property(self):
        """Vérifie la propriété model_name."""
        model = KoboldNativeModel(model_name="qwen2.5-3b")
        assert model.model_name == "qwen2.5-3b"

    def test_system_property(self):
        """Vérifie que system retourne 'koboldcpp'."""
        model = KoboldNativeModel()
        assert model.system == "koboldcpp"


# ---------------------------------------------------------------------------
# Tests _format_messages (ChatML)
# ---------------------------------------------------------------------------

class TestFormatMessages:
    """Tests du formatage des messages en ChatML."""

    def setup_method(self):
        self.model = KoboldNativeModel(
            base_url="http://localhost:5001",
            model_name="test-model",
        )

    def test_system_prompt_formatting(self):
        """Vérifie le formatage d'un message système."""
        msg = make_model_message("system-prompt", "Tu es un assistant musical.")
        result = self.model._format_messages([msg])

        assert "<|im_start|>system" in result
        assert "Tu es un assistant musical." in result
        assert "</s>" in result

    def test_user_prompt_formatting(self):
        """Vérifie le formatage d'un message utilisateur."""
        msg = make_model_message("user-prompt", "Quelle est la meilleure chanson ?")
        result = self.model._format_messages([msg])

        assert "<|im_start|>user" in result
        assert "Quelle est la meilleure chanson ?" in result
        assert "</s>" in result

    def test_assistant_text_formatting(self):
        """Vérifie le formatage d'une réponse assistant (historique)."""
        msg = make_model_message("text", "Voici ma réponse.")
        result = self.model._format_messages([msg])

        assert "<|im_start|>assistant" in result
        assert "Voici ma réponse." in result

    def test_assistant_marker_appended(self):
        """Vérifie que le marqueur de début de réponse assistant est ajouté."""
        msg = make_model_message("user-prompt", "Bonjour")
        result = self.model._format_messages([msg])

        # Le prompt doit se terminer par le marqueur assistant
        assert result.endswith("<|im_start|>assistant\n")

    def test_full_conversation_order(self):
        """Vérifie l'ordre correct dans une conversation complète."""
        system_msg = make_model_message("system-prompt", "Système")
        user_msg = make_model_message("user-prompt", "Question")
        assistant_msg = make_model_message("text", "Réponse")

        result = self.model._format_messages([system_msg, user_msg, assistant_msg])

        system_pos = result.find("<|im_start|>system")
        user_pos = result.find("<|im_start|>user")
        assistant_pos = result.find("<|im_start|>assistant")

        assert system_pos < user_pos < assistant_pos

    def test_empty_messages(self):
        """Vérifie le comportement avec une liste vide."""
        result = self.model._format_messages([])
        # Doit au moins contenir le marqueur assistant
        assert "<|im_start|>assistant\n" in result

    def test_tool_return_formatting(self):
        """Vérifie le formatage d'un résultat de tool."""
        part = MagicMock()
        part.part_kind = "tool-return"
        part.tool_name = "search_tracks"
        part.content = '{"tracks": ["Song A", "Song B"]}'
        msg = MagicMock()
        msg.parts = [part]

        result = self.model._format_messages([msg])

        assert "<|im_start|>tool" in result
        assert "[search_tracks]" in result


# ---------------------------------------------------------------------------
# Tests _build_payload
# ---------------------------------------------------------------------------

class TestBuildPayload:
    """Tests de la construction du payload KoboldCPP."""

    def setup_method(self):
        self.model = KoboldNativeModel(
            base_url="http://localhost:5001",
            model_name="test-model",
        )

    def test_default_payload_structure(self):
        """Vérifie la structure du payload avec settings=None."""
        payload = self.model._build_payload("test prompt", None)

        assert "prompt" in payload
        assert payload["prompt"] == "test prompt"
        assert "max_length" in payload
        assert "temperature" in payload
        assert "top_p" in payload
        assert "quiet" in payload
        assert payload["quiet"] is True

    def test_koboldcpp_native_params_present(self):
        """Vérifie que les paramètres natifs KoboldCPP sont inclus."""
        payload = self.model._build_payload("prompt", None)

        # Paramètres natifs non disponibles via API OpenAI
        assert "tfs" in payload
        assert "top_a" in payload
        assert "min_p" in payload
        assert "typical" in payload
        assert "rep_pen" in payload
        assert "rep_pen_range" in payload

    def test_default_values(self):
        """Vérifie les valeurs par défaut."""
        payload = self.model._build_payload("prompt", None)

        assert payload["max_length"] == 512
        assert payload["temperature"] == 0.7
        assert payload["top_p"] == 0.9
        assert payload["rep_pen"] == 1.1
        assert payload["min_p"] == 0.05

    def test_model_settings_override(self):
        """Vérifie que ModelSettings surcharge les valeurs par défaut."""
        settings = MagicMock()
        settings.max_tokens = 1024
        settings.temperature = 0.5
        settings.top_p = 0.8

        payload = self.model._build_payload("prompt", settings)

        assert payload["max_length"] == 1024
        assert payload["temperature"] == 0.5
        assert payload["top_p"] == 0.8

    def test_max_context_length_from_env(self):
        """Vérifie que max_context_length est configurable via env var."""
        with patch.dict("os.environ", {"KOBOLD_CTX_LENGTH": "4096"}):
            payload = self.model._build_payload("prompt", None)
            assert payload["max_context_length"] == 4096


# ---------------------------------------------------------------------------
# Tests KoboldNativeModel.request (non-streaming)
# ---------------------------------------------------------------------------

class TestKoboldNativeModelRequest:
    """Tests de la méthode request() non-streaming."""

    def setup_method(self):
        self.model = KoboldNativeModel(
            base_url="http://localhost:5001",
            model_name="test-model",
        )

    @pytest.mark.asyncio
    async def test_request_success(self):
        """Vérifie une requête non-streaming réussie."""
        mock_response_data = {
            "results": [{"text": "Voici ma réponse générée."}]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        # Create mock client with post method
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "backend.ai.models.kobold_model.get_llm_http_client",
            return_value=mock_client,
        ):
            result = await self.model.request(
                messages=[make_model_message("user-prompt", "Bonjour")],
                model_settings=None,
                model_request_params=MagicMock(),
            )

        assert result is not None
        assert len(result.parts) == 1
        assert result.parts[0].content == "Voici ma réponse générée."
        assert result.model_name == "test-model"
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_request_connect_error_raises(self):
        """Vérifie que ConnectError est propagée avec un log d'erreur."""
        # Create mock client that raises ConnectError
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch(
            "backend.ai.models.kobold_model.get_llm_http_client",
            return_value=mock_client,
        ):
            with pytest.raises(httpx.ConnectError):
                await self.model.request(
                    messages=[make_model_message("user-prompt", "Test")],
                    model_settings=None,
                    model_request_params=MagicMock(),
                )

    @pytest.mark.asyncio
    async def test_request_invalid_response_format_raises(self):
        """Vérifie que ValueError est levée si le format de réponse est inattendu."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected": "format"}
        mock_response.raise_for_status = MagicMock()

        # Create mock client with post method
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "backend.ai.models.kobold_model.get_llm_http_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError, match="Format de réponse KoboldCPP inattendu"):
                await self.model.request(
                    messages=[make_model_message("user-prompt", "Test")],
                    model_settings=None,
                    model_request_params=MagicMock(),
                )


# ---------------------------------------------------------------------------
# Tests KoboldStreamedResponse
# ---------------------------------------------------------------------------

class TestKoboldStreamedResponse:
    """Tests de la réponse streamée SSE."""

    def _make_mock_response(self, sse_lines: list[str]):
        """Crée un mock de réponse HTTPX avec des lignes SSE."""
        async def aiter_lines():
            for line in sse_lines:
                yield line

        mock_response = MagicMock()
        mock_response.aiter_lines = aiter_lines
        return mock_response

    def _make_streamed(self, mock_response, model_name: str = "test-model") -> KoboldStreamedResponse:
        """Crée un KoboldStreamedResponse avec les paramètres requis."""
        return KoboldStreamedResponse(
            model_request_parameters=DEFAULT_MODEL_REQUEST_PARAMS,
            response=mock_response,
            base_url="http://localhost:5001",
            model_name=model_name,
        )

    @pytest.mark.asyncio
    async def test_streams_tokens_from_sse(self):
        """Vérifie que les tokens SSE sont correctement parsés et yielded."""
        tokens = ["Bonjour", " ", "le", " ", "monde"]
        sse_lines = make_sse_lines(tokens)
        mock_response = self._make_mock_response(sse_lines)

        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        # On doit avoir reçu des événements pour chaque token non-vide
        non_empty_tokens = [t for t in tokens if t.strip()]
        assert len(events) >= len(non_empty_tokens)

    @pytest.mark.asyncio
    async def test_stops_on_done_marker(self):
        """Vérifie que le streaming s'arrête sur [DONE]."""
        sse_lines = [
            'data: {"token": "Hello"}',
            "data: [DONE]",
            'data: {"token": "Should not appear"}',  # Ne doit pas être yielded
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        # Seulement "Hello" doit être yielded, pas "Should not appear"
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_stops_on_finish_reason_stop(self):
        """Vérifie que le streaming s'arrête sur finish_reason=stop."""
        sse_lines = [
            'data: {"token": "Token1", "finish_reason": null}',
            'data: {"token": "Token2", "finish_reason": "stop"}',
            'data: {"token": "Token3", "finish_reason": null}',  # Ne doit pas apparaître
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        # Token1 et Token2 yielded, Token3 non
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_continues_on_string_null_finish_reason(self):
        """Vérifie que le streaming continue quand finish_reason est la chaîne 'null'."""
        # Régression fix: certains versions de KoboldCPP retournent "null" (string) au lieu de null (JSON)
        sse_lines = [
            'data: {"token": "Token1", "finish_reason": "null"}',
            'data: {"token": "Token2", "finish_reason": "null"}',
            'data: {"token": "Token3", "finish_reason": "stop"}',
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        # Tous les tokens doivent être yielded car "null" (string) ne doit pas arrêter le stream
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_continues_on_json_null_finish_reason(self):
        """Vérifie que le streaming continue quand finish_reason est JSON null."""
        sse_lines = [
            'data: {"token": "Token1", "finish_reason": null}',
            'data: {"token": "Token2", "finish_reason": null}',
            'data: {"token": "Token3", "finish_reason": "stop"}',
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        # Tous les tokens doivent être yielded car null (JSON) ne doit pas arrêter le stream
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_stops_on_various_real_finish_reasons(self):
        """Vérifie que le streaming s'arrête sur différentes valeurs réelles de finish_reason."""
        test_cases = [
            ("stop", "Arrêt normal"),
            ("length", "Limite de longueur atteinte"),
            ("eos_token", "Token de fin détecté"),
        ]

        for finish_reason, description in test_cases:
            sse_lines = [
                f'data: {{"token": "Hello", "finish_reason": "{finish_reason}"}}',
                f'data: {{"token": "Should not appear", "finish_reason": null}}',
            ]
            mock_response = self._make_mock_response(sse_lines)
            streamed = self._make_streamed(mock_response)

            events = []
            async for event in streamed:
                events.append(event)

            # Seul le premier token doit être yielded, le stream doit s'arrêter
            assert len(events) == 1, f"Échec pour {description} ({finish_reason})"

    @pytest.mark.asyncio
    async def test_ignores_invalid_json_lines(self):
        """Vérifie que les lignes JSON invalides sont ignorées silencieusement."""
        sse_lines = [
            "data: not-valid-json",
            'data: {"token": "Valid"}',
            "data: [DONE]",
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        # Seulement "Valid" doit être yielded
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_ignores_empty_lines(self):
        """Vérifie que les lignes vides sont ignorées."""
        sse_lines = [
            "",
            "   ",
            'data: {"token": "Hello"}',
            "data: [DONE]",
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        assert len(events) == 1

    def test_model_name_property(self):
        """Vérifie la propriété model_name."""
        mock_response = MagicMock()
        streamed = KoboldStreamedResponse(
            model_request_parameters=DEFAULT_MODEL_REQUEST_PARAMS,
            response=mock_response,
            model_name="my-model",
        )
        assert streamed.model_name == "my-model"

    def test_timestamp_property(self):
        """Vérifie que timestamp est une datetime."""
        mock_response = MagicMock()
        streamed = KoboldStreamedResponse(
            model_request_parameters=DEFAULT_MODEL_REQUEST_PARAMS,
            response=mock_response,
            model_name="test",
        )
        assert isinstance(streamed.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_text_field_fallback(self):
        """Vérifie le fallback sur le champ 'text' si 'token' absent."""
        sse_lines = [
            'data: {"text": "Fallback token"}',
            "data: [DONE]",
        ]
        mock_response = self._make_mock_response(sse_lines)
        streamed = self._make_streamed(mock_response)

        events = []
        async for event in streamed:
            events.append(event)

        assert len(events) == 1


# ---------------------------------------------------------------------------
# Tests get_kobold_model (factory)
# ---------------------------------------------------------------------------

class TestGetKoboldModel:
    """Tests de la fonction factory get_kobold_model."""

    def test_returns_kobold_native_model(self):
        """Vérifie que get_kobold_model retourne bien un KoboldNativeModel."""
        from backend.ai.ollama import get_kobold_model

        model = get_kobold_model(
            base_url="http://localhost:5001",
            model_name="test-model",
        )
        assert isinstance(model, KoboldNativeModel)

    def test_uses_env_vars_as_defaults(self):
        """Vérifie que les env vars sont utilisées comme valeurs par défaut."""
        from backend.ai.ollama import get_kobold_model

        with patch.dict("os.environ", {
            "KOBOLDCPP_BASE_URL": "http://env-kobold:5001",
            "AGENT_MODEL": "env-model",
        }):
            model = get_kobold_model()
            assert model.base_url == "http://env-kobold:5001"
            assert model._model_name == "env-model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
