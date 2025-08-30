from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.utils.database import get_db
from backend.utils.pending_analysis_service import PendingAnalysisService
from backend.utils.tinydb_handler import TinyDBHandler
from backend.utils.celery_app import celery
from backend.api.models.tracks_model import Track as TrackModel
from backend.utils.logging import logger
from tinydb import Query

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
pending_service = PendingAnalysisService()

@router.get("/pending")
async def get_pending_analysis():
    """Récupère la liste des pistes en attente d'analyse."""
    logger.info("API: Récupération des pistes en attente")
    tracks = pending_service.get_pending_tracks()
    logger.info(f"API: {len(tracks)} pistes en attente trouvées")
    return tracks

@router.post("/process")
async def process_pending_analysis(db: SQLAlchemySession = Depends(get_db)):
    """Traite toutes les pistes en attente d'analyse."""
    try:
        logger.info("API: Traitement des analyses en attente")
        pending_tracks = pending_service.get_pending_tracks()
        logger.info(f"API: {len(pending_tracks)} pistes à traiter")
        tasks_launched = []
        db_tasks = TinyDBHandler.get_db("analysis_tasks")
        logger.info(f"API: DB tasks path: {db_tasks.storage._handle.name}")

        for track_data in pending_tracks:
            try:
                # Récupérer la piste en BDD
                track = db.get(TrackModel, track_data["track_id"])
                if not track:
                    continue

                # Lancer la tâche Celery
                task_result = celery.send_task("analyze_audio_with_librosa", args=[track_data["track_id"], track_data["file_path"]])
                logger.info(f"Tâche Celery lancée pour {track_data['file_path']} (task_id={task_result.id})")

                # Stocker l'id de la tâche et l'id de la track dans TinyDB
                db_tasks.insert({
                    "track_id": track_data["track_id"],
                    "task_id": task_result.id,
                    "file_path": track_data["file_path"]
                })

                tasks_launched.append({
                    "track_id": track_data["track_id"],
                    "task_id": task_result.id
                })

            except Exception as e:
                logger.error(f"Erreur analyse track {track_data['track_id']}: {str(e)}")
                continue

        return {
            "message": f"{len(tasks_launched)} tâches Celery lancées",
            "tasks": tasks_launched
        }

    except Exception as e:
        logger.error(f"Erreur traitement analyse: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_results")
async def process_analysis_results(db: SQLAlchemySession = Depends(get_db)):
    """
    Récupère les résultats des tâches Celery terminées et met à jour les features en BDD.
    """
    db_tasks = TinyDBHandler.get_db("analysis_tasks")
    updated = 0
    for task in db_tasks.all():
        task_id = task["task_id"]
        track_id = task["track_id"]
        result = celery.AsyncResult(task_id)
        if result.ready() and result.successful():
            features = result.result
            # Récupérer la track
            track = db.get(TrackModel, track_id)
            if not track:
                continue
            # Mettre à jour seulement les features manquantes
            # Récupérer les missing_features depuis le service d'analyse en attente
            pending_tracks = pending_service.get_pending_tracks()
            missing_features = []
            for pending_track in pending_tracks:
                if pending_track["track_id"] == track_id:
                    missing_features = pending_track["missing_features"]
                    break

            for feature, value in features.items():
                if feature in missing_features:
                    setattr(track, feature, value)
            db.commit()
            pending_service.mark_as_analyzed(track_id)
            # Supprimer la tâche de TinyDB
            TaskQuery = Query()
            db_tasks.remove(TaskQuery.task_id == task_id)
            updated += 1
            logger.info(f"Track {track_id} mis à jour avec succès")
    return {"message": f"{updated} pistes mises à jour"}

@router.post("/update_features")
async def update_features(data: dict, db: SQLAlchemySession = Depends(get_db)):
    track_id = data["track_id"]
    features = data["features"]
    track = db.get(TrackModel, track_id)
    if not track:
        return {"error": "Track not found"}
    for feature, value in features.items():
        setattr(track, feature, value)
    db.commit()
    pending_service.mark_as_analyzed(track_id)
    return {"message": f"Track {track_id} mis à jour"}