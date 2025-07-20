import os
from fastapi import HTTPException
from utils.logging import logger
from utils.search import get_or_create_index, search_index, add_to_index
from api.schemas.search_schema import SearchQuery, SearchResult, SearchFacet, AddToIndexRequest

class SearchService:
    def api_get_or_create_index(self, index_dir: str):
        get_or_create_index(index_dir)
        return {"index_name": "music_index", "index_dir": index_dir}

    def api_add_to_index(self, body: AddToIndexRequest):
        logger.info(f"Adding data to index: {body.index_dir}, data: {body.whoosh_data}")
        index = get_or_create_index(body.index_dir, body.index_name)
        add_to_index(index, body.whoosh_data)
        return {"status": "ok"}

    async def search(self, query: SearchQuery) -> SearchResult:
        try:
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
                total_pages=(total + query.page_size - 1) // query.page_size
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))