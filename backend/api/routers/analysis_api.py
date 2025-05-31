from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.database import get_db
from backend.services.pending_analysis_service import PendingAnalysisService
from backend.services.audio_features_service import analyze_audio_with_librosa
from backend.api.models.tracks_model import Track as TrackModel
from helpers.logging import logger

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
pending_service = PendingAnalysisService()

@router.get("/pending")
async def get_pending_analysis():
    """Récupère la liste des pistes en attente d'analyse."""
    return pending_service.get_pending_tracks()

@router.post("/process")
async def process_pending_analysis(db: SQLAlchemySession = Depends(get_db)):
    """Traite toutes les pistes en attente d'analyse."""
    try:
        pending_tracks = pending_service.get_pending_tracks()
        processed = 0

        for track_data in pending_tracks:
            try:
                # Récupérer la piste en BDD
                track = db.query(TrackModel).get(track_data["track_id"])
                if not track:
                    continue

                # Analyser avec Librosa
                features = await analyze_audio_with_librosa(track_data["file_path"])
                
                # Mettre à jour seulement les features manquantes
                for feature, value in features.items():
                    if feature in track_data["missing_features"]:
                        setattr(track, feature, value)

                db.commit()
                pending_service.mark_as_analyzed(track_data["track_id"])
                processed += 1
                logger.info(f"Track {track_data['track_id']} analysé avec succès")

            except Exception as e:
                logger.error(f"Erreur analyse track {track_data['track_id']}: {str(e)}")
                continue

        return {"message": f"{processed} pistes analysées"}

    except Exception as e:
        logger.error(f"Erreur traitement analyse: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
