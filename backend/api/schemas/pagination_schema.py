from typing import Generic, List, TypeVar
#from pydantic.generics import BaseModel as GenericModel
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    results: List[T]