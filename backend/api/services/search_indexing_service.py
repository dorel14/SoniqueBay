# -*- coding: UTF-8 -*-
"""
Service d'indexation PostgreSQL pour la recherche full-text
Gère le remplissage automatique des colonnes TSVECTOR pour tracks et artists.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from backend.api.utils.logging import logger
from backend.api.utils.database import get_db


class SearchIndexingService:
    """Service pour maintenir les index de recherche PostgreSQL."""

    @staticmethod
    def update_track_search_vectors(db: Optional[Session] = None, track_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Met à jour les vecteurs de recherche TSVECTOR pour les tracks.

        Args:
            db: Session de base de données
            track_ids: IDs spécifiques des tracks, ou None pour tous

        Returns:
            Statistiques de mise à jour
        """
        if not db:
            db = next(get_db())

        try:
            logger.info("[SEARCH INDEXING] Démarrage mise à jour TSVECTOR tracks")

            # Requête pour mettre à jour les TSVECTOR
            if track_ids:
                # Tracks spécifiques
                query = text("""
                    UPDATE tracks
                    SET search = to_tsvector('english',
                        COALESCE(title, '') || ' ' ||
                        COALESCE(genre, '') || ' ' ||
                        COALESCE(year, '') || ' ' ||
                        COALESCE(artists.name, '') || ' ' ||
                        COALESCE(albums.title, '')
                    )
                    FROM artists, albums
                    WHERE tracks.track_artist_id = artists.id
                      AND tracks.album_id = albums.id
                      AND tracks.id = ANY(:track_ids)
                      AND (tracks.title IS NOT NULL OR artists.name IS NOT NULL)
                """)
                result = db.execute(query, {"track_ids": track_ids})
                updated_count = result.rowcount
            else:
                # Tous les tracks
                query = text("""
                    UPDATE tracks
                    SET search = to_tsvector('english',
                        COALESCE(title, '') || ' ' ||
                        COALESCE(genre, '') || ' ' ||
                        COALESCE(year, '') || ' ' ||
                        COALESCE(artists.name, '') || ' ' ||
                        COALESCE(albums.title, '')
                    )
                    FROM artists, albums
                    WHERE tracks.track_artist_id = artists.id
                      AND tracks.album_id = albums.id
                      AND (tracks.title IS NOT NULL OR artists.name IS NOT NULL)
                """)
                result = db.execute(query)
                updated_count = result.rowcount

            db.commit()
            logger.info(f"[SEARCH INDEXING] Mis à jour {updated_count} tracks TSVECTOR")

            return {
                "success": True,
                "tracks_updated": updated_count,
                "type": "tracks"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"[SEARCH INDEXING] Erreur mise à jour tracks: {e}")
            return {
                "success": False,
                "error": str(e),
                "tracks_updated": 0,
                "type": "tracks"
            }

    @staticmethod
    def update_artist_search_vectors(db: Optional[Session] = None, artist_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Met à jour les vecteurs de recherche TSVECTOR pour les artists.

        Args:
            db: Session de base de données
            artist_ids: IDs spécifiques des artists, ou None pour tous

        Returns:
            Statistiques de mise à jour
        """
        if not db:
            db = next(get_db())

        try:
            logger.info("[SEARCH INDEXING] Démarrage mise à jour TSVECTOR artists")

            # Requête pour mettre à jour les TSVECTOR des artists
            if artist_ids:
                query = text("""
                    UPDATE artists
                    SET search = to_tsvector('english', COALESCE(name, ''))
                    WHERE id = ANY(:artist_ids) AND name IS NOT NULL
                """)
                result = db.execute(query, {"artist_ids": artist_ids})
                updated_count = result.rowcount
            else:
                query = text("""
                    UPDATE artists
                    SET search = to_tsvector('english', COALESCE(name, ''))
                    WHERE name IS NOT NULL
                """)
                result = db.execute(query)
                updated_count = result.rowcount

            db.commit()
            logger.info(f"[SEARCH INDEXING] Mis à jour {updated_count} artists TSVECTOR")

            return {
                "success": True,
                "artists_updated": updated_count,
                "type": "artists"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"[SEARCH INDEXING] Erreur mise à jour artists: {e}")
            return {
                "success": False,
                "error": str(e),
                "artists_updated": 0,
                "type": "artists"
            }

    @staticmethod
    def update_all_search_vectors(db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Met à jour tous les vecteurs de recherche TSVECTOR.

        Args:
            db: Session de base de données

        Returns:
            Statistiques complètes de mise à jour
        """
        if not db:
            db = next(get_db())

        logger.info("[SEARCH INDEXING] Démarrage mise à jour complète TSVECTOR")

        # Mise à jour des artists d'abord
        artist_result = SearchIndexingService.update_artist_search_vectors(db)

        # Puis des tracks
        track_result = SearchIndexingService.update_track_search_vectors(db)

        total_success = artist_result["success"] and track_result["success"]
        total_updated = artist_result.get("artists_updated", 0) + track_result.get("tracks_updated", 0)

        result = {
            "success": total_success,
            "total_updated": total_updated,
            "artists": artist_result,
            "tracks": track_result
        }

        if total_success:
            logger.info(f"[SEARCH INDEXING] Mise à jour complète réussie: {total_updated} éléments")
        else:
            logger.error("[SEARCH INDEXING] Mise à jour complète partiellement échouée")

        return result

    @staticmethod
    def get_indexing_stats(db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques d'indexation.

        Args:
            db: Session de base de données

        Returns:
            Statistiques d'indexation
        """
        if not db:
            db = next(get_db())

        try:
            # Stats tracks
            track_stats = db.execute(text("""
                SELECT
                    COUNT(*) as total_tracks,
                    COUNT(search) as indexed_tracks,
                    ROUND(
                        COUNT(search)::numeric / NULLIF(COUNT(*), 0) * 100, 2
                    ) as indexing_percentage
                FROM tracks
            """)).fetchone()

            # Stats artists
            artist_stats = db.execute(text("""
                SELECT
                    COUNT(*) as total_artists,
                    COUNT(search) as indexed_artists,
                    ROUND(
                        COUNT(search)::numeric / NULLIF(COUNT(*), 0) * 100, 2
                    ) as indexing_percentage
                FROM artists
            """)).fetchone()

            return {
                "tracks": {
                    "total": track_stats.total_tracks,
                    "indexed": track_stats.indexed_tracks,
                    "percentage": track_stats.indexing_percentage
                },
                "artists": {
                    "total": artist_stats.total_artists,
                    "indexed": artist_stats.indexed_artists,
                    "percentage": artist_stats.indexing_percentage
                }
            }

        except Exception as e:
            logger.error(f"Erreur récupération stats indexation: {e}")
            return {"error": str(e)}

    @staticmethod
    def create_triggers_for_auto_indexing(db: Optional[Session] = None) -> bool:
        """
        Crée des triggers PostgreSQL pour maintenir automatiquement les TSVECTOR.

        Args:
            db: Session de base de données

        Returns:
            True si réussi
        """
        if not db:
            db = next(get_db())

        try:
            logger.info("[SEARCH INDEXING] Création triggers auto-indexation")

            # Trigger pour tracks
            db.execute(text("""
                CREATE OR REPLACE FUNCTION update_track_search_vector()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search := to_tsvector('english',
                        COALESCE(NEW.title, '') || ' ' ||
                        COALESCE(NEW.genre, '') || ' ' ||
                        COALESCE(NEW.year, '') || ' ' ||
                        COALESCE((SELECT name FROM artists WHERE id = NEW.track_artist_id), '') || ' ' ||
                        COALESCE((SELECT title FROM albums WHERE id = NEW.album_id), '')
                    );
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))

            db.execute(text("""
                DROP TRIGGER IF EXISTS trigger_update_track_search ON tracks;
                CREATE TRIGGER trigger_update_track_search
                    BEFORE INSERT OR UPDATE ON tracks
                    FOR EACH ROW EXECUTE FUNCTION update_track_search_vector();
            """))

            # Trigger pour artists
            db.execute(text("""
                CREATE OR REPLACE FUNCTION update_artist_search_vector()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search := to_tsvector('english', COALESCE(NEW.name, ''));
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))

            db.execute(text("""
                DROP TRIGGER IF EXISTS trigger_update_artist_search ON artists;
                CREATE TRIGGER trigger_update_artist_search
                    BEFORE INSERT OR UPDATE ON artists
                    FOR EACH ROW EXECUTE FUNCTION update_artist_search_vector();
            """))

            db.commit()
            logger.info("[SEARCH INDEXING] Triggers auto-indexation créés")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"[SEARCH INDEXING] Erreur création triggers: {e}")
            return False

    @staticmethod
    def create_materialized_views_for_facets(db: Optional[Session] = None) -> bool:
        """
        Crée des vues matérialisées pour optimiser les facettes fréquentes.

        Args:
            db: Session de base de données

        Returns:
            True si réussi
        """
        if not db:
            db = next(get_db())

        try:
            logger.info("[SEARCH INDEXING] Création vues matérialisées pour facettes")

            # Vue matérialisée pour les genres
            db.execute(text("""
                DROP MATERIALIZED VIEW IF EXISTS mv_genre_facets;
                CREATE MATERIALIZED VIEW mv_genre_facets AS
                SELECT
                    genre,
                    COUNT(*) as count,
                    ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rank
                FROM tracks
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY count DESC;
            """))

            # Vue matérialisée pour les artistes
            db.execute(text("""
                DROP MATERIALIZED VIEW IF EXISTS mv_artist_facets;
                CREATE MATERIALIZED VIEW mv_artist_facets AS
                SELECT
                    a.name as artist_name,
                    COUNT(t.id) as track_count,
                    ROW_NUMBER() OVER (ORDER BY COUNT(t.id) DESC) as rank
                FROM artists a
                JOIN tracks t ON a.id = t.track_artist_id
                GROUP BY a.id, a.name
                ORDER BY track_count DESC;
            """))

            # Vue matérialisée pour les décennies
            db.execute(text("""
                DROP MATERIALIZED VIEW IF EXISTS mv_decade_facets;
                CREATE MATERIALIZED VIEW mv_decade_facets AS
                SELECT
                    CASE
                        WHEN year ~ '^\d{4}$' THEN (CAST(year AS INTEGER) / 10) * 10
                        ELSE NULL
                    END as decade,
                    COUNT(*) as count,
                    ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rank
                FROM tracks
                WHERE year IS NOT NULL AND year ~ '^\d{4}$'
                GROUP BY decade
                HAVING decade IS NOT NULL
                ORDER BY count DESC;
            """))

            # Index sur les vues matérialisées
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_genre_facets_genre ON mv_genre_facets(genre);"))
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_artist_facets_name ON mv_artist_facets(artist_name);"))
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_decade_facets_decade ON mv_decade_facets(decade);"))

            db.commit()
            logger.info("[SEARCH INDEXING] Vues matérialisées créées")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"[SEARCH INDEXING] Erreur création vues matérialisées: {e}")
            return False

    @staticmethod
    def refresh_materialized_views(db: Optional[Session] = None) -> bool:
        """
        Rafraîchit les vues matérialisées pour les facettes.

        Args:
            db: Session de base de données

        Returns:
            True si réussi
        """
        if not db:
            db = next(get_db())

        try:
            logger.info("[SEARCH INDEXING] Rafraîchissement vues matérialisées")

            db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_genre_facets;"))
            db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_artist_facets;"))
            db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_decade_facets;"))

            db.commit()
            logger.info("[SEARCH INDEXING] Vues matérialisées rafraîchies")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"[SEARCH INDEXING] Erreur rafraîchissement vues matérialisées: {e}")
            return False