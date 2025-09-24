from tinydb import Query
from typing import List, Dict
from backend.utils.logging import logger
from backend.utils.tinydb_handler import TinyDBHandler

class PendingAnalysisService:
    def __init__(self):
        self.db = TinyDBHandler.get_db("pending_analysis")
        self.tracks = self.db.table('tracks')

    def add_track(self, track_id: int, file_path: str, missing_features: List[str]):
        """Ajoute une piste à analyser."""
        Track = Query()
        # Éviter les doublons
        if not self.tracks.search(Track.track_id == track_id):
            self.tracks.insert({
                'track_id': track_id,
                'file_path': file_path,
                'missing_features': missing_features,
                'analyzed': False
            })
            logger.info(f"Track {track_id} ajouté pour analyse ultérieure - DB path: {self.db.storage._handle.name}")
            logger.info(f"Total tracks in DB after insert: {len(self.tracks)}")
        else:
            logger.info(f"Track {track_id} déjà présent dans la DB")

    def get_pending_tracks(self) -> List[Dict]:
        """Récupère toutes les pistes en attente d'analyse."""
        Track = Query()
        pending_tracks = self.tracks.search(not Track.analyzed)
        logger.info(f"Récupération des pistes en attente - DB path: {self.db.storage._handle.name}")
        logger.info(f"Total tracks in DB: {len(self.tracks)}, Pending tracks: {len(pending_tracks)}")
        if pending_tracks:
            logger.info(f"Pending track IDs: {[t['track_id'] for t in pending_tracks]}")
        return pending_tracks

    def mark_as_analyzed(self, track_id: int):
        """Marque une piste comme analysée."""
        Track = Query()
        self.tracks.update({'analyzed': True}, Track.track_id == track_id)

    def clear_all(self):
        """Supprime toutes les données (utile pour les tests)."""
        self.tracks.truncate()
        logger.info("Toutes les données d'analyse en attente ont été supprimées")
