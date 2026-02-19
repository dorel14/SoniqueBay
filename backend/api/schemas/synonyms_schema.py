# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour les endpoints MIR Synonyms.

Ce module définit les modèles de validation pour :
- Requêtes de création/mise à jour de synonyms
- Réponses pour les synonyms
- Résultats de recherche hybride FTS + vectorielle
- Tâches Celery asynchrones

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional

from pydantic import BaseModel, Field


class SynonymRequest(BaseModel):
    """Requête pour créer ou mettre à jour des synonyms."""

    tag_type: str = Field(
        ...,
        description="Type de tag ('genre' ou 'mood')",
        pattern="^(genre|mood)$",
    )
    tag_value: str = Field(
        ..., min_length=1, max_length=100, description="Valeur du tag"
    )
    synonyms: dict = Field(
        ...,
        description="Structure JSONB contenant les synonyms",
        example={
            "search_terms": ["rock", "hard rock"],
            "related_tags": ["energetic", "guitar"],
            "usage_context": ["party", "workout"],
            "translations": {"en": ["rock"], "fr": ["rock"]},
        },
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Score de confiance"
    )


class SynonymResponse(BaseModel):
    """Réponse pour un synonym."""

    id: int = Field(..., description="Identifiant unique")
    tag_type: str = Field(..., description="Type de tag")
    tag_value: str = Field(..., description="Valeur du tag")
    synonyms: dict = Field(..., description="Structure JSONB des synonyms")
    search_terms: list[str] = Field(default_factory=list, description="Termes de recherche")
    related_tags: list[str] = Field(default_factory=list, description="Tags liés")
    usage_contexts: list[str] = Field(default_factory=list, description="Contextes d'usage")
    translations: dict = Field(default_factory=dict, description="Traductions")
    source: str = Field(default="ollama", description="Source de génération")
    confidence: float = Field(..., description="Score de confiance")
    is_active: bool = Field(..., description="Statut d'activation")


class SearchResultItem(BaseModel):
    """Élément de résultat de recherche."""

    tag_type: str = Field(..., description="Type de tag")
    tag_value: str = Field(..., description="Valeur du tag")
    synonyms: dict = Field(..., description="Structure JSONB des synonyms")
    fts_score: float = Field(default=0.0, description="Score FTS")
    vector_score: float = Field(default=0.0, description="Score vectoriel")
    hybrid_score: float = Field(default=0.0, description="Score hybride pondéré")


class SearchResponse(BaseModel):
    """Réponse pour la recherche de synonyms."""

    query: str = Field(..., description="Requête de recherche")
    count: int = Field(..., description="Nombre de résultats")
    results: list[SearchResultItem] = Field(
        default_factory=list, description="Résultats"
    )


class TriggerTaskResponse(BaseModel):
    """Réponse lors du déclenchement d'une tâche Celery."""

    task_id: str = Field(..., description="Identifiant de la tâche Celery")
    message: str = Field(..., description="Message de confirmation")


class DeleteResponse(BaseModel):
    """Réponse lors de la désactivation d'un synonym."""

    success: bool = Field(..., description="Succès de l'opération")
    message: str = Field(..., description="Message de confirmation")


class GenerateRequest(BaseModel):
    """Requête pour déclencher la génération de synonyms."""

    tag_type: str = Field(
        ...,
        description="Type de tag ('genre' ou 'mood')",
        pattern="^(genre|mood)$",
    )
    tag_value: str = Field(
        ..., min_length=1, max_length=100, description="Valeur du tag"
    )
    force: bool = Field(
        default=False, description="Forcer la régénération même si existant"
    )
