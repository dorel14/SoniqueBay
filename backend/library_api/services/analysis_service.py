from backend.library_api.api.models.tracks_model import Track as TrackModel
from backend.library_api.utils.logging import logger
from backend.library_api.utils.tinydb_handler import TinyDBHandler
from backend.library_api.utils.celery_app import celery
from sqlalchemy.orm import Session
from tinydb import Query

class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def get_pending_tracks(self):
        # Récupère la liste des pistes en attente d'analyse
        db_tasks = TinyDBHandler.get_db("pending_analysis")
        tracks_table = db_tasks.table('tracks')
        Track = Query()
        pending = tracks_table.search(not Track.analyzed)
        logger.info(f"get_pending_tracks: DB path {db_tasks.storage._handle.name if hasattr(db_tasks.storage, '_handle') else 'unknown'}, total pending items: {len(pending)}")
        if pending:
            logger.info(f"Pending tracks IDs: {[item.get('track_id') for item in pending]}")
        return pending

    def process_pending_tracks(self):
        # Traite toutes les pistes en attente d'analyse
        db_tasks = TinyDBHandler.get_db("pending_analysis")
        all_tasks = db_tasks.all()
        logger.info(f"process_pending_tracks: DB path {db_tasks.storage._handle.name if hasattr(db_tasks.storage, '_handle') else 'unknown'}, total items before process: {len(all_tasks)}")
        tasks_launched = []
        for track_data in all_tasks:
            logger.info(f"Processing track_data: {track_data}")
            track = self.db.get(TrackModel, track_data["track_id"])
            if not track:
                logger.warning(f"Track {track_data['track_id']} not found in DB")
                continue
            try:
                task_result = celery.send_task("analyze_audio_with_librosa", args=[track_data["track_id"], track_data["file_path"]])
                logger.info(f"Celery task sent for track {track_data['track_id']}, task_id: {task_result.id}")
                TinyDBHandler.get_db("analysis_tasks").insert({
                    "track_id": track_data["track_id"],
                    "task_id": task_result.id,
                    "file_path": track_data["file_path"]
                })
                tasks_launched.append({
                    "track_id": track_data["track_id"],
                    "task_id": task_result.id
                })
            except Exception as e:
                logger.error(f"Error sending Celery task for track {track_data['track_id']}: {e}")
        logger.info(f"process_pending_tracks completed, launched {len(tasks_launched)} tasks")
        task_word = "tâche" if len(tasks_launched) == 1 else "tâches"
        return {"message": f"{len(tasks_launched)} {task_word} Celery lancée{'s' if len(tasks_launched) != 1 else ''}", "tasks": tasks_launched}

    def process_analysis_results(self):
        try:
            db_tasks = TinyDBHandler.get_db("analysis_tasks")
            all_tasks = db_tasks.all()
            logger.info(f"process_analysis_results: DB path {db_tasks.storage._handle.name if hasattr(db_tasks.storage, '_handle') else 'unknown'}, total tasks: {len(all_tasks)}")
            updated = 0
            for task in all_tasks:
                task_id = task["task_id"]
                track_id = task["track_id"]
                logger.info(f"Checking task {task_id} for track {track_id}")
                try:
                    result = celery.AsyncResult(task_id)
                    logger.info(f"AsyncResult for {task_id}: ready={result.ready()}, successful={result.successful()}")
                    if result.ready() and result.successful():
                        features = result.result
                        logger.info(f"Features for track {track_id}: {features}")
                        track = self.db.get(TrackModel, track_id)
                        if not track:
                            logger.warning(f"Track {track_id} not found")
                            continue
                        for feature, value in features.items():
                            setattr(track, feature, value)
                            logger.info(f"Set {feature} = {value} for track {track_id}")
                        self.db.commit()
                        logger.info(f"Committed updates for track {track_id}")
                        pending_db = TinyDBHandler.get_db("pending_analysis")
                        pending_table = pending_db.table('tracks')
                        pending_table.remove(Query().track_id == track_id)
                        db_tasks.remove(Query().task_id == task_id)
                        updated += 1
                        logger.info(f"Removed pending and task entries for {track_id}")
                except Exception as task_e:
                    logger.error(f"Error processing task {task_id}: {task_e}")
            logger.info(f"process_analysis_results completed, updated {updated} tracks")
            if updated == 0:
                return {"message": "Aucune piste mise à jour"}
            else:
                return {"message": f"{updated} piste{'s' if updated != 1 else ''} mise{'s' if updated != 1 else ''} à jour"}
        except Exception as e:
            # Log l'erreur mais retourne toujours 200
            logger.error(f"Erreur process_analysis_results: {e}")
            return {"message": "Aucune piste mise à jour", "error": str(e)}

    def update_features(self, track_id, features):
        track = self.db.get(TrackModel, track_id)
        if not track:
            return {"error": "Track not found"}
        for feature, value in features.items():
            setattr(track, feature, value)
        self.db.commit()
        pending_db = TinyDBHandler.get_db("pending_analysis")
        pending_table = pending_db.table('tracks')
        Track = Query()
        pending_table.remove(Track.track_id == track_id)
        logger.info(f"Updated features for track {track_id} and removed from pending")
        return {"message": f"Track {track_id} mis à jour"}
