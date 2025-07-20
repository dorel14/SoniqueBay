from venv import logger
from fastapi import APIRouter, Body, HTTPException
from utils.search import get_or_create_index, search_index, add_to_index
from api.schemas.search_schema import SearchQuery, SearchResult, SearchFacet, AddToIndexRequest

import os

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("/index")
def api_get_or_create_index(index_dir: str = Body(...)):
    # Ici tu peux initialiser ou vérifier l'index côté serveur
    get_or_create_index(index_dir)
    return {"index_name": "music_index", "index_dir": index_dir}

@router.post("/add")
def api_add_to_index(body: AddToIndexRequest):
    logger.info(f"Adding data to index: {body.index_dir}, data: {body.whoosh_data}")
    index = get_or_create_index(body.index_dir, body.index_name)
    add_to_index(index, body.whoosh_data)
    return {"status": "ok"}

@router.post("/", response_model=SearchResult)
async def search(query: SearchQuery):
    try:
        # Initialiser l'index
        index_dir = os.path.join(os.getcwd(), "search_index")
        index = get_or_create_index(index_dir)

        # Effectuer la recherche
        total, artist_facet, genre_facet, decade_facet, results = search_index(index, query.query)

        # Calculer la pagination
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paginated_results = results[start:end]

        # Organiser les facettes
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
