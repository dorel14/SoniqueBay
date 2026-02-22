
"""
Module Ollama - Fournit l'accès aux modèles LLM via le service unifié.
Supporte Ollama et KoboldCPP.
"""
import os
from backend.api.services.llm_service import get_llm_service_sync

# Initialiser le service LLM avec lazy initialization
llm_service = get_llm_service_sync()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")  # docker-compose
DEFAULT_OLLAMA_MODEL = os.getenv("AGENT_MODEL", "Qwen/Qwen3-4B-Instruct:Q3_K_M")


def get_ollama_model(
    model_name: str = None,
    num_ctx: int = 4096,
    temperature: float = 0.7,
    top_p: float = 0.9
):
    """
    Récupère un modèle LLM configuré (Ollama ou KoboldCPP).
    
    Args:
        model_name: Nom du modèle (utilise le modèle par défaut si None)
        num_ctx: Taille du contexte
        temperature: Température de génération
        top_p: Valeur top_p pour la génération
        
    Returns:
        OpenAIChatModel configuré avec le fournisseur détecté
    """
    return llm_service.get_model(
        model_name=model_name,
        num_ctx=num_ctx,
        temperature=temperature,
        top_p=top_p
    )
