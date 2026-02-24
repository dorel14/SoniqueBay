
"""
Module Ollama - Fournit l'accès aux modèles LLM via le service unifié.
Supporte Ollama et KoboldCPP (natif ou OpenAI-compatible).
"""
import os
from typing import TYPE_CHECKING

from backend.api.services.llm_service import get_llm_service_sync
from backend.api.utils.logging import logger

if TYPE_CHECKING:
    from backend.ai.models.kobold_model import KoboldNativeModel

# Initialiser le service LLM avec lazy initialization
llm_service = get_llm_service_sync()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")  # docker-compose
DEFAULT_OLLAMA_MODEL = os.getenv("AGENT_MODEL", "Qwen/Qwen3-4B-Instruct:Q3_K_M")


def get_kobold_model(
    model_name: str = None,
    base_url: str = None,
) -> "KoboldNativeModel":
    """
    Retourne un KoboldNativeModel configuré pour l'API native KoboldCPP.

    Utilise l'API native (/api/v1/generate + /api/extra/generate/stream)
    plutôt que l'API OpenAI-compatible, permettant l'accès aux paramètres
    avancés (tfs, top_a, min_p, rep_pen, etc.).

    Args:
        model_name: Nom du modèle (défaut : AGENT_MODEL env var)
        base_url: URL de base KoboldCPP (défaut : KOBOLDCPP_BASE_URL env var)

    Returns:
        KoboldNativeModel: Instance configurée du modèle natif KoboldCPP
    """
    # Import local pour éviter les imports circulaires au niveau module
    from backend.ai.models.kobold_model import KoboldNativeModel

    effective_url = base_url or os.getenv(
        "KOBOLDCPP_BASE_URL", "http://llm-service:5001"
    )
    effective_model = model_name or os.getenv(
        "AGENT_MODEL", "kobold-local"
    )

    logger.debug(
        f"[ollama] Création KoboldNativeModel: model={effective_model}, url={effective_url}"
    )

    return KoboldNativeModel(
        base_url=effective_url,
        model_name=effective_model,
    )


def get_ollama_model(
    model_name: str = None,
    num_ctx: int = 4096,
    temperature: float = 0.7,
    top_p: float = 0.9,
):
    """
    Récupère un modèle LLM configuré (Ollama ou KoboldCPP).

    Routing automatique selon le provider détecté :
    - Si provider == 'koboldcpp' → KoboldNativeModel (API native)
    - Sinon → OpenAIChatModel via OllamaProvider

    Args:
        model_name: Nom du modèle (utilise le modèle par défaut si None)
        num_ctx: Taille du contexte (ignoré pour KoboldNativeModel,
                 géré via KOBOLD_CTX_LENGTH env var)
        temperature: Température de génération (ignorée pour KoboldNativeModel,
                     gérée au niveau ModelSettings)
        top_p: Valeur top_p (ignorée pour KoboldNativeModel)

    Returns:
        KoboldNativeModel si provider=koboldcpp,
        OpenAIChatModel sinon (Ollama ou autre OpenAI-compatible)
    """
    # S'assurer que le service est initialisé avant de lire provider_type
    if not llm_service._initialized:
        llm_service.initialize()

    if llm_service.provider_type == "koboldcpp":
        logger.debug(
            f"[ollama] Provider koboldcpp détecté → KoboldNativeModel (model={model_name})"
        )
        return get_kobold_model(model_name=model_name)

    # Fallback : OpenAIChatModel via OllamaProvider (ou autre provider OpenAI-compatible)
    # Note: num_ctx, temperature et top_p sont gérés au niveau des requêtes API
    # OpenAIChatModel ne supporte pas ces paramètres dans son constructeur
    logger.debug(
        f"[ollama] Provider {llm_service.provider_type} → OpenAIChatModel (model={model_name})"
    )
    return llm_service.get_model(model_name=model_name)
