from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.covers_model import Cover
import strawberry

@strawchemy.order(Cover, include="all")
class CoverOrderedType: ...
@strawchemy.filter(Cover, include="all")
class CoverFilterType: ...
@strawchemy.type(Cover, include="all",filter_input=CoverFilterType, order_by=CoverOrderedType, override=True)
class CoverType: ...