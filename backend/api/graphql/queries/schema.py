
import strawberry
from .query import Query
from .mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)