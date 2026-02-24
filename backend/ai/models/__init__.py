"""
Module models — Modèles LLM personnalisés pour pydantic-ai.

Fournit des implémentations de l'interface pydantic-ai Model pour
les différents fournisseurs LLM utilisés par SoniqueBay.

Exports :
    KoboldNativeModel : Modèle natif KoboldCPP (API /api/v1/generate)
    KoboldStreamedResponse : Réponse streamée SSE native KoboldCPP
"""
from backend.ai.models.kobold_model import KoboldNativeModel, KoboldStreamedResponse

__all__ = [
    "KoboldNativeModel",
    "KoboldStreamedResponse",
]
