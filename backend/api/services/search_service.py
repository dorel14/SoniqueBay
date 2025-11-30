"""
Service de recherche PostgreSQL pour l'API SoniqueBay
Utilise PostgreSQL full-text search avec TSVECTOR et recherche vectorielle hybride.
Auteur : Kilo Code
Dépendances : backend.api.schemas.search_schema
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text, func, desc, or_, and_
from sqlalchemy.orm import Session
from backend.api.schemas.search_schema import SearchQuery, SearchResult
from backend.api.services.redis_cache_service import redis_cache_service
from backend.api.utils.logging import logger

class SearchService:
    """Service de recherche hybride PostgreSQL + pgvector."""

    @staticmethod
    def search(query: SearchQuery, db: Optional[Session] = None) -> SearchResult:
        """
        Recherche hybride combinant recherche textuelle et vectorielle avec cache Redis.

        Args:
            query: Paramètres de recherche
            db: Session de base de données

        Returns:
            Résultats de recherche avec scoring hybride
        """
        if not db:
            from backend.api.utils.database import get_db
            db = next(get_db())

        if not query.query or not query.query.strip():
            return SearchResult(
                total=0,
                items=[],
                facets={"artists": [], "genres": [], "decades": []},
                page=query.page,
                total_pages=0
            )

        # Vérifier le cache Redis pour les résultats de recherche
        cached_result = redis_cache_service.get_cached_search_result(
            query.query, query.page, query.page_size, query.filters
        )

        if cached_result:
            logger.debug(f"[SEARCH CACHE] Hit pour requête: '{query.query}' page {query.page}")
            # Vérifier si les facettes sont en cache
            cached_facets = redis_cache_service.get_cached_facets()
            if cached_facets:
                cached_result["facets"] = cached_facets
            return SearchResult(**cached_result)

        logger.debug(f"[SEARCH CACHE] Miss pour requête: '{query.query}' page {query.page}")

        # Recherche textuelle avec TSVECTOR
        text_results = SearchService._text_search(query, db)

        # Recherche vectorielle si disponible
        vector_results = SearchService._vector_search(query, db)

        # Fusionner et scorer hybride
        combined_results = SearchService._combine_results(text_results, vector_results, query)

        # Pagination
        offset = (query.page - 1) * query.page_size
        paginated_items = combined_results[offset:offset + query.page_size]

        # Facettes
        facets = SearchService._get_facets(query, db)

        total = len(combined_results)
        total_pages = (total // query.page_size) + (1 if total % query.page_size else 0)

        result = SearchResult(
            total=total,
            items=paginated_items,
            facets=facets,
            page=query.page,
            total_pages=total_pages
        )

        # Mettre en cache le résultat (sauf si c'est une requête vide ou trop spécifique)
        if len(query.query.strip()) > 2:  # Éviter de cacher les requêtes trop courtes
            result_dict = result.model_dump()
            redis_cache_service.cache_search_result(
                query.query, query.page, query.page_size, query.filters, result_dict
            )

        return result

    @staticmethod
    def _text_search(query: SearchQuery, db: Session) -> List[Dict[str, Any]]:
        """Recherche textuelle avec PostgreSQL TSVECTOR."""
        try:
            # Préparer la requête de recherche
            search_terms = func.plainto_tsquery('english', query.query)

            # Recherche dans tracks
            track_query = text("""
                SELECT
                    t.id,
                    t.title,
                    a.name as artist,
                    al.title as album,
                    t.genre,
                    t.path,
                    ts_rank_cd(t.search, :search_terms) as text_score,
                    0.0 as vector_score
                FROM tracks t
                LEFT JOIN artists a ON t.track_artist_id = a.id
                LEFT JOIN albums al ON t.album_id = al.id
                WHERE t.search @@ :search_terms
                ORDER BY text_score DESC
                LIMIT 100
            """)

            track_results = db.execute(track_query, {"search_terms": search_terms}).fetchall()

            # Recherche dans artists
            artist_query = text("""
                SELECT
                    NULL as id,
                    a.name as title,
                    a.name as artist,
                    NULL as album,
                    NULL as genre,
                    NULL as path,
                    ts_rank_cd(a.search, :search_terms) as text_score,
                    0.0 as vector_score
                FROM artists a
                WHERE a.search @@ :search_terms
                ORDER BY text_score DESC
                LIMIT 50
            """)

            artist_results = db.execute(artist_query, {"search_terms": search_terms}).fetchall()

            # Combiner et formater
            results = []
            for row in track_results:
                results.append({
                    "id": row.id,
                    "title": row.title or "",
                    "artist": row.artist or "",
                    "album": row.album or "",
                    "genre": row.genre or "",
                    "path": row.path or "",
                    "text_score": float(row.text_score),
                    "vector_score": float(row.vector_score),
                    "type": "track"
                })

            for row in artist_results:
                results.append({
                    "id": None,
                    "title": row.title or "",
                    "artist": row.artist or "",
                    "album": "",
                    "genre": "",
                    "path": "",
                    "text_score": float(row.text_score),
                    "vector_score": float(row.vector_score),
                    "type": "artist"
                })

            return results

        except Exception as e:
            logger.error(f"Erreur recherche textuelle: {e}")
            return []

    @staticmethod
    def _vector_search(query: SearchQuery, db: Session) -> List[Dict[str, Any]]:
        """Recherche vectorielle avec pgvector."""
        try:
            # Pour la recherche vectorielle, on utilise un embedding moyen des termes
            # En production, utiliser un modèle d'embedding réel
            from backend.api.services.vector_search_service import VectorSearchService
            vector_service = VectorSearchService(db)

            # Recherche de tracks similaires (placeholder - besoin d'embedding de la requête)
            # Pour l'instant, retourner vide si pas d'embedding disponible
            return []

        except Exception as e:
            logger.error(f"Erreur recherche vectorielle: {e}")
            return []

    @staticmethod
    def _combine_results(text_results: List[Dict], vector_results: List[Dict], query: SearchQuery) -> List[Dict]:
        """Combiner résultats textuels et vectoriels avec scoring hybride."""
        # Pondération: 70% texte, 30% vecteur
        TEXT_WEIGHT = 0.7
        VECTOR_WEIGHT = 0.3

        combined = {}

        # Ajouter résultats textuels
        for result in text_results:
            key = f"{result['type']}_{result['id'] or result['title']}"
            result['hybrid_score'] = result['text_score'] * TEXT_WEIGHT
            combined[key] = result

        # Ajouter résultats vectoriels
        for result in vector_results:
            key = f"{result['type']}_{result['id'] or result['title']}"
            if key in combined:
                combined[key]['vector_score'] = result.get('vector_score', 0)
                combined[key]['hybrid_score'] += result['vector_score'] * VECTOR_WEIGHT
            else:
                result['hybrid_score'] = result.get('vector_score', 0) * VECTOR_WEIGHT
                combined[key] = result

        # Trier par score hybride
        sorted_results = sorted(combined.values(), key=lambda x: x['hybrid_score'], reverse=True)

        # Nettoyer les scores pour la réponse
        for result in sorted_results:
            result.pop('text_score', None)
            result.pop('vector_score', None)

        return sorted_results

    @staticmethod
    def _get_facets(query: SearchQuery, db: Session) -> Dict[str, List]:
        """Générer les facettes pour les résultats en utilisant les vues matérialisées et cache Redis."""
        # Vérifier le cache Redis d'abord
        cached_facets = redis_cache_service.get_cached_facets()
        if cached_facets:
            logger.debug("[FACETS CACHE] Hit")
            return cached_facets

        logger.debug("[FACETS CACHE] Miss")

        try:
            # Facette genres depuis vue matérialisée
            genre_query = text("""
                SELECT genre, count
                FROM mv_genre_facets
                WHERE rank <= 20
                ORDER BY rank
            """)
            genres = [{"name": row[0], "count": row[1]} for row in db.execute(genre_query).fetchall()]

            # Facette artistes depuis vue matérialisée
            artist_query = text("""
                SELECT artist_name, track_count
                FROM mv_artist_facets
                WHERE rank <= 20
                ORDER BY rank
            """)
            artists = [{"name": row[0], "count": row[1]} for row in db.execute(artist_query).fetchall()]

            # Facette décennies depuis vue matérialisée
            decade_query = text("""
                SELECT decade, count
                FROM mv_decade_facets
                WHERE rank <= 10
                ORDER BY rank
            """)
            decades = [{"name": f"{row[0]}s", "count": row[1]} for row in db.execute(decade_query).fetchall() if row[0]]

            facets = {
                "genres": genres,
                "artists": artists,
                "decades": decades
            }

            # Mettre en cache les facettes
            redis_cache_service.cache_facets(facets)

            return facets

        except Exception as e:
            logger.error(f"Erreur génération facettes depuis vues matérialisées: {e}")
            # Fallback vers requêtes classiques si vues matérialisées indisponibles
            facets = SearchService._get_facets_fallback(query, db)
            # Essayer de mettre en cache même le fallback
            redis_cache_service.cache_facets(facets)
            return facets

    @staticmethod
    def _get_facets_fallback(query: SearchQuery, db: Session) -> Dict[str, List]:
        """Fallback pour les facettes si vues matérialisées indisponibles."""
        try:
            # Facette genres
            genre_query = text("""
                SELECT genre, COUNT(*) as count
                FROM tracks
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 20
            """)
            genres = [{"name": row[0], "count": row[1]} for row in db.execute(genre_query).fetchall()]

            # Facette artistes
            artist_query = text("""
                SELECT a.name, COUNT(t.id) as count
                FROM artists a
                JOIN tracks t ON a.id = t.track_artist_id
                GROUP BY a.id, a.name
                ORDER BY count DESC
                LIMIT 20
            """)
            artists = [{"name": row[0], "count": row[1]} for row in db.execute(artist_query).fetchall()]

            # Facette décennies
            decade_query = text("""
                SELECT
                    CASE
                        WHEN year ~ '^\\d{4}$' THEN (CAST(year AS INTEGER) / 10) * 10
                        ELSE NULL
                    END as decade,
                    COUNT(*) as count
                FROM tracks
                WHERE year IS NOT NULL AND year ~ '^\\d{4}$'
                GROUP BY decade
                ORDER BY decade DESC
                LIMIT 10
            """)
            decades = [{"name": f"{row[0]}s", "count": row[1]} for row in db.execute(decade_query).fetchall() if row[0]]

            return {
                "genres": genres,
                "artists": artists,
                "decades": decades
            }

        except Exception as e:
            logger.error(f"Erreur génération facettes fallback: {e}")
            return {"artists": [], "genres": [], "decades": []}

    @staticmethod
    def typeahead_search(q: str, limit: int = 10, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Recherche typeahead pour suggestions en temps réel."""
        if not db:
            from backend.api.utils.database import get_db
            db = next(get_db())

        if not q or not q.strip():
            return []

        try:
            search_terms = func.plainto_tsquery('english', q)

            # Recherche dans tracks
            query = text("""
                SELECT
                    t.id,
                    t.title,
                    a.name as artist,
                    al.title as album,
                    ts_rank_cd(t.search, :search_terms) as rank
                FROM tracks t
                LEFT JOIN artists a ON t.track_artist_id = a.id
                LEFT JOIN albums al ON t.album_id = al.id
                WHERE t.search @@ :search_terms
                ORDER BY rank DESC
                LIMIT :limit
            """)

            results = db.execute(query, {"search_terms": search_terms, "limit": limit}).fetchall()

            return [{
                "id": row.id,
                "title": row.title or "",
                "artist": row.artist or "",
                "album": row.album or "",
                "type": "track"
            } for row in results]

        except Exception as e:
            logger.error(f"Erreur recherche typeahead: {e}")
            return []
