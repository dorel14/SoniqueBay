
import strawberry

from backend.api.graphql.queries.queries import Query
from backend.api.graphql.queries.mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)