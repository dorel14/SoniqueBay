from ..gqContext_init import strawchemy
import strawberry
from .query import Query


schema = strawberry.Schema(query=Query)