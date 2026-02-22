# -*- coding: utf-8 -*-
"""
Service de génération de synonyms via le serveur LLM local.

Rôle:
    Génère des termes de recherche, tags liés et contextes d'usage
    pour les tags musicaux (genres, moods) en utilisant le modèle
    défini dans le conteneur `llm-service` (par défaut llama3.2:1b).
    Utilise également un service d'embeddings local (all-mpnet-base-v2, 768D).

Dépendances:
    - backend_worker.utils.logging: logger
    - backend_worker.services.ollama_embedding_service: OllamaEmbeddingService
    - httpx: client HTTP pour appeler le serveur LLM

Auteur: SoniqueBay Team
"""

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from backend_worker.services.ollama_embedding_service import (
    OllamaEmbeddingService,
    OllamaEmbeddingError,
)
from backend_worker.utils.logging import logger


class OllamaSynonymGenerationError(Exception):
    """Exception pour les erreurs de génération de synonyms."""

    pass


class OllamaSynonymService:
    """
    Service pour générer des synonyms via Ollama.

    Ce service utilise llama3.2:1b pour générer des termes de recherche,
    tags liés et contextes d'usage pour un tag musical. Il utilise également
    nomic-embed-text pour générer des embeddings sémantiques.

    Exemple:
        >>> service = OllamaSynonymService()
        >>> result = await service.generate_synonyms("Rock", "genre")
        >>> result["search_terms"]
        ['rock', 'rock music', 'rock and roll', ...]
    """

    # Modèles
    TEXT_MODEL = "llama3.2:1b"  # Modèle léger pour RPi4
    EMBEDDING_MODEL = "all-mpnet-base-v2"  # 768 dimensions via sentence-transformers (compatible pgvector)

    # Configuration
    # ancien nom conservé pour compatibilité environnementale
    OLLAMA_HOST = "http://ollama:11434"
    LLM_HOST = "http://llm-service:11434"

    # Prompt système pour génération de synonyms
    SYNONYM_PROMPT = """
Tu es un expert en musique. Génère des synonymes et termes associés pour le tag musical: "{tag_name}"

Tags similaires disponibles: {related_tags}

Génère un JSON avec:
- "search_terms": [] termes de recherche (5-10) en FR et EN
- "related_tags": [] tags musicalement liés (5-10)
- "usage_context": [] contextes d'usage (3-5)
- "translations": {{}} traductions par langue

Format JSON uniquement, pas de markdown.
""".strip()

    def __init__(
        self,
        ollama_host: str = None,
        embedding_service: OllamaEmbeddingService = None,
    ) -> None:
        """Initialise le service de génération de synonyms.

        Args:
            ollama_host: URL du serveur LLM (la variable d'environnement
                précédente s'appelait OLLAMA_BASE_URL – on continue de
                l'accepter). Par défaut on utilise LLM_HOST qui pointe vers
                le conteneur `llm-service`.
            embedding_service: Service d'embeddings (optionnel, créé si non fourni)
        """
        # détermine host à utiliser (priorité argument, puis env var, puis LLM_HOST)
        self.llm_host = (
            ollama_host or
            self.OLLAMA_HOST or
            self.LLM_HOST
        )

        # client HTTP synchrone pour vérifications simples (utilisé par
        # is_text_model_available, etc.)
        self.client = httpx.Client(base_url=self.llm_host, timeout=5.0)
        # client HTTP asynchrone pour les appels de génération
        self.async_client = httpx.AsyncClient(base_url=self.llm_host, timeout=30.0)

        # Service d'embeddings partagé
        self.embedding_service = embedding_service or OllamaEmbeddingService(
            host=self.llm_host
        )

        logger.info(
            f"[SYNONYM] Service initialisé avec host={self.llm_host}, "
            f"text_model={self.TEXT_MODEL}, embedding_model={self.EMBEDDING_MODEL}"
        )

    async def generate_synonyms(
        self,
        tag_name: str,
        tag_type: str = "genre",
        related_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Génère les synonyms pour un tag via Ollama.

        Args:
            tag_name: Nom du genre ou mood
            tag_type: Type de tag ('genre' ou 'mood')
            related_tags: Tags similaires pour contexte

        Returns:
            Dict avec:
                - search_terms: List[str]
                - related_tags: List[str]
                - usage_context: List[str]
                - translations: Dict[str, str]
                - embedding: List[float] (optionnel)

        Raises:
            OllamaSynonymGenerationError: Si la génération échoue
        """
        try:
            # Formatter le prompt
            prompt = self._format_prompt(tag_name, related_tags)

            # Appeler Ollama pour la génération de texte
            logger.info(f"[SYNONYM] Génération synonyms pour '{tag_name}'")
            response = await self._call_ollama(prompt)

            # Parser le JSON
            synonym_data = self._parse_response(response)

            # Ajouter le tag_name comme source
            synonym_data["source_tag"] = tag_name
            synonym_data["tag_type"] = tag_type

            logger.info(
                f"[SYNONYM] {len(synonym_data.get('search_terms', []))} "
                f"termes générés pour '{tag_name}'"
            )

            return synonym_data

        except OllamaSynonymGenerationError:
            raise
        except Exception as e:
            logger.error(f"[SYNONYM] Erreur génération synonyms: {e}")
            raise OllamaSynonymGenerationError(
                f"Échec génération synonyms pour '{tag_name}': {e}"
            )

    async def generate_embedding(self, text: str) -> List[float]:
        """Génère un embedding sémantique via le service local.

        Args:
            text: Texte à vectoriser

        Returns:
            Vecteur de 768 dimensions

        Raises:
            OllamaEmbeddingError: Si la génération échoue
        """
        return await self.embedding_service.get_embedding(text)

    async def generate_synonyms_with_embedding(
        self,
        tag_name: str,
        tag_type: str = "genre",
        related_tags: Optional[List[str]] = None,
        include_embedding: bool = True,
    ) -> Dict[str, Any]:
        """Génère les synonyms et l'embedding pour un tag.

        Args:
            tag_name: Nom du genre ou mood
            tag_type: Type de tag ('genre' ou 'mood')
            related_tags: Tags similaires pour contexte
            include_embedding: Si True, génère aussi l'embedding

        Returns:
            Dict avec synonyms et optionnellement embedding
        """
        # Générer les synonyms
        synonym_data = await self.generate_synonyms(
            tag_name=tag_name,
            tag_type=tag_type,
            related_tags=related_tags,
        )

        # Générer l'embedding si demandé
        if include_embedding:
            # Utiliser le tag_name + search_terms pour l'embedding
            embedding_text = f"{tag_name}: {', '.join(synonym_data.get('search_terms', []))}"
            try:
                embedding = await self.generate_embedding(embedding_text)
                synonym_data["embedding"] = embedding
            except OllamaEmbeddingError as e:
                logger.warning(
                    f"[SYNONYM] Échec génération embedding pour '{tag_name}': {e}"
                )
                synonym_data["embedding"] = None

        return synonym_data

    def _format_prompt(self, tag_name: str, related_tags: Optional[List[str]]) -> str:
        """Formate le prompt pour la génération de synonyms.

        Args:
            tag_name: Nom du tag
            related_tags: Liste des tags liés

        Returns:
            Prompt formaté
        """
        related_tags_str = ", ".join(related_tags) if related_tags else ""

        return self.SYNONYM_PROMPT.format(
            tag_name=tag_name,
            related_tags=related_tags_str,
        )

    async def _call_ollama(self, prompt: str) -> str:
        """Envoie le prompt au serveur LLM via HTTP.

        Ce code remplace l'ancien client Ollama et est conçu pour
        fonctionner avec le conteneur `llm-service` qui expose une API
        compatible type OpenAI chat completions.

        Args:
            prompt: Prompt à envoyer au modèle

        Returns:
            Texte généré par le modèle

        Raises:
            OllamaSynonymGenerationError: Si l'appel échoue
        """
        try:
            payload = {
                "model": self.TEXT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                # max_tokens peut être ajusté en fonction des besoins
                "max_tokens": 512,
            }

            response = await self.async_client.post(
                "/api/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            # OpenAI style response
            choices = data.get("choices") or []
            if not choices:
                raise OllamaSynonymGenerationError("Réponse LLM sans choix")

            # contenu du premier choix
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            if not content:
                raise OllamaSynonymGenerationError("Réponse LLM vide")

            return content

        except Exception as e:
            logger.error(f"[SYNONYM] Erreur appel LLM: {e}")
            raise OllamaSynonymGenerationError(f"Échec appel LLM: {e}")

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse JSON d'Ollama.

        Args:
            response: Réponse textuelle d'Ollama

        Returns:
            Dict avec les données parsées
        """
        try:
            # Nettoyer la réponse (enlever les markers markdown si présents)
            cleaned_response = self._clean_json_response(response)

            # Parser le JSON
            data = json.loads(cleaned_response)

            # Valider la structure
            required_keys = ["search_terms", "related_tags", "usage_context", "translations"]
            for key in required_keys:
                if key not in data:
                    logger.warning(
                        f"[SYNONYM] Clé manquante dans la réponse: {key}"
                    )
                    data[key] = []

            # S'assurer que les listes sont des listes
            data["search_terms"] = self._ensure_list(data.get("search_terms"))
            data["related_tags"] = self._ensure_list(data.get("related_tags"))
            data["usage_context"] = self._ensure_list(data.get("usage_context"))

            # S'assurer que translations est un dict
            if not isinstance(data.get("translations"), dict):
                data["translations"] = {}

            return data

        except json.JSONDecodeError as e:
            logger.error(f"[SYNONYM] Erreur parsing JSON: {e}")
            logger.debug(f"[SYNONYM] Réponse complète: {response}")
            raise OllamaSynonymGenerationError(f"Erreur parsing JSON: {e}")

    def _clean_json_response(self, response: str) -> str:
        """Nettoie la réponse JSON des markers markdown.

        Args:
            response: Réponse brute

        Returns:
            JSON nettoyé
        """
        # Enlever les ```json et ```
        response = re.sub(r"```json\s*", "", response)
        response = re.sub(r"\s*```", "", response)

        # Enlever les ``` seuls
        response = re.sub(r"```\s*", "", response)

        return response.strip()

    def _ensure_list(self, value: Any) -> List[str]:
        """S'assure que la valeur est une liste de strings.

        Args:
            value: Valeur à convertir

        Returns:
            Liste de strings
        """
        if isinstance(value, list):
            return [str(item) for item in value]
        elif isinstance(value, str):
            # Si c'est une string, essayer de la parser comme JSON
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            return [value]
        elif value is None:
            return []
        else:
            return [str(value)]

    def is_text_model_available(self) -> bool:
        """Vérifie si le modèle de texte est disponible sur le serveur LLM.

        Cette méthode reste synchrone pour faciliter les tests et s'appuie sur
        un endpoint `/api/models` prévu par le conteneur.

        Returns:
            True si le modèle est listé
        """
        try:
            resp = self.client.get("/api/models")
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            # les éléments sont des dicts avec clé 'name'
            return any(self.TEXT_MODEL in m.get("name", "") for m in models)
        except Exception as e:
            logger.error(f"[SYNONYM] Erreur vérification modèle: {e}")
            return False

    async def pull_text_model(self) -> bool:
        """Tentative de récupération du modèle sur le serveur.

        Le conteneur `llm-service` gère lui‑même le téléchargement au démarrage
        selon la variable d'environnement. Il n'est donc généralement pas
        nécessaire d'appeler cette méthode.

        Returns:
            True si le serveur confirme la présence du modèle, False sinon
        """
        # on se contente de vérifier la disponibilité
        available = self.is_text_model_available()
        if not available:
            logger.warning(
                f"[SYNONYM] Modèle {self.TEXT_MODEL} non disponible"
            )
        return available

    async def batch_generate_synonyms(
        self,
        tags: List[Dict[str, str]],
        fail_silently: bool = False,
    ) -> List[Dict[str, Any]]:
        """Génère les synonyms pour une liste de tags.

        Args:
            tags: Liste de dicts avec 'name' et 'type'
            fail_silently: Si True, continue même si un tag échoue

        Returns:
            Liste des résultats pour chaque tag
        """
        results = []
        for tag in tags:
            tag_name = tag.get("name")
            tag_type = tag.get("type", "genre")
            related_tags = tag.get("related_tags")

            try:
                result = await self.generate_synonyms(
                    tag_name=tag_name,
                    tag_type=tag_type,
                    related_tags=related_tags,
                )
                result["status"] = "success"
                results.append(result)
            except OllamaSynonymGenerationError as e:
                if fail_silently:
                    logger.warning(
                        f"[SYNONYM] Échec pour '{tag_name}', suite..."
                    )
                    results.append({
                        "source_tag": tag_name,
                        "tag_type": tag_type,
                        "status": "error",
                        "error": str(e),
                        "search_terms": [],
                        "related_tags": [],
                        "usage_context": [],
                        "translations": {},
                    })
                else:
                    raise

        logger.info(
            f"[SYNONYM] Batch terminé: {len(results)}/{len(tags)} tags traités"
        )
        return results
