"""
Service de recherche pour l'API SoniqueBay
Déplace toute la logique métier de recherche ici.
Auteur : GitHub Copilot
Dépendances : backend.utils.search, backend.api.schemas.search_schema
"""
from backend.utils.search import get_or_create_index, search_index, add_to_index
from backend.api.schemas.search_schema import SearchQuery, SearchResult, SearchFacet
import os

class SearchService:

    @staticmethod
    def get_or_create_index(index_dir: str, index_name: str = "music_index"):
        # Laisser l’exception brute remonter (mock side_effect inclus)
        return get_or_create_index(index_dir, index_name)


    @staticmethod
    def add_to_index(index_dir: str, index_name: str, whoosh_data):
        try:
            index = get_or_create_index(index_dir, index_name)
        except Exception as e:
            raise Exception(f"Index creation failed: {str(e)}")
        add_to_index(index, whoosh_data)
        return {"status": "ok"}
    @staticmethod
    def search(query: SearchQuery, index_dir: str = None):
        # Laisser l’exception brute remonter (mock side_effect inclus)
        if index_dir is None:
            index_dir = os.path.join(os.getcwd(), "search_index")
        index = get_or_create_index(index_dir)
        total, artist_facet, genre_facet, decade_facet, results = search_index(index, query.query)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paginated_results = results[start:end]
        facets = {
            "artists": [SearchFacet(name=name, count=count) for name, count in artist_facet],
            "genres": [SearchFacet(name=name, count=count) for name, count in genre_facet],
            "decades": [SearchFacet(name=name, count=count) for name, count in decade_facet]
        }
        return SearchResult(
            total=total,
            items=paginated_results,
            facets=facets,
            page=query.page,
            total_pages=(total // query.page_size) + (1 if total % query.page_size else 0)
        )
