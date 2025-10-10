"""
Service de recherche pour l'API SoniqueBay
Utilise SQLite FTS pour la recherche.
Auteur : GitHub Copilot
Dépendances : backend.api.schemas.search_schema
"""
from backend.library_api.api.schemas.search_schema import SearchQuery, SearchResult
from backend.library_api.utils.search import get_or_create_index, add_to_index
from sqlalchemy import text

class SearchService:

    @staticmethod
    def search(query: SearchQuery, db=None):
        if not db:
            from backend.library_api.utils.database import get_db
            db = next(get_db())

        # Search in tracks FTS
        search_query = f"""
        SELECT t.id, t.title, t.path, a.name as artist_name, al.title as album_title, t.genre,
               bm25(tracks_fts) as score
        FROM tracks_fts
        JOIN tracks t ON tracks_fts.rowid = t.id
        LEFT JOIN artists a ON t.track_artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id
        WHERE tracks_fts MATCH :query
        ORDER BY score
        LIMIT :limit OFFSET :offset
        """  # noqa: F541

        offset = (query.page - 1) * query.page_size
        results = db.execute(text(search_query), {"query": query.query, "limit": query.page_size, "offset": offset}).fetchall()

        # Get total count
        count_query = "SELECT count(*) FROM tracks_fts WHERE tracks_fts MATCH :query"
        total = db.execute(text(count_query), {"query": query.query}).scalar()

        # Convert to SearchResult format
        items = []
        for row in results:
            items.append({
                "id": row.id,
                "title": row.title,
                "artist": row.artist_name,
                "album": row.album_title,
                "genre": row.genre,
                "path": row.path
            })

        # For facets, we can add later if needed
        facets = {
            "artists": [],
            "genres": [],
            "decades": []
        }

        return SearchResult(
            total=total,
            items=items,
            facets=facets,
            page=query.page,
            total_pages=(total // query.page_size) + (1 if total % query.page_size else 0)
        )

    @staticmethod
    def add_to_index(index_dir: str, index_name: str, whoosh_data: dict):
        """Add data to Whoosh index."""
        index = get_or_create_index(index_dir, index_name)
        add_to_index(index, whoosh_data)
