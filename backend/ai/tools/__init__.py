"""Outils pour les agents IA."""

from typing import Any, Dict, List, Optional, Callable


class ToolRegistry:
    """Registre des outils disponibles pour les agents."""
    
    _tools: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, func: Callable, description: str = "") -> Callable:
        """Enregistre un outil."""
        cls._tools[name] = {
            "func": func,
            "description": description or func.__doc__ or ""
        }
        return func
    
    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        """Récupère un outil par nom."""
        tool = cls._tools.get(name)
        return tool["func"] if tool else None
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """Liste tous les outils disponibles."""
        return list(cls._tools.keys())
    
    @classmethod
    def all(cls) -> Dict[str, Dict[str, Any]]:
        """Retourne tous les outils avec leurs descriptions."""
        return cls._tools


async def search_tracks(session, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Recherche des morceaux."""
    return []


async def search_artists(session, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Recherche des artistes."""
    return []


async def search_albums(session, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Recherche des albums."""
    return []


async def create_playlist(session, name: str, track_ids: List[int], description: str = "") -> Dict[str, Any]:
    """Crée une playlist."""
    return {"id": 1, "name": name, "track_count": len(track_ids), "tracks": track_ids, "description": description}


async def play_track(session, track_id: int) -> Dict[str, Any]:
    """Lance la lecture d'un morceau."""
    return {"status": "success", "message": f"Lecture démarrée pour le morceau {track_id}", "track": {"id": track_id}}


async def add_to_playqueue(session, track_id: int) -> Dict[str, Any]:
    """Ajoute un morceau à la file de lecture."""
    return {"status": "success", "message": f"Ajouté à la file de lecture: morceau {track_id}"}


async def get_playqueue(session) -> List[Dict[str, Any]]:
    """Obtient la file de lecture."""
    return []


async def scan_library(session) -> Dict[str, Any]:
    """Démarre un scan de la bibliothèque."""
    return {"status": "started", "message": "Scan de la bibliothèque démarré"}


async def get_recommendations(session, limit: int = 10) -> List[Dict[str, Any]]:
    """Obtient des recommandations."""
    return []


# Enregistrement des outils
ToolRegistry.register("search_tracks", search_tracks, "Recherche de morceaux")
ToolRegistry.register("search_artists", search_artists, "Recherche d'artistes")
ToolRegistry.register("search_albums", search_albums, "Recherche d'albums")
ToolRegistry.register("create_playlist", create_playlist, "Création de playlist")
ToolRegistry.register("play_track", play_track, "Lecture d'un morceau")
ToolRegistry.register("add_to_playqueue", add_to_playqueue, "Ajout à la file de lecture")
ToolRegistry.register("get_playqueue", get_playqueue, "Obtention de la file de lecture")
ToolRegistry.register("scan_library", scan_library, "Scan de la bibliothèque")
ToolRegistry.register("get_recommendations", get_recommendations, "Recommandations musicales")


__all__ = [
    'ToolRegistry',
    'search_tracks',
    'search_artists',
    'search_albums',
    'create_playlist',
    'play_track',
    'add_to_playqueue',
    'get_playqueue',
    'scan_library',
    'get_recommendations',
]
