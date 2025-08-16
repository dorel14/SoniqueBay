
import strawberry
from backend.api.graphql.queries.query import Query
from backend.api.graphql.queries.mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)