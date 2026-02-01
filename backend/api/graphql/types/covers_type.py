# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
import strawberry

@strawberry.type
class CoverType:
    id: int
    entity_type: str
    entity_id: int
    cover_data: str | None = strawberry.field(name="coverData")
    date_added: str
    date_modified: str
    mime_type: str | None = strawberry.field(name="mimeType")

    @strawberry.field
    def url(self) -> str:
        return f"/covers/{self.entity_type}/{self.entity_id}"