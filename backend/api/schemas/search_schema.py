from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AddToIndexRequest(BaseModel):
    index_dir: str
    index_name: str
    whoosh_data: dict
class SearchQuery(BaseModel):
    query: str
    page: Optional[int] = 1
    page_size: Optional[int] = 10
    filters: Optional[Dict[str, List[str]]] = {}

class SearchFacet(BaseModel):
    name: str
    count: int

class SearchResult(BaseModel):
    total: int
    items: List[Dict[str, Any]]
    facets: Dict[str, List[SearchFacet]]
    page: int
    total_pages: int
