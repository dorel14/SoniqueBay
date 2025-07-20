from ..graph_init import strawchemy
from ...models.artists_model import Artist

@strawchemy.type(model=Artist, include=["id","name"])
class ArtistType():
    pass

@strawchemy.filter(model=Artist, include=["name"])
class ArtistFilter():
    pass

@strawchemy.order(model=Artist, include=["name"])
class ArtistOrderBy():
    pass