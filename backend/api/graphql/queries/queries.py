from ..graph_init import strawchemy
import strawberry
#from ..types.artist_type import ArtistType, ArtistFilter, ArtistOrderBy
from ..types.user_type import UserType,UserFilter,UserOrderBy

@strawberry.type
class Query:
    #artists: list[ArtistType] = strawchemy.field(filter_input=ArtistFilter, order_by=ArtistOrderBy, pagination=True)
    users: list[UserType] = strawchemy.field(filter_input=UserFilter, order_by=UserOrderBy, pagination=True)



schema = strawberry.Schema(Query)