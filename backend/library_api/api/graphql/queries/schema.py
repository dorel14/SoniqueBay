
import strawberry

from backend.library_api.api.graphql.queries.queries import Query
from backend.library_api.api.graphql.queries.mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)