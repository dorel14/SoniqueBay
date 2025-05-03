from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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
