from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from backend.api.schemas.search_schema import SearchQuery, SearchResult
from backend.api.services.search_service import SearchService
from backend.api.services.search_indexing_service import SearchIndexingService
from backend.api.utils.database import get_db
from backend.api.utils.logging import logger


router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/typeahead")
async def typeahead_search(
    q: str = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Recherche typeahead pour la barre de recherche."""
    try:
        if not q or not q.strip():
            return {"items": []}

        results = SearchService.typeahead_search(q, limit, db)
        return {"items": results}

    except Exception as e:
        logger.error(f"Erreur recherche typeahead: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Typeahead search failed: {str(e)}")

@router.post("/", response_model=SearchResult)
async def search(
    query: SearchQuery,
    db: Session = Depends(get_db)
):
    """Recherche principale avec scoring hybride."""
    try:
        # Validation basique
        if query.page < 1:
            query.page = 1
        if query.page_size < 1 or query.page_size > 100:
            query.page_size = 20

        result = SearchService.search(query, db)
        return result

    except Exception as e:
        logger.error(f"Erreur recherche principale: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/indexing/update-all")
async def update_all_search_indexes(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Met à jour tous les index de recherche TSVECTOR."""
    try:
        # Lancer en arrière-plan pour éviter timeout
        background_tasks.add_task(SearchIndexingService.update_all_search_vectors, db)
        return {"message": "Mise à jour des index lancée en arrière-plan", "status": "running"}
    except Exception as e:
        logger.error(f"Erreur lancement mise à jour index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")

@router.post("/indexing/create-triggers")
async def create_auto_indexing_triggers(db: Session = Depends(get_db)):
    """Crée les triggers PostgreSQL pour l'indexation automatique."""
    try:
        success = SearchIndexingService.create_triggers_for_auto_indexing(db)
        if success:
            return {"message": "Triggers d'indexation automatique créés", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Échec création triggers")
    except Exception as e:
        logger.error(f"Erreur création triggers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create triggers: {str(e)}")

@router.post("/indexing/create-materialized-views")
async def create_materialized_views(db: Session = Depends(get_db)):
    """Crée les vues matérialisées pour optimiser les facettes."""
    try:
        success = SearchIndexingService.create_materialized_views_for_facets(db)
        if success:
            return {"message": "Vues matérialisées créées", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Échec création vues matérialisées")
    except Exception as e:
        logger.error(f"Erreur création vues matérialisées: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create materialized views: {str(e)}")

@router.post("/indexing/refresh-materialized-views")
async def refresh_materialized_views(db: Session = Depends(get_db)):
    """Rafraîchit les vues matérialisées pour les facettes."""
    try:
        success = SearchIndexingService.refresh_materialized_views(db)
        if success:
            return {"message": "Vues matérialisées rafraîchies", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Échec rafraîchissement vues matérialisées")
    except Exception as e:
        logger.error(f"Erreur rafraîchissement vues matérialisées: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh materialized views: {str(e)}")

@router.get("/cache/stats")
async def get_cache_stats():
    """Récupère les statistiques du cache Redis."""
    try:
        from backend.api.services.redis_cache_service import redis_cache_service
        stats = redis_cache_service.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération stats cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@router.delete("/cache/search")
async def clear_search_cache():
    """Vide le cache de recherche."""
    try:
        from backend.api.services.redis_cache_service import redis_cache_service
        deleted_count = redis_cache_service.invalidate_search_cache()
        return {"message": f"Cache de recherche vidé: {deleted_count} clés supprimées", "status": "success"}
    except Exception as e:
        logger.error(f"Erreur vidage cache recherche: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear search cache: {str(e)}")

@router.delete("/cache/facets")
async def clear_facets_cache():
    """Vide le cache des facettes."""
    try:
        from backend.api.services.redis_cache_service import redis_cache_service
        success = redis_cache_service.invalidate_facets_cache()
        return {"message": "Cache des facettes vidé", "status": "success" if success else "warning"}
    except Exception as e:
        logger.error(f"Erreur vidage cache facettes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear facets cache: {str(e)}")

@router.delete("/cache/all")
async def clear_all_cache():
    """Vide complètement le cache Redis."""
    try:
        from backend.api.services.redis_cache_service import redis_cache_service
        success = redis_cache_service.clear_all_cache()
        return {"message": "Cache complètement vidé", "status": "success" if success else "warning"}
    except Exception as e:
        logger.error(f"Erreur vidage cache complet: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear all cache: {str(e)}")

@router.get("/indexing/stats")
async def get_indexing_stats(db: Session = Depends(get_db)):
    """Récupère les statistiques d'indexation."""
    try:
        stats = SearchIndexingService.get_indexing_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération stats indexation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# Endpoints dépréciés - maintenus pour compatibilité
@router.post("/index")
def api_get_or_create_index(index_dir: str = None):
    """Endpoint déprécié - PostgreSQL gère automatiquement l'indexation."""
    logger.warning("Endpoint /index déprécié - utiliser PostgreSQL TSVECTOR")
    return {"message": "Indexation automatique via PostgreSQL", "deprecated": True}

@router.post("/add")
def api_add_to_index():
    """Endpoint déprécié - données indexées automatiquement."""
    logger.warning("Endpoint /add déprécié - indexation automatique")
    return {"message": "Indexation automatique", "deprecated": True}
