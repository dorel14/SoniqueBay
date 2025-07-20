from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession
from utils.pending_analysis_service import PendingAnalysisService
from utils.tinydb_handler import TinyDBHandler
from utils.celery_app import celery
from api.models.tracks_model import Track as TrackModel
from utils.logging import logger
from utils.session import transactional

class AnalysisService:
    def __init__(self):
        self.pending_service = PendingAnalysisService()

    async def get_pending_analysis(self):
        """Récupère la liste des pistes en attente d'analyse."""
        return self.pending_service.get_pending_tracks()

    @transactional
    async def process_pending_analysis(self, session: SQLAlchemySession):
        """Traite toutes les pistes en attente d'analyse."""
        try:
            pending_tracks = self.pending_service.get_pending_tracks()
            tasks_launched = []
            db_tasks = TinyDBHandler.get_db("analysis_tasks")

            for track_data in pending_tracks:
                try:
                    track = session.query(TrackModel).get(track_data["track_id"])
                    if not track:
                        continue

                    task_result = celery.send_task("analyze_audio_with_librosa", args=[track_data["track_id"], track_data["file_path"]])
                    logger.info(f"Tâche Celery lancée pour {track_data['file_path']} (task_id={task_result.id})")

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

    @transactional
    async def process_analysis_results(self, session: SQLAlchemySession):
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
                track = session.query(TrackModel).get(track_id)
                if not track:
                    continue
                missing_features = getattr(track, "missing_features", [])
                for feature, value in features.items():
                    if feature in missing_features:
                        setattr(track, feature, value)
                self.pending_service.mark_as_analyzed(track_id)
                db_tasks.remove(doc_ids=[task.doc_id])
                updated += 1
                logger.info(f"Track {track_id} mis à jour avec succès")
        return {"message": f"{updated} pistes mises à jour"}

    @transactional
    async def update_features(self, session: SQLAlchemySession, data: dict):
        track_id = data["track_id"]
        features = data["features"]
        track = session.query(TrackModel).get(track_id)
        if not track:
            return {"error": "Track not found"}
        for feature, value in features.items():
            setattr(track, feature, value)
        self.pending_service.mark_as_analyzed(track_id)
        return {"message": f"Track {track_id} mis à jour"}