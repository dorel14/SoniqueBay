from typing import Type, Callable,Any
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from library_api.utils.paginations import paginate_query
from library_api.api.schemas.pagination_schema import PaginatedResponse
from pydantic import BaseModel
from library_api.utils.database import get_db  # Ton propre get_db dépendance

def paginated_route(
    router: APIRouter,
    path: str,
    schema: Type[BaseModel],
    db_model: Any,
    *,
    tags: list[str] = None,
    summary: str = None,
    description: str = None,
):
    def decorator(func: Callable):
        async def endpoint(skip: int = 0, limit: int = 25, db: Session = Depends(get_db)):
            query = db.query(db_model).order_by(db_model.name)
            return paginate_query(query, schema, skip, limit=limit)

        endpoint.__name__ = f"get_{db_model.__name__.lower()}_paginated"
        router.add_api_route(
            path,
            endpoint,
            methods=["GET"],
            response_model=PaginatedResponse[schema],
            tags=tags or [db_model.__name__],
            summary=summary or f"Liste paginée des {db_model.__name__}",
            description=description or f"Renvoie une liste paginée de {schema.__name__}.",
        )

        return endpoint
    return decorator