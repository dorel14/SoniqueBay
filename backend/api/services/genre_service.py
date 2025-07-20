from fastapi import HTTPException
from sqlalchemy import  text
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from api.schemas.genres_schema import GenreCreate, Genre, GenreWithRelations
from api.models.genres_model import Genre as GenreModel
from datetime import datetime
from utils.session import transactional

class GenreService:
    @transactional
    async def search_genres(
        self,
        session: SQLAlchemySession,
        name: Optional[str] = None
    ) -> List[Genre]:
        """Recherche des genres par nom."""
        try:
            if name:
                sql = text("""
                    SELECT id, name, date_added, date_modified 
                    FROM genres 
                    WHERE LOWER(name) LIKE :name_pattern
                """)
                result = session.execute(sql, {"name_pattern": f"%{name.lower()}%"})
            else:
                sql = text("SELECT id, name, date_added, date_modified FROM genres")
                result = session.execute(sql)
            
            genres = []
            for row in result:
                genre_data = {
                    "id": row.id,
                    "name": row.name,
                    "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                    "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None
                }
                genres.append(genre_data)
            
            return genres
            
        except Exception as e:
            print(f"Error in search_genres: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")

    @transactional
    async def create_genre(self, session: SQLAlchemySession, genre: GenreCreate) -> Genre:
        try:
            db_genre = GenreModel(**genre.model_dump())
            session.add(db_genre)
            session.flush()
            session.refresh(db_genre)
            return db_genre
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors de la création: {str(e)}")

    @transactional
    async def read_genres(self, session: SQLAlchemySession, skip: int = 0, limit: int = 100) -> List[Genre]:
        try:
            sql = text("SELECT id, name, date_added, date_modified FROM genres LIMIT :limit OFFSET :skip")
            result = session.execute(sql, {"limit": limit, "skip": skip})
            
            genres = []
            for row in result:
                genre_data = {
                    "id": row.id,
                    "name": row.name,
                    "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                    "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None
                }
                genres.append(genre_data)
            
            return genres
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

    @transactional
    async def read_genre(self, session: SQLAlchemySession, genre_id: int) -> GenreWithRelations:
        try:
            sql = text("SELECT id, name, date_added, date_modified FROM genres WHERE id = :genre_id")
            result = session.execute(sql, {"genre_id": genre_id})
            row = result.first()
            
            if row is None:
                raise HTTPException(status_code=404, detail="Genre non trouvé")
            
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None,
                "tracks": [],
                "albums": []
            }
            
            return genre_data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

    @transactional
    async def update_genre(self, session: SQLAlchemySession, genre_id: int, genre: GenreCreate) -> Genre:
        try:
            db_genre = session.query(GenreModel).filter(GenreModel.id == genre_id).first()
            if db_genre is None:
                raise HTTPException(status_code=404, detail="Genre non trouvé")
            
            for key, value in genre.model_dump(exclude_unset=True).items():
                setattr(db_genre, key, value)
            
            session.flush()
            session.refresh(db_genre)
            return db_genre
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}")

    @transactional
    async def delete_genre(self, session: SQLAlchemySession, genre_id: int):
        try:
            genre = session.query(GenreModel).filter(GenreModel.id == genre_id).first()
            if genre is None:
                raise HTTPException(status_code=404, detail="Genre non trouvé")
            
            session.delete(genre)
            return {"ok": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors de la suppression: {str(e)}")

    @transactional
    async def get_genres_by_album_id(self, session: SQLAlchemySession, album_id: int) -> List[Genre]:
        sql = text("""
            SELECT g.id, g.name, g.date_added, g.date_modified
            FROM genres g
            JOIN tracks_genre_links tgl ON g.id = tgl.genre_id
            JOIN tracks t ON tgl.track_id = t.id
            WHERE t.album_id = :album_id
            GROUP BY g.id
        """)
        result = session.execute(sql, {"album_id": album_id})
        genres = []
        for row in result:
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None
            }
            genres.append(genre_data)
        return genres

    @transactional
    async def get_genres_by_artist_id(self, session: SQLAlchemySession, artist_id: int) -> List[Genre]:
        sql = text("""
            SELECT g.id, g.name, g.date_added, g.date_modified
            FROM genres g
            JOIN tracks_genre_links tgl ON g.id = tgl.genre_id
            JOIN tracks t ON tgl.track_id = t.id
            JOIN artists a ON t.track_artist_id = a.id
            WHERE a.id = :artist_id
            GROUP BY g.id
        """)
        result = session.execute(sql, {"artist_id": artist_id})
        genres = []
        for row in result:
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None
            }
            genres.append(genre_data)
        return genres