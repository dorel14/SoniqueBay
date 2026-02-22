# -*- coding: utf-8 -*-
"""
Router API pour les endpoints MIRSynonym.

Ce router expose les endpoints REST pour:
- Récupérer les synonyms d'un tag
- Rechercher des synonyms (hybride FTS + vectorielle)
- Créer ou mettre à jour des synonyms
- Désactiver des synonyms
- Déclencher la génération de synonyms via Celery

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body

from backend.api.schemas.synonyms_schema import (
    DeleteResponse,
    GenerateRequest,
    SearchResponse,
    SearchResultItem,
    SynonymRequest,
    SynonymResponse,
    TriggerTaskResponse,
)
from backend.api.services.mir_synonym_service import MIRSynonymService
from backend.api.utils.celery_app import celery_app
from backend.api.utils.database import AsyncSession, get_async_session
from backend.api.utils.logging import logger


# ============================================================================
# Router Synonyms
# ============================================================================

router = APIRouter(prefix="/api/synonyms", tags=["Synonyms"])


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/{tag_type}/{tag_value}",
    response_model=SynonymResponse,
    summary="Récupérer les synonyms d'un tag",
    description="Retourne les synonyms dynamiques pour un tag spécifique.",
)
async def get_synonyms(
    tag_type: str,
    tag_value: str,
    db: AsyncSession = Depends(get_async_session),
) -> SynonymResponse:
    """
    Récupère les synonyms pour un tag (genre ou mood).

    Args:
        tag_type: Type de tag ('genre' ou 'mood')
        tag_value: Valeur du tag
        db: Session de base de données

    Returns:
        Les synonyms associés au tag

    Raises:
        HTTPException: Si le tag n'est pas trouvé
    """
    try:
        logger.info(f"[SYNONYMS] GET {tag_type}/{tag_value}")

        service = MIRSynonymService(db)
        synonym = await service.get_synonyms(tag_type, tag_value)

        if not synonym:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun synonym trouvé pour {tag_type}:{tag_value}",
            )

        return SynonymResponse(**synonym)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SYNONYMS] Erreur GET {tag_type}/{tag_value}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des synonyms: {str(e)}",
        )


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Rechercher des synonyms",
    description="Recherche hybride FTS + vectorielle pour trouver des synonyms.",
)
async def search_synonyms(
    q: str,
    tag_type: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session),
) -> SearchResponse:
    """
    Recherche des synonyms via recherche hybride.

    La recherche combine:
    - PostgreSQL Full-Text Search (FTS) sur les termes de recherche
    - Recherche vectorielle via pgvector sur les embeddings

    Args:
        q: Terme de recherche
        tag_type: Filtrer par type ('genre' ou 'mood')
        limit: Nombre maximum de résultats (défaut: 10)
        db: Session de base de données

    Returns:
        Liste des synonyms correspondants avec leurs scores
    """
    try:
        # Valider les paramètres
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100

        if tag_type and tag_type not in ["genre", "mood"]:
            raise HTTPException(
                status_code=400,
                detail="tag_type doit être 'genre' ou 'mood'",
            )

        logger.info(f"[SYNONYMS] Search '{q}' (type={tag_type}, limit={limit})")

        service = MIRSynonymService(db)
        results = await service.search_synonyms(q, tag_type, limit)

        # Convertir en format de réponse
        result_items = []
        for r in results:
            result_items.append(
                SearchResultItem(
                    tag_type=r.get("tag_type", ""),
                    tag_value=r.get("tag_value", ""),
                    synonyms=r.get("synonyms", {}),
                    fts_score=r.get("fts_score", r.get("hybrid_score", 0.0) * 0.3),
                    vector_score=r.get("vector_score", r.get("hybrid_score", 0.0) * 0.7),
                    hybrid_score=r.get("hybrid_score", 0.0),
                )
            )

        return SearchResponse(
            query=q,
            count=len(result_items),
            results=result_items,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SYNONYMS] Erreur recherche: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche: {str(e)}",
        )


@router.post(
    "/",
    response_model=SynonymResponse,
    summary="Créer ou mettre à jour des synonyms",
    description="Crée ou met à jour les synonyms pour un tag.",
)
async def create_synonyms(
    request: SynonymRequest,
    db: AsyncSession = Depends(get_async_session),
) -> SynonymResponse:
    """
    Crée ou met à jour les synonyms pour un tag.

    Args:
        request: Requête contenant le tag et les synonyms
        db: Session de base de données

    Returns:
        Le synonym créé ou mis à jour

    Raises:
        HTTPException: Si une erreur survient
    """
    try:
        logger.info(
            f"[SYNONYMS] POST create {request.tag_type}/{request.tag_value}"
        )

        # Valider la structure synonyms
        if not request.synonyms:
            raise HTTPException(
                status_code=400,
                detail="Le champ 'synonyms' est requis",
            )

        service = MIRSynonymService(db)
        synonym = await service.create_synonyms(
            tag_type=request.tag_type,
            tag_value=request.tag_value,
            synonyms=request.synonyms,
            confidence=request.confidence,
        )

        if not synonym:
            raise HTTPException(
                status_code=500,
                detail="Échec de la création des synonyms",
            )

        return SynonymResponse(**synonym)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SYNONYMS] Erreur création: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création: {str(e)}",
        )


@router.delete(
    "/{tag_type}/{tag_value}",
    response_model=DeleteResponse,
    summary="Désactiver les synonyms d'un tag",
    description="Désactive (soft delete) les synonyms pour un tag.",
)
async def deactivate_synonyms(
    tag_type: str,
    tag_value: str,
    db: AsyncSession = Depends(get_async_session),
) -> DeleteResponse:
    """
    Désactive les synonyms pour un tag.

    Args:
        tag_type: Type de tag ('genre' ou 'mood')
        tag_value: Valeur du tag
        db: Session de base de données

    Returns:
        Confirmation de la désactivation
    """
    try:
        logger.info(
            f"[SYNONYMS] DELETE {tag_type}/{tag_value}"
        )

        service = MIRSynonymService(db)
        success = await service.deactivate_synonyms(tag_type, tag_value)

        if success:
            return DeleteResponse(
                success=True,
                message=f"Synonyms désactivés pour {tag_type}:{tag_value}",
            )
        else:
            return DeleteResponse(
                success=False,
                message=f"Aucun synonym trouvé pour {tag_type}:{tag_value}",
            )

    except Exception as e:
        logger.error(f"[SYNONYMS] Erreur suppression: {e}")
        return DeleteResponse(
            success=False,
            message=f"Erreur lors de la désactivation: {str(e)}",
        )


@router.post(
    "/webhook/trigger",
    response_model=TriggerTaskResponse,
    summary="Déclencher la génération de synonyms via Celery",
    description="Lance la génération de synonyms via une tâche Celery asynchrone.",
)
async def trigger_synonym_generation(
    request: GenerateRequest,
) -> TriggerTaskResponse:
    """
    Déclenche la génération de synonyms via Ollama/Celery.

    Cette endpoint lance une tâche Celery asynchrone pour générer
    les synonyms sémantiques pour un tag via Ollama.

    Args:
        request: Requête contenant le tag à traiter

    Returns:
        Identifiant de la tâche Celery et message de confirmation

    Raises:
        HTTPException: Si l'envoi de la tâche échoue
    """
    try:
        logger.info(
            f"[SYNONYMS] Trigger génération {request.tag_type}/{request.tag_value} "
            f"(force={request.force})"
        )

        # Envoyer la tâche Celery
        task = celery_app.send_task(
            "synonym.generate_synonyms_for_tag",
            args=[
                request.tag_type,
                request.tag_value,
            ],
            kwargs={"force": request.force},
            queue="synonym",
            priority=5,
        )

        logger.info(f"[SYNONYMS] Tâche Celery créée: {task.id}")

        return TriggerTaskResponse(
            task_id=task.id,
            message=f"Tâche de génération créée pour {request.tag_type}:{request.tag_value}",
        )

    except Exception as e:
        logger.error(
            f"[SYNONYMS] Erreur lors du déclenchement de la génération: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du déclenchement: {str(e)}",
        )


@router.post(
    "/webhook/trigger_batch",
    response_model=TriggerTaskResponse,
    summary="Déclencher la génération batch de synonyms",
    description="Lance la génération de synonyms pour plusieurs tags via Celery.",
)
async def trigger_batch_synonym_generation(
    tag_type: str = Body(
        ...,
        description="Type de tag ('genre' ou 'mood')",
        pattern="^(genre|mood)$",
    ),
) -> TriggerTaskResponse:
    """
    Déclenche la génération batch de tous les tags d'un type.

    Cette endpoint lance une tâche Celery pour générer
    les synonyms pour tous les tags d'un type donné.

    Args:
        tag_type: Type de tag à traiter ('genre' ou 'mood')

    Returns:
        Identifiant de la tâche Celery et message de confirmation
    """
    try:
        logger.info(f"[SYNONYMS] Trigger génération batch pour {tag_type}")

        # Envoyer la tâche Celery
        task = celery_app.send_task(
            "synonym.generate_all_synonyms",
            args=[tag_type],
            queue="synonym",
            priority=3,
        )

        logger.info(f"[SYNONYMS] Tâche batch créée: {task.id}")

        return TriggerTaskResponse(
            task_id=task.id,
            message=f"Tâche de génération batch créée pour {tag_type}",
        )

    except Exception as e:
        logger.error(
            f"[SYNONYMS] Erreur lors du déclenchement batch: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du déclenchement: {str(e)}",
        )


@router.get(
    "/health",
    summary="Vérifier la santé du service",
    description="Retourne le statut du service de synonyms.",
)
async def health_check() -> dict:
    """
    Vérifie la santé du service de synonyms.

    Returns:
        Statut du service
    """
    return {
        "status": "healthy",
        "service": "mir_synonym",
        "version": "1.0.0",
    }
