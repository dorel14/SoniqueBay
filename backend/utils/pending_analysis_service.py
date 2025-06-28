from tinydb import TinyDB, Query
from pathlib import Path
from typing import List, Dict
from helpers.logging import logger

class PendingAnalysisService:
    def __init__(self):
        data_dir = Path("./backend/data")
        data_dir.mkdir(exist_ok=True)
        self.db = TinyDB(data_dir / "pending_analysis.json")
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
            logger.info(f"Track {track_id} ajouté pour analyse ultérieure")

    def get_pending_tracks(self) -> List[Dict]:
        """Récupère toutes les pistes en attente d'analyse."""
        Track = Query()
        return self.tracks.search(Track.analyzed == False)

    def mark_as_analyzed(self, track_id: int):
        """Marque une piste comme analysée."""
        Track = Query()
        self.tracks.update({'analyzed': True}, Track.track_id == track_id)
