"""
Exemple d'outil migré utilisant le nouveau système de décorateurs
Montre la transformation d'un outil existant vers le système optimisé
"""

from typing import Dict, Any, Optional
from backend.ai.utils.decorators import ai_tool, validate_tool_config
from backend.api.utils.logging import logger


# ============================================================================
# EXEMPLE 1: Outil de recherche musicale - Version décorée
# ============================================================================

@ai_tool(
    name="search_tracks",
    description="Recherche des pistes musicales selon divers critères",
    allowed_agents=["search_agent", "playlist_agent"],
    timeout=15,
    version="2.0",
    priority="normal",
    cache_strategy="redis"
)
async def search_tracks(
    query: str,
    genre: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    limit: int = 25,
    session = None
) -> Dict[str, Any]:
    """
    Recherche des pistes musicales avec filtres avancés
    
    Args:
        query: Terme de recherche principal
        genre: Genre musical à filtrer (optionnel)
        year_min: Année minimum (optionnel)
        year_max: Année maximum (optionnel)
        limit: Nombre maximum de résultats (défaut: 25)
        session: Session de base de données injectée automatiquement
        
    Returns:
        Dict contenant les résultats de recherche avec métadonnées
    """
    try:
        logger.info(f"Recherche de pistes: '{query}' (limite: {limit})")
        
        # Simulation de recherche (remplacer par vraie logique)
        results = {
            "query": query,
            "total_found": 42,
            "results": [
                {
                    "id": "track_1",
                    "title": "Example Track 1",
                    "artist": "Example Artist",
                    "album": "Example Album",
                    "year": 2020,
                    "genre": genre or "Unknown",
                    "score": 0.95
                }
            ],
            "filters_applied": {
                "genre": genre,
                "year_range": f"{year_min}-{year_max}" if year_min and year_max else None
            },
            "search_metadata": {
                "execution_time": "0.123s",
                "cache_hit": False,
                "agents_used": ["search_agent"]
            }
        }
        
        logger.info(f"Recherche terminée: {results['total_found']} pistes trouvées")
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        raise


# ============================================================================
# EXEMPLE 2: Outil de génération de playlist - Version décorée
# ============================================================================

@ai_tool(
    name="generate_playlist",
    description="Génère une playlist personnalisée basée sur des critères",
    allowed_agents=["playlist_agent"],
    timeout=30,
    version="2.0",
    priority="high",
    cache_strategy="none"
)
async def generate_playlist(
    mood: str,
    genre: str,
    duration_minutes: int = 60,
    energy_level: str = "medium",
    exclude_recent: bool = True,
    max_tracks: int = 20,
    session = None
) -> Dict[str, Any]:
    """
    Génère une playlist selon les préférences utilisateur
    
    Args:
        mood: Ambiance souhaitée (énergique, calme, motivé, etc.)
        genre: Genre musical principal
        duration_minutes: Durée totale en minutes (défaut: 60)
        energy_level: Niveau d'énergie (low, medium, high)
        exclude_recent: Éviter les morceaux récemment joués
        max_tracks: Nombre maximum de pistes
        session: Session DB injectée automatiquement
        
    Returns:
        Dict contenant la playlist générée avec métadonnées
    """
    try:
        logger.info(f"Génération de playlist: {mood} / {genre} ({duration_minutes}min)")
        
        # Simulation de génération (remplacer par vraie logique)
        playlist = {
            "playlist_id": "generated_123",
            "name": f"Playlist {mood} - {genre}",
            "description": f"Playlist générée automatiquement pour une ambiance {mood}",
            "total_duration": duration_minutes * 60,  # en secondes
            "track_count": min(max_tracks, 15),  # Simulation
            "criteria": {
                "mood": mood,
                "genre": genre,
                "energy_level": energy_level,
                "exclude_recent": exclude_recent
            },
            "tracks": [
                {
                    "id": "track_1",
                    "title": "Energetic Track",
                    "artist": "Test Artist",
                    "duration": 240,
                    "position": 1,
                    "selection_reason": "Correspond à l'ambiance énergique"
                }
            ],
            "generation_metadata": {
                "algorithm_version": "2.0",
                "confidence_score": 0.87,
                "generation_time": "0.456s",
                "cache_applied": False
            }
        }
        
        logger.info(f"Playlist générée: {playlist['track_count']} pistes")
        return playlist
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de playlist: {e}")
        raise


# ============================================================================
# EXEMPLE 3: Outil d'action système - Version décorée
# ============================================================================

@ai_tool(
    name="scan_library",
    description="Lance un scan de la bibliothèque musicale",
    allowed_agents=["action_agent"],
    timeout=300,  # 5 minutes pour les gros scans
    version="2.0",
    priority="low",
    cache_strategy="none"
)
async def scan_library(
    force_rescan: bool = False,
    update_metadata: bool = True,
    parallel_processes: int = 4,
    session = None
) -> Dict[str, Any]:
    """
    Lance un scan complet de la bibliothèque musicale
    
    Args:
        force_rescan: Forcer le re-scan même pour les fichiers inchangés
        update_metadata: Mettre à jour les métadonnées manquantes
        parallel_processes: Nombre de processus parallèles (max: 8)
        session: Session DB injectée automatiquement
        
    Returns:
        Dict avec les résultats du scan et statistiques
    """
    try:
        logger.info(f"Lancement du scan de bibliothèque (force: {force_rescan})")
        
        # Simulation de scan (remplacer par vraie logique)
        scan_result = {
            "scan_id": "scan_456",
            "status": "completed",
            "start_time": "2025-01-15T10:00:00Z",
            "end_time": "2025-01-15T10:05:30Z",
            "duration_seconds": 330,
            "statistics": {
                "directories_scanned": 150,
                "files_found": 1247,
                "new_files": 23,
                "updated_files": 45,
                "errors": 2,
                "skipped_files": 8
            },
            "actions_taken": {
                "metadata_extracted": True,
                "covers_downloaded": True,
                "vectors_generated": True,
                "indexes_updated": True
            },
            "performance": {
                "files_per_second": 3.78,
                "average_file_processing": "0.26s",
                "memory_peak": "512MB",
                "cpu_usage": "45%"
            }
        }
        
        logger.info(f"Scan terminé: {scan_result['statistics']['files_found']} fichiers traités")
        return scan_result
        
    except Exception as e:
        logger.error(f"Erreur lors du scan: {e}")
        raise


# ============================================================================
# EXEMPLE 4: Outil de smalltalk avec analyse de mood
# ============================================================================

@ai_tool(
    name="analyze_mood",
    description="Analyse l'humeur de l'utilisateur à partir de son message",
    allowed_agents=["smalltalk_agent"],
    timeout=5,
    version="2.0",
    priority="normal",
    cache_strategy="memory"
)
async def analyze_mood(
    message: str,
    conversation_context: Optional[Dict[str, Any]] = None,
    session = None
) -> Dict[str, Any]:
    """
    Analyse l'humeur de l'utilisateur dans son message
    
    Args:
        message: Message de l'utilisateur à analyser
        conversation_context: Contexte de la conversation (optionnel)
        session: Session DB injectée automatiquement
        
    Returns:
        Dict avec l'humeur détectée et score de confiance
    """
    try:
        logger.info(f"Analyse d'humeur pour message: '{message[:50]}...'")
        
        # Simulation d'analyse (remplacer par vraie logique ML)
        mood_analysis = {
            "detected_mood": "joyeux",
            "confidence_score": 0.85,
            "mood_details": {
                "primary_emotion": "joie",
                "secondary_emotion": "enthousiasme",
                "intensity": "medium",
                "valence": 0.7,  # -1 à 1 (négatif à positif)
                "arousal": 0.6   # 0 à 1 (calme à excité)
            },
            "linguistic_features": {
                "positive_words": 3,
                "exclamation_marks": 2,
                "capital_letters": 1,
                "smileys": 1
            },
            "context_considered": conversation_context is not None,
            "analysis_metadata": {
                "model_version": "mood_analyzer_v2.1",
                "processing_time": "0.045s",
                "cache_hit": True
            }
        }
        
        logger.info(f"Humeur détectée: {mood_analysis['detected_mood']} (confiance: {mood_analysis['confidence_score']})")
        return mood_analysis
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse d'humeur: {e}")
        raise


# ============================================================================
# EXEMPLE 5: Tool validator pour validation de configuration
# ============================================================================

# Exemple de validation personnalisée pour les outils critiques
def validate_search_params(query: str, limit: int) -> bool:
    """Validation personnalisée pour l'outil de recherche"""
    if not query or len(query.strip()) < 2:
        raise ValueError("Le terme de recherche doit contenir au moins 2 caractères")
    if limit < 1 or limit > 100:
        raise ValueError("La limite doit être entre 1 et 100")
    return True

# Application de la validation à l'outil search_tracks
search_tracks = validate_tool_config(validate_search_params)(search_tracks)


# ============================================================================
# EXPORT ET AUTO-ENREGISTREMENT
# ============================================================================

# Ces outils seront automatiquement enregistrés lors de l'import
# grâce au mécanisme __init__.py dans le package tools/

__all__ = [
    "search_tracks",
    "generate_playlist", 
    "scan_library",
    "analyze_mood"
]