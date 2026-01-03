"""
Tâche Celery pour le diagnostic des métadonnées manquantes
Utilise l'API backend au lieu de la connexion directe à la DB
Respecte l'architecture SoniqueBay
"""

import asyncio
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.metadata_diagnostic_api import run_metadata_diagnostic_via_api
from backend_worker.utils.redis_utils import get_redis_client


@celery.task(name="metadata.diagnostic_missing_fields", queue="maintenance", bind=True)
async def diagnostic_missing_metadata_task(self):
    """
    Tâche Celery pour diagnostiquer les métadonnées manquantes via l'API backend.
    
    Respecte l'architecture SoniqueBay :
    - Utilise l'API backend pour accéder aux données
    - Publie la progression via Redis/SSE
    - Ne fait pas d'accès direct à la DB
    
    Returns:
        Résultat du diagnostic avec recommandations
    """
    task_id = self.request.id
    start_time = asyncio.get_event_loop().time()
    
    logger.info(f"[DIAGNOSTIC TASK] Démarrage diagnostic métadonnées manquantes - Task ID: {task_id}")
    
    try:
        # Initialiser le client Redis pour la progression
        async def publish_progress(step: str, current: int, total: int = 100):
            """Publier la progression via Redis"""
            try:
                redis_client = await get_redis_client()
                progress_data = {
                    "task_id": task_id,
                    "type": "metadata_diagnostic_progress",
                    "step": step,
                    "current": current,
                    "total": total,
                    "timestamp": start_time
                }
                await redis_client.publish("progress", str(progress_data))
                logger.info(f"[DIAGNOSTIC TASK] Progression: {step} ({current}/{total})")
            except Exception as e:
                logger.error(f"[DIAGNOSTIC TASK] Erreur publication progression: {e}")
        
        # Étapes du diagnostic
        steps = [
            ("Initialisation", 10),
            ("Connexion API backend", 20),
            ("Récupération tracks", 40),
            ("Analyse métadonnées", 70),
            ("Calcul statistiques", 90),
            ("Génération rapport", 100)
        ]
        
        # Exécuter le diagnostic
        async def run_diagnostic():
            # Étape 1: Initialisation
            await publish_progress(steps[0][0], steps[0][1])
            
            # Étape 2: Connexion API backend
            await publish_progress(steps[1][0], steps[1][1])
            
            # Étape 3-6: Diagnostic via API
            await publish_progress(steps[2][0], steps[2][1])
            result = await run_metadata_diagnostic_via_api()
            
            # Finalisation
            for step_name, progress in steps[3:]:
                await publish_progress(step_name, progress)
            
            return result
        
        # Exécuter le diagnostic asynchrone
        diagnostic_result = asyncio.run(run_diagnostic())
        
        # Métriques finales
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Construire le résultat final
        final_result = {
            "task_id": task_id,
            "execution_time": execution_time,
            "status": "success",
            "timestamp": start_time,
            "diagnostic": diagnostic_result,
            "summary": {
                "total_tracks_analyzed": diagnostic_result.get("total_tracks_analyzed", 0),
                "tracks_without_album_id": diagnostic_result.get("album_id_missing", {}).get("missing", 0),
                "critical_metadata_missing": len([
                    field for field, stats in diagnostic_result.get("metadata_missing", {}).items()
                    if stats.get("percentage", 0) > 80
                ]),
                "recommendations_count": len(diagnostic_result.get("recommendations", []))
            }
        }
        
        # Log du résumé
        summary = final_result["summary"]
        logger.info("[DIAGNOSTIC TASK] === DIAGNOSTIC TERMINÉ ===")
        logger.info(f"[DIAGNOSTIC TASK] Tracks analysées: {summary['total_tracks_analyzed']}")
        logger.info(f"[DIAGNOSTIC TASK] Tracks sans album_id: {summary['tracks_without_album_id']}")
        logger.info(f"[DIAGNOSTIC TASK] Métadonnées critiques manquantes: {summary['critical_metadata_missing']}")
        logger.info(f"[DIAGNOSTIC TASK] Recommandations: {summary['recommendations_count']}")
        logger.info(f"[DIAGNOSTIC TASK] Durée: {execution_time:.2f}s")
        
        # Publication du résultat final
        try:
            redis_client = asyncio.run(get_redis_client())
            final_progress = {
                "task_id": task_id,
                "type": "metadata_diagnostic_complete",
                "status": "success",
                "summary": summary,
                "timestamp": start_time
            }
            await redis_client.publish("progress", str(final_progress))
        except Exception as e:
            logger.error(f"[DIAGNOSTIC TASK] Erreur publication résultat final: {e}")
        
        return final_result
        
    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        error_result = {
            "task_id": task_id,
            "execution_time": execution_time,
            "status": "error",
            "error": str(e),
            "timestamp": start_time
        }
        
        logger.error(f"[DIAGNOSTIC TASK] Erreur après {execution_time:.2f}s: {str(e)}")
        
        # Publication de l'erreur
        try:
            redis_client = asyncio.run(get_redis_client())
            error_progress = {
                "task_id": task_id,
                "type": "metadata_diagnostic_error",
                "status": "error",
                "error": str(e),
                "timestamp": start_time
            }
            await redis_client.publish("progress", str(error_progress))
        except Exception as pub_error:
            logger.error(f"[DIAGNOSTIC TASK] Erreur publication erreur: {pub_error}")
        
        return error_result


@celery.task(name="metadata.quick_diagnostic", queue="maintenance")
def quick_diagnostic_metadata_task():
    """
    Tâche rapide pour un diagnostic minimal des métadonnées.
    
    Plus légère que le diagnostic complet, pour des vérifications rapides.
    
    Returns:
        Statistiques de base sur les métadonnées
    """
    logger.info("[QUICK DIAGNOSTIC] Démarrage diagnostic rapide métadonnées")
    
    try:
        # Import du service de diagnostic
        from backend_worker.utils.metadata_diagnostic_api import metadata_diagnostic_api
        
        # Exécution du diagnostic
        async def run_quick_diagnostic():
            # Diagnostic rapide (limité)
            tracks = await metadata_diagnostic_api.get_all_tracks_with_metadata(limit=100)
            
            if not tracks:
                return {"error": "Aucune track trouvée"}
            
            # Statistiques de base
            total_tracks = len(tracks)
            without_album = sum(1 for track in tracks if not track.get('album_id'))
            
            # Métadonnées critiques
            critical_fields = ['bpm', 'key', 'danceability']
            critical_missing = {}
            for field in critical_fields:
                missing = sum(1 for track in tracks if not track.get(field))
                critical_missing[field] = {
                    "missing": missing,
                    "percentage": (missing / total_tracks * 100) if total_tracks > 0 else 0
                }
            
            return {
                "type": "quick_diagnostic",
                "sample_size": total_tracks,
                "tracks_without_album_id": {
                    "count": without_album,
                    "percentage": (without_album / total_tracks * 100) if total_tracks > 0 else 0
                },
                "critical_metadata": critical_missing,
                "quick_recommendations": [
                    f"Album ID: {without_album}/{total_tracks} tracks sans lien album",
                    f"BPM: {critical_missing.get('bpm', {}).get('missing', 0)} tracks sans BPM",
                    f"Key: {critical_missing.get('key', {}).get('missing', 0)} tracks sans tonalité"
                ]
            }
        
        result = asyncio.run(run_quick_diagnostic())
        logger.info(f"[QUICK DIAGNOSTIC] Terminé: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[QUICK DIAGNOSTIC] Erreur: {str(e)}")
        return {"error": str(e), "type": "quick_diagnostic"}


# Configuration des tâches pour Celery Beat
DIAGNOSTIC_SCHEDULE = {
    # Diagnostic complet quotidien
    'metadata-diagnostic-complete': {
        'task': 'metadata.diagnostic_missing_fields',
        'schedule': 86400.0,  # Toutes les 24 heures
        'options': {'queue': 'maintenance'}
    },
    
    # Diagnostic rapide toutes les 4 heures
    'metadata-diagnostic-quick': {
        'task': 'metadata.quick_diagnostic',
        'schedule': 14400.0,  # Toutes les 4 heures
        'options': {'queue': 'maintenance'}
    }
}