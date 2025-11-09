from __future__ import annotations
import strawberry
from typing import Optional
from backend.library_api.api.graphql.types.genres_type import GenreType
from backend.library_api.api.graphql.types.covers_type import CoverType
from backend.library_api.api.graphql.types.tags_type import GenreTagType, MoodTagType
from backend.library_api.services.genres_service import GenreService
from backend.library_api.services.covers_service import CoverService
from backend.library_api.services.tags_service import TagService


@strawberry.type
class OtherQueries:
    """Queries for other entities (genres, covers, tags)."""

    @strawberry.field
    def genre(self, info: strawberry.types.Info, id: int) -> Optional[GenreType]:
        db = info.context.session
        service = GenreService(db)
        genre = service.read_genre(id)
        return GenreType.from_orm(genre) if genre else None

    @strawberry.field
    def genres(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[GenreType]:
        db = info.context.session
        service = GenreService(db)
        genres = service.read_genres(skip, limit)
        return [GenreType.from_orm(g) for g in genres]

    @strawberry.field
    def cover(self, info: strawberry.types.Info, id: int) -> Optional[CoverType]:
        db = info.context.session
        service = CoverService(db)
        cover = service.get_cover_by_id(id)
        return CoverType.from_orm(cover) if cover else None

    @strawberry.field
    def covers(self, info: strawberry.types.Info) -> list[CoverType]:
        db = info.context.session
        service = CoverService(db)
        covers = service.get_covers()
        return [CoverType.from_orm(c) for c in covers]

    @strawberry.field
    def genre_tag(self, info: strawberry.types.Info, id: int) -> Optional[GenreTagType]:
        db = info.context.session
        service = TagService(db)
        tag = service.get_genre_tag(id)
        return GenreTagType.from_orm(tag) if tag else None

    @strawberry.field
    def genre_tags(self, info: strawberry.types.Info) -> list[GenreTagType]:
        db = info.context.session
        service = TagService(db)
        tags = service.get_genre_tags()
        return [GenreTagType.from_orm(t) for t in tags]

    @strawberry.field
    def mood_tag(self, info: strawberry.types.Info, id: int) -> Optional[MoodTagType]:
        db = info.context.session
        service = TagService(db)
        tag = service.get_mood_tag(id)
        return MoodTagType.from_orm(tag) if tag else None

    @strawberry.field
    def mood_tags(self, info: strawberry.types.Info) -> list[MoodTagType]:
        db = info.context.session
        service = TagService(db)
        tags = service.get_mood_tags()
        return [MoodTagType.from_orm(t) for t in tags]