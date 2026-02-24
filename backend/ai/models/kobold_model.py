"""
Module KoboldNativeModel — Modèle PydanticAI natif pour KoboldCPP.

Implémente l'interface pydantic-ai 1.x Model en utilisant l'API native KoboldCPP
(/api/v1/generate et /api/extra/generate/stream) plutôt que l'API OpenAI-compatible.

Avantages par rapport à OpenAIChatModel + OpenAIProvider :
- Accès aux paramètres natifs KoboldCPP (tfs, top_a, min_p, typical, rep_pen)
- Streaming SSE natif sans couche de compatibilité OpenAI
- Meilleure gestion des erreurs spécifiques à KoboldCPP
- Contrôle total du format de prompt (ChatML, Llama3, etc.)

Configuration Docker :
    KOBOLDCPP_BASE_URL=http://llm-service:5001

Configuration locale :
    KOBOLDCPP_BASE_URL=http://localhost:5001
"""
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, List, Optional

import httpx

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
)
from pydantic_ai.models import (
    Model,
    ModelRequestParameters,
    StreamedResponse,
)
from pydantic_ai._parts_manager import ModelResponsePartsManager
from pydantic_ai._run_context import RunContext
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

from backend.api.utils.logging import logger


class KoboldStreamedResponse(StreamedResponse):
    """
    Réponse streamée depuis l'API native KoboldCPP.

    Implémente l'interface StreamedResponse de pydantic-ai 1.x en parsant
    les événements SSE de l'endpoint /api/extra/generate/stream.

    Format SSE natif KoboldCPP :
        data: {"token": "...", "finish_reason": null}
        data: {"token": "", "finish_reason": "stop"}

    Méthodes abstraites pydantic-ai 1.x implémentées :
        - _get_event_iterator : itérateur SSE → ModelResponseStreamEvent
        - provider_name       : identifiant du fournisseur
        - provider_url        : URL du service
    """

    def __init__(
        self,
        model_request_parameters: ModelRequestParameters,
        response: httpx.Response,
        base_url: str = "",
        model_name: str = "",
    ) -> None:
        """
        Initialise la réponse streamée.

        Args:
            model_request_parameters: Paramètres de requête pydantic-ai (requis par StreamedResponse)
            response: Réponse HTTPX en mode streaming (context manager actif)
            base_url: URL de base du service KoboldCPP (pour provider_url)
            model_name: Nom du modèle KoboldCPP (pour model_name property)

        Note: StreamedResponse est un @dataclass — on appelle super().__init__() avec
        model_request_parameters comme champ requis. Les autres champs internes
        (_parts_manager, _usage, etc.) sont initialisés par le parent.
        """
        # Appel du constructeur dataclass parent avec le champ requis
        super().__init__(model_request_parameters=model_request_parameters)
        self._response = response
        self._base_url = base_url
        self._model_name_str = model_name
        self._timestamp_dt = datetime.now()

    async def _get_event_iterator(self) -> AsyncIterator[Any]:
        """
        Itérateur interne sur le flux SSE natif KoboldCPP.

        Méthode abstraite de StreamedResponse (pydantic-ai 1.x).
        Yield des ModelResponseStreamEvent via ModelResponsePartsManager :
        - PartStartEvent au premier token (crée la TextPart)
        - PartDeltaEvent aux tokens suivants (ajoute du contenu)

        Note: Le vendor_part_id 'text' regroupe tous les tokens dans une
        seule TextPart.
        """
        async for line in self._response.aiter_lines():
            line = line.strip()
            if not line:
                continue

            # Les événements SSE commencent par "data: "
            if not line.startswith("data: "):
                continue

            data_str = line[6:]  # Supprimer le préfixe "data: "

            # Détection de fin de flux SSE standard
            if data_str.strip() == "[DONE]":
                logger.debug("[KoboldNative] Fin du flux SSE ([DONE])")
                return

            try:
                data = json.loads(data_str)

                # L'API native KoboldCPP renvoie 'token' ou 'text' selon la version
                token = data.get("token", data.get("text", ""))

                if token:
                    # handle_text_delta génère automatiquement :
                    # - PartStartEvent au premier appel (crée la TextPart)
                    # - PartDeltaEvent aux appels suivants (ajoute du contenu)
                    event = self._parts_manager.handle_text_delta(
                        vendor_part_id="text",
                        content=token,
                    )
                    if event is not None:
                        yield event

                # Vérifier si c'est la fin du stream (finish_reason)
                finish_reason = data.get("finish_reason")
                if finish_reason and finish_reason != "null":
                    logger.debug(
                        f"[KoboldNative] Fin du flux SSE (finish_reason={finish_reason})"
                    )
                    return

            except json.JSONDecodeError:
                logger.debug(
                    f"[KoboldNative] Ligne SSE non-JSON ignorée: {data_str[:80]}"
                )
                continue

    @property
    def provider_name(self) -> Optional[str]:
        """Identifiant du fournisseur (requis par pydantic-ai 1.x StreamedResponse)."""
        return "koboldcpp"

    @property
    def provider_url(self) -> Optional[str]:
        """URL du service (requis par pydantic-ai 1.x StreamedResponse)."""
        return self._base_url or None

    @property
    def model_name(self) -> str:
        """Nom du modèle KoboldCPP."""
        return self._model_name_str

    @property
    def timestamp(self) -> datetime:
        """Horodatage de début de la réponse."""
        return self._timestamp_dt


class KoboldNativeModel(Model):
    """
    Modèle PydanticAI natif pour KoboldCPP.

    Implémente l'interface pydantic-ai 1.x Model en utilisant directement
    l'API native KoboldCPP plutôt que la couche de compatibilité OpenAI.

    Endpoints utilisés :
        - POST /api/v1/generate          → requête non-streaming
        - POST /api/extra/generate/stream → requête streaming SSE

    Format de prompt : ChatML (compatible Qwen2.5, Mistral, Phi-3, etc.)

    Exemple d'utilisation :
        model = KoboldNativeModel(
            base_url="http://llm-service:5001",
            model_name="qwen2.5-3b-instruct-q4_k_m"
        )
        agent = Agent(model=model, system_prompt="Tu es un assistant musical.")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """
        Initialise le modèle KoboldCPP natif.

        Args:
            base_url: URL de base du service KoboldCPP.
                      Défaut : KOBOLDCPP_BASE_URL env var ou http://llm-service:5001
            model_name: Nom du modèle (utilisé pour les métadonnées pydantic-ai).
                        Défaut : AGENT_MODEL env var ou 'kobold-local'

        Note: On utilise _base_url (préfixé _) car la classe Model de pydantic-ai 1.x
        définit une propriété base_url en lecture seule (retourne None par défaut).
        On la surcharge via la propriété base_url ci-dessous.
        """
        # Appel du constructeur parent Model (keyword-only: settings, profile)
        super().__init__()

        # Utiliser _base_url pour stocker la valeur, exposée via la propriété base_url
        self._base_url = (
            base_url
            or os.getenv("KOBOLDCPP_BASE_URL", "http://llm-service:5001")
        ).rstrip("/")

        self._model_name = model_name or os.getenv(
            "AGENT_MODEL", "kobold-local"
        )

        # Client HTTPX optimisé pour Docker et les LLM (réponses potentiellement longues)
        # TODO(dev): Ajuster connect_timeout si KoboldCPP est lent à démarrer (RPi4)
        # TODO(dev): read=None signifie pas de timeout de lecture — surveiller la mémoire
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=None,    # Pas de timeout de lecture (réponses LLM longues)
                write=30.0,
                pool=10.0,
            ),
            limits=httpx.Limits(
                max_connections=10,            # Limité pour RPi4
                max_keepalive_connections=5,
            ),
            headers={"Connection": "keep-alive"},
        )

        logger.info(
            f"[KoboldNative] Modèle initialisé: {self._model_name} @ {self._base_url}"
        )

    async def request(
        self,
        messages: List[ModelMessage],
        model_settings: Optional[ModelSettings],
        model_request_params: ModelRequestParameters,
    ) -> ModelResponse:
        """
        Exécute une requête non-streaming via /api/v1/generate.

        Args:
            messages: Liste des messages de la conversation (pydantic-ai)
            model_settings: Paramètres du modèle (temperature, max_tokens, etc.)
            model_request_params: Paramètres de requête pydantic-ai (tools, etc.)

        Returns:
            ModelResponse: Réponse complète avec le texte généré

        Raises:
            httpx.HTTPStatusError: Si KoboldCPP retourne une erreur HTTP
            ValueError: Si le format de réponse est inattendu
        """
        prompt = self._format_messages(messages)
        payload = self._build_payload(prompt, model_settings)

        logger.debug(
            f"[KoboldNative] Requête non-streaming: {len(prompt)} chars de prompt"
        )

        try:
            response = await self._client.post("/api/v1/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            # L'API native KoboldCPP retourne {"results": [{"text": "..."}]}
            text = data["results"][0]["text"]

            logger.debug(
                f"[KoboldNative] Réponse reçue: {len(text)} chars"
            )

            return ModelResponse(
                parts=[TextPart(content=text)],
                model_name=self._model_name,
                timestamp=datetime.now(),
            )

        except httpx.ConnectError as e:
            logger.error(
                f"[KoboldNative] Impossible de se connecter à {self._base_url}: {e}. "
                "Vérifiez que KOBOLDCPP_BASE_URL pointe vers le bon service "
                "(Docker: http://llm-service:5001, local: http://localhost:5001)"
            )
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[KoboldNative] Erreur HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
            raise
        except (KeyError, IndexError) as e:
            logger.error(
                f"[KoboldNative] Format de réponse inattendu: {e}. "
                f"Réponse brute: {data if 'data' in locals() else 'N/A'}"
            )
            raise ValueError(
                f"Format de réponse KoboldCPP inattendu: {e}"
            ) from e

    @asynccontextmanager
    async def request_stream(
        self,
        messages: List[ModelMessage],
        model_settings: Optional[ModelSettings],
        model_request_params: ModelRequestParameters,
        run_context: Optional[Any] = None,
    ) -> AsyncIterator[StreamedResponse]:
        """
        Exécute une requête en streaming via /api/extra/generate/stream.

        Utilise le flux SSE natif de KoboldCPP pour un streaming token-par-token.
        Doit être utilisé comme context manager asynchrone :

            async with model.request_stream(messages, settings, params) as stream:
                async for event in stream:
                    ...

        Args:
            messages: Liste des messages de la conversation
            model_settings: Paramètres du modèle
            model_request_params: Paramètres de requête pydantic-ai

        Yields:
            KoboldStreamedResponse: Réponse streamée compatible pydantic-ai 1.x

        Raises:
            httpx.ConnectError: Si KoboldCPP n'est pas accessible
            httpx.HTTPStatusError: Si KoboldCPP retourne une erreur HTTP
        """
        prompt = self._format_messages(messages)
        payload = self._build_payload(prompt, model_settings)

        logger.debug(
            f"[KoboldNative] Requête streaming: {len(prompt)} chars de prompt"
        )

        try:
            async with self._client.stream(
                "POST",
                "/api/extra/generate/stream",
                json=payload,
            ) as response:
                response.raise_for_status()
                logger.debug("[KoboldNative] Connexion SSE établie, début du streaming")
                yield KoboldStreamedResponse(
                    model_request_parameters=model_request_params,
                    response=response,
                    base_url=self._base_url,
                    model_name=self._model_name,
                )

        except httpx.ConnectError as e:
            logger.error(
                f"[KoboldNative] Impossible de se connecter à {self._base_url}: {e}. "
                "Vérifiez que KOBOLDCPP_BASE_URL pointe vers le bon service "
                "(Docker: http://llm-service:5001, local: http://localhost:5001)"
            )
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[KoboldNative] Erreur HTTP streaming {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
            raise

    def _format_messages(self, messages: List[ModelMessage]) -> str:
        """
        Convertit les messages pydantic-ai en prompt ChatML pour KoboldCPP.

        Format ChatML (compatible Qwen2.5, Mistral, Phi-3, etc.) :
            <|im_start|>system
            {system_content}
            <|im_end|>
            <|im_start|>user
            {user_content}
            <|im_end|>
            <|im_start|>assistant

        Args:
            messages: Liste des messages pydantic-ai (ModelRequest | ModelResponse)

        Returns:
            str: Prompt formaté en ChatML prêt pour KoboldCPP
        """
        parts: List[str] = []

        for msg in messages:
            if not hasattr(msg, "parts"):
                continue

            for part in msg.parts:
                part_kind = getattr(part, "part_kind", None)

                if part_kind == "system-prompt":
                    content = getattr(part, "content", "")
                    parts.append(f"<|im_start|>system\n{content}<|im_end|>")

                elif part_kind == "user-prompt":
                    content = getattr(part, "content", "")
                    # Gestion des contenus multimodaux (liste de parts)
                    if not isinstance(content, str):
                        content = " ".join(
                            getattr(p, "text", str(p))
                            for p in content
                            if hasattr(p, "text") or isinstance(p, str)
                        )
                    parts.append(f"<|im_start|>user\n{content}<|im_end|>")

                elif part_kind == "text":
                    # Réponse assistant précédente (historique de conversation)
                    content = getattr(part, "content", "")
                    parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")

                elif part_kind == "tool-return":
                    # Résultat d'un appel de tool
                    tool_name = getattr(part, "tool_name", "tool")
                    content = getattr(part, "content", "")
                    parts.append(
                        f"<|im_start|>tool\n[{tool_name}]: {content}<|im_end|>"
                    )

                elif part_kind == "retry-prompt":
                    # Message de retry (erreur de validation)
                    content = getattr(part, "content", "")
                    if not isinstance(content, str):
                        content = str(content)
                    parts.append(f"<|im_start|>user\n{content}<|im_end|>")

        # Marqueur de début de réponse assistant (KoboldCPP continue à partir d'ici)
        parts.append("<|im_start|>assistant\n")

        return "\n".join(parts)

    def _build_payload(
        self,
        prompt: str,
        settings: Optional[ModelSettings],
    ) -> dict:
        """
        Construit le payload JSON pour l'API native KoboldCPP.

        Inclut les paramètres avancés non disponibles via l'API OpenAI-compatible,
        comme tfs, top_a, min_p, typical et rep_pen.

        Args:
            prompt: Prompt formaté en ChatML
            settings: Paramètres du modèle pydantic-ai (ModelSettings)

        Returns:
            dict: Payload JSON pour POST /api/v1/generate ou /api/extra/generate/stream
        """
        # Extraction des paramètres depuis ModelSettings (pydantic-ai 1.x)
        # getattr avec fallback None pour éviter AttributeError si settings=None
        max_tokens: int = getattr(settings, "max_tokens", None) or 512
        temperature: float = getattr(settings, "temperature", None) or 0.7
        top_p: float = getattr(settings, "top_p", None) or 0.9

        return {
            "prompt": prompt,
            "max_length": max_tokens,
            # TODO(dev): Rendre max_context_length configurable via env var
            # Valeur actuelle : 2048 tokens (adapté RPi4 avec 4GB RAM)
            "max_context_length": int(
                os.getenv("KOBOLD_CTX_LENGTH", "2048")
            ),
            "temperature": temperature,
            "top_p": top_p,
            "top_k": 100,
            # --- Paramètres natifs KoboldCPP (non disponibles via API OpenAI) ---
            "tfs": 1.0,           # Tail-free sampling (1.0 = désactivé)
            "top_a": 0.0,         # Top-A sampling (0.0 = désactivé)
            "min_p": 0.05,        # Min-P sampling
            "typical": 1.0,       # Typical sampling (1.0 = désactivé)
            "rep_pen": 1.1,       # Repetition penalty
            "rep_pen_range": 1024,
            "rep_pen_slope": 0.7,
            "quiet": True,        # Supprime les logs verbeux de KoboldCPP
        }

    @property
    def base_url(self) -> str:
        """URL de base du service KoboldCPP (propriété publique en lecture)."""
        return self._base_url

    @property
    def model_name(self) -> str:
        """Nom du modèle KoboldCPP (utilisé par pydantic-ai pour les métadonnées)."""
        return self._model_name

    @property
    def system(self) -> str:
        """Identifiant du système de modèle (utilisé par pydantic-ai)."""
        return "koboldcpp"

    async def aclose(self) -> None:
        """
        Ferme le client HTTPX proprement.

        À appeler lors de l'arrêt de l'application pour libérer les connexions.
        """
        await self._client.aclose()
        logger.debug("[KoboldNative] Client HTTPX fermé")
