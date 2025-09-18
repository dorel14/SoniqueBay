# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.covers_model import Cover
import strawberry

@strawberry.type
class CoverType:
    id: int
    entity_type: str
    entity_id: int
    url: str
    cover_data: str | None
    date_added: str
    date_modified: str
    mime_type: str | None