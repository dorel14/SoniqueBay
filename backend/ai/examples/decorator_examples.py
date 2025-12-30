"""
Exemples d'utilisation du décorateur @ai_tool optimisé
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ai.utils.decorators import ai_tool, search_tool, playlist_tool, music_tool


# Exemple 1: Tool de recherche simple
@search_tool(
    name="search_tracks",
    description="Recherche des pistes musicales par titre, artiste ou album",
    allowed_agents=["search_agent", "playlist_agent"],
    timeout=30
)
async def search_tracks(
    query: str,
    artist: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = 25,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """
    Recherche des pistes musicales dans la base de données.
    
    Args:
        query: Terme de recherche
        artist: Filtrer par artiste (optionnel)
        genre: Filtrer par genre (optionnel)
        limit: Nombre maximum de résultats
        session: Session de base de données
    """
    # Implementation de la recherche
    results = await session.execute(
        "SELECT * FROM tracks WHERE title ILIKE :query LIMIT :limit",
        {"query": f"%{query}%", "limit": limit}
    )
    
    return {
        "tracks": [dict(row) for row in results.fetchall()],
        "count": len(results.fetchall())
    }


# Exemple 2: Tool de playlist
@playlist_tool(
    name="generate_playlist",
    description="Génère une playlist basée sur des critères musicaux",
    allowed_agents=["playlist_agent"],
    timeout=60
)
async def generate_playlist(
    mood: Optional[str] = None,
    genre: Optional[str] = None,
    energy: str = "medium",
    bpm_min: Optional[int] = None,
    bpm_max: Optional[int] = None,
    duration_minutes: int = 60,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """
    Génère une playlist personnalisée selon les critères.
    
    Args:
        mood: Ambiance recherchée
        genre: Genre musical
        energy: Niveau d'énergie (low, medium, high)
        bpm_min: BPM minimum
        bpm_max: BPM maximum
        duration_minutes: Durée souhaitée en minutes
        session: Session de base de données
    """
    # Construction de la requête selon les critères
    where_clauses = []
    params = {}
    
    if genre:
        where_clauses.append("genre = :genre")
        params["genre"] = genre
    
    if mood:
        where_clauses.append("mood = :mood")
        params["mood"] = mood
    
    if bpm_min:
        where_clauses.append("bpm >= :bpm_min")
        params["bpm_min"] = bpm_min
    
    if bpm_max:
        where_clauses.append("bpm <= :bpm_max")
        params["bpm_max"] = bpm_max
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Exécution de la requête
    query = f"""
        SELECT * FROM tracks 
        WHERE {where_clause}
        ORDER BY RANDOM()
        LIMIT 20
    """
    
    results = await session.execute(query, params)
    tracks = [dict(row) for row in results.fetchall()]
    
    return {
        "playlist": tracks,
        "criteria": {
            "mood": mood,
            "genre": genre,
            "energy": energy,
            "bpm_range": [bpm_min, bpm_max]
        },
        "total_duration": sum(track.get('duration', 0) for track in tracks)
    }


# Exemple 3: Tool musical général
@music_tool(
    name="get_artist_info",
    description="Récupère les informations détaillées d'un artiste",
    allowed_agents=["search_agent", "playlist_agent"],
    timeout=15
)
async def get_artist_info(
    artist_name: str,
    include_similar: bool = True,
    include_stats: bool = True,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """
    Récupère les informations détaillées d'un artiste.
    
    Args:
        artist_name: Nom de l'artiste
        include_similar: Inclure les artistes similaires
        include_stats: Inclure les statistiques d'écoute
        session: Session de base de données
    """
    # Récupération des informations de base
    artist_result = await session.execute(
        "SELECT * FROM artists WHERE name ILIKE :name",
        {"name": f"%{artist_name}%"}
    )
    
    artist = dict(artist_result.fetchone())
    if not artist:
        return {"error": f"Artiste '{artist_name}' non trouvé"}
    
    # Albums de l'artiste
    albums_result = await session.execute(
        "SELECT * FROM albums WHERE artist_id = :artist_id",
        {"artist_id": artist['id']}
    )
    albums = [dict(row) for row in albums_result.fetchall()]
    
    # Pistes de l'artiste
    tracks_result = await session.execute(
        "SELECT * FROM tracks WHERE artist_id = :artist_id",
        {"artist_id": artist['id']}
    )
    tracks = [dict(row) for row in tracks_result.fetchall()]
    
    result = {
        "artist": artist,
        "albums_count": len(albums),
        "tracks_count": len(tracks),
        "total_duration": sum(track.get('duration', 0) for track in tracks)
    }
    
    # Artistes similaires
    if include_similar:
        similar_result = await session.execute(
            """
            SELECT similar_artist_id, similarity_score 
            FROM artist_similar 
            WHERE artist_id = :artist_id 
            ORDER BY similarity_score DESC 
            LIMIT 10
            """,
            {"artist_id": artist['id']}
        )
        result["similar_artists"] = [dict(row) for row in similar_result.fetchall()]
    
    # Statistiques d'écoute
    if include_stats:
        stats_result = await session.execute(
            """
            SELECT COUNT(*) as play_count, SUM(duration) as total_play_duration
            FROM play_history 
            WHERE artist_id = :artist_id
            """,
            {"artist_id": artist['id']}
        )
        stats = dict(stats_result.fetchone())
        result["statistics"] = stats
    
    return result


# Exemple 4: Tool d'action système
@ai_tool(
    name="scan_library",
    description="Lance le scan de la bibliothèque musicale",
    allowed_agents=["action_agent"],
    requires_session=True,
    timeout=300,
    category="system",
    tags=["scan", "library", "maintenance"]
)
async def scan_library(
    scan_path: str,
    recursive: bool = True,
    force_rescan: bool = False,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """
    Lance le scan de la bibliothèque musicale.
    
    Args:
        scan_path: Chemin à scanner
        recursive: Scanner récursivement
        force_rescan: Forcer le rescan même si les fichiers sont déjà en base
        session: Session de base de données
    """
    # Validation des paramètres
    if not scan_path or not scan_path.strip():
        raise ValueError("Le chemin de scan ne peut pas être vide")
    
    # Log du début du scan
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Début du scan de la bibliothèque: {scan_path}")
    
    # Création d'une session de scan
    scan_session_result = await session.execute(
        """
        INSERT INTO scan_sessions (path, recursive, status, started_at)
        VALUES (:path, :recursive, 'running', NOW())
        RETURNING id
        """,
        {
            "path": scan_path,
            "recursive": recursive,
        }
    )
    scan_session_id = scan_session_result.fetchone()['id']
    
    # Simulation du processus de scan (dans la réalité, ceci serait fait par un worker)
    import time
    await time.sleep(2)  # Simulation
    
    # Mise à jour du statut de la session
    await session.execute(
        """
        UPDATE scan_sessions 
        SET status = 'completed', completed_at = NOW()
        WHERE id = :id
        """,
        {"id": scan_session_id}
    )
    
    await session.commit()
    
    logger.info(f"Scan terminé pour: {scan_path}")
    
    return {
        "scan_session_id": scan_session_id,
        "status": "completed",
        "path": scan_path,
        "recursive": recursive,
        "message": "Scan de la bibliothèque terminé avec succès"
    }


# Exemple 5: Tool avec validation avancée
@ai_tool(
    name="recommend_similar_tracks",
    description="Recommande des pistes similaires basée sur des embeddings vectoriels",
    allowed_agents=["search_agent", "playlist_agent"],
    timeout=45,
    category="recommendation",
    tags=["recommendation", "ai", "vector"]
)
async def recommend_similar_tracks(
    track_id: int,
    limit: int = 10,
    similarity_threshold: float = 0.7,
    exclude_recent: bool = True,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """
    Recommande des pistes similaires basée sur les embeddings vectoriels.
    
    Args:
        track_id: ID de la piste de référence
        limit: Nombre maximum de recommandations
        similarity_threshold: Seuil de similarité (0-1)
        exclude_recent: Exclure les pistes récemment écoutées
        session: Session de base de données
    """
    # Validation des paramètres
    if track_id <= 0:
        raise ValueError("L'ID de la piste doit être positif")
    
    if not (0 <= similarity_threshold <= 1):
        raise ValueError("Le seuil de similarité doit être entre 0 et 1")
    
    # Récupération de la piste de référence
    track_result = await session.execute(
        "SELECT * FROM tracks WHERE id = :id",
        {"id": track_id}
    )
    
    reference_track = dict(track_result.fetchone())
    if not reference_track:
        return {"error": f"Piste avec ID {track_id} non trouvée"}
    
    # Récupération de l'embedding de la piste de référence
    embedding_result = await session.execute(
        """
        SELECT embedding FROM track_vectors 
        WHERE track_id = :track_id
        """,
        {"track_id": track_id}
    )
    
    reference_embedding = embedding_result.fetchone()
    if not reference_embedding:
        return {"error": f"Aucun embedding disponible pour la piste {track_id}"}
    
    # Recherche des pistes similaires avec similarité cosinus
    similar_query = """
        SELECT 
            t.*,
            tv.embedding,
            (tv.embedding <=> :reference_embedding) as similarity_score
        FROM tracks t
        JOIN track_vectors tv ON t.id = tv.track_id
        WHERE t.id != :track_id
        AND (tv.embedding <=> :reference_embedding) < :threshold
        ORDER BY similarity_score ASC
        LIMIT :limit
    """
    
    similar_result = await session.execute(
        similar_query,
        {
            "reference_embedding": reference_embedding['embedding'],
            "track_id": track_id,
            "threshold": 1 - similarity_threshold,  # Distance = 1 - similarité
            "limit": limit
        }
    )
    
    similar_tracks = []
    for row in similar_result.fetchall():
        track_dict = dict(row)
        # Conversion du score de distance en score de similarité
        track_dict['similarity_score'] = 1 - track_dict['similarity_score']
        similar_tracks.append(track_dict)
    
    # Filtrage des pistes récemment écoutées si demandé
    if exclude_recent:
        recent_result = await session.execute(
            """
            SELECT track_id FROM play_history 
            WHERE played_at > NOW() - INTERVAL '7 days'
            AND track_id IN :track_ids
            """,
            {"track_ids": tuple(t['id'] for t in similar_tracks)}
        )
        
        recent_track_ids = {row['track_id'] for row in recent_result.fetchall()}
        similar_tracks = [t for t in similar_tracks if t['id'] not in recent_track_ids]
    
    return {
        "reference_track": {
            "id": reference_track['id'],
            "title": reference_track['title'],
            "artist": reference_track['artist']
        },
        "recommendations": similar_tracks,
        "total_recommendations": len(similar_tracks),
        "parameters": {
            "similarity_threshold": similarity_threshold,
            "exclude_recent": exclude_recent
        }
    }