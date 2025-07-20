from sqlalchemy.orm import Query
from api.schemas.pagination_schema import PaginatedResponse
from typing import Type, TypeVar
from pydantic import BaseModel, create_model
from functools import lru_cache
T = TypeVar("T", bound=BaseModel)

def paginate_query(query: Query, schema: Type[T], skip: int = 0, limit: int = 100):
    total = query.count()
    items = query.offset(skip).limit(limit).all()

    # Créer dynamiquement un modèle Pydantic basé sur le type concret
    ConcretePaginated = type(
        f"Paginated_{schema.__name__}",
        (PaginatedResponse[schema],),
        {
            '__annotations__': {
                'count': int,
                'results': list[schema]
            }
        }
    )
    ConcretePaginated = get_concrete_paginated(schema)
    return ConcretePaginated(count=total, results=items)

@lru_cache
def get_concrete_paginated(schema: Type[BaseModel]):
    return type(
        f"Paginated_{schema.__name__}",
        (PaginatedResponse[schema],),
        {
            '__annotations__': {
                'count': int,
                'results': list[schema]
            }
        }
    )
