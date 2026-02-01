"""
Service métier pour la gestion des genres.
Déplace toute la logique métier depuis genres_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.api.models.genres_model, backend.api.schemas.genres_schema
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional
from backend.api.models.genres_model import Genre as GenreModel
from backend.api.schemas.genres_schema import GenreCreate
from datetime import datetime


class GenreService:
    def __init__(self, db: AsyncSession):
        self.session = db

    async def search_genres(
        self, name: Optional[str] = None, skip: int = 0, limit: Optional[int] = None
    ) -> List[dict]:
        if name:
            sql = text("""
                SELECT id, name, date_added, date_modified
                FROM genres
                WHERE LOWER(name) LIKE :name_pattern
                LIMIT :limit OFFSET :skip
            """)
            result = await self.session.execute(
                sql,
                {
                    "name_pattern": f"%{name.lower()}%",
                    "limit": limit if limit is not None else 1000,
                    "skip": skip,
                },
            )
        else:
            sql = text(
                "SELECT id, name, date_added, date_modified FROM genres LIMIT :limit OFFSET :skip"
            )
            result = await self.session.execute(
                sql,
                {
                    "limit": limit if limit is not None else 1000,
                    "skip": skip,
                },
            )

        genres = []
        for row in result:
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added
                if isinstance(row.date_added, datetime)
                else None,
                "date_modified": row.date_modified
                if isinstance(row.date_modified, datetime)
                else None,
            }
            genres.append(genre_data)

        return genres

    async def create_genre(self, genre: GenreCreate) -> GenreModel:
        db_genre = GenreModel(**genre.model_dump())
        self.session.add(db_genre)
        await self.session.commit()
        await self.session.refresh(db_genre)
        return db_genre

    async def read_genres(self, skip: int = 0, limit: int = 100) -> List[dict]:
        sql = text(
            "SELECT id, name, date_added, date_modified FROM genres LIMIT :limit OFFSET :skip"
        )
        result = await self.session.execute(sql, {"limit": limit, "skip": skip})
        genres = []
        for row in result:
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added
                if isinstance(row.date_added, datetime)
                else None,
                "date_modified": row.date_modified
                if isinstance(row.date_modified, datetime)
                else None,
            }
            genres.append(genre_data)
        return genres

    async def read_genre(self, genre_id: int) -> dict:
        sql = text(
            "SELECT id, name, date_added, date_modified FROM genres WHERE id = :genre_id"
        )
        result = await self.session.execute(sql, {"genre_id": genre_id})
        row = result.first()
        if row is None:
            return None
        genre_data = {
            "id": row.id,
            "name": row.name,
            "date_added": row.date_added
            if isinstance(row.date_added, datetime)
            else None,
            "date_modified": row.date_modified
            if isinstance(row.date_modified, datetime)
            else None,
            "tracks": [],
            "albums": [],
        }
        return genre_data

    async def update_genre(
        self, genre_id: int, genre: GenreCreate
    ) -> Optional[GenreModel]:
        result = await self.session.execute(
            select(GenreModel).where(GenreModel.id == genre_id)
        )
        db_genre = result.scalars().first()
        if db_genre is None:
            return None
        for key, value in genre.model_dump().items():
            setattr(db_genre, key, value)
        await self.session.commit()
        await self.session.refresh(db_genre)
        return db_genre

    async def delete_genre(self, genre_id: int) -> bool:
        result = await self.session.execute(
            select(GenreModel).where(GenreModel.id == genre_id)
        )
        genre = result.scalars().first()
        if genre is None:
            return False
        await self.session.delete(genre)
        await self.session.commit()
        return True
