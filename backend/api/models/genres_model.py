import trace
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from backend.database import Base

class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # Genre name
    description = Column(String)  # Description of the genre
    date_added = Column(String)  # Date when the genre was added to the database
    date_modified = Column(String)  # Date when the genre was last modified
    tracklist = relationship("Track", back_populates='genrelist', secondary='genre_links')  # Relationship to the Track model

    def __repr__(self):
        return f"<Genre(name='{self.name}', description='{self.description}')>"
