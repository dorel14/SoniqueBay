from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Float, Boolean
from sqlalchemy.orm import relationship, foreign


from backend.database import Base
from .genre_links import track_genre_links
from .tags_model import track_mood_tags, track_genre_tags
from .genres_model import track_genres

class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    album_id = Column(Integer, ForeignKey('albums.id'), nullable=True)
    path = Column(String, unique=True)
    duration = Column(Integer, nullable=True)
    track_number = Column(String, nullable=True)
    disc_number = Column(String, nullable=True)
    year = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    musicbrainz_id = Column(String, nullable=True, unique=True)
    musicbrainz_albumid = Column(String, nullable=True)
    musicbrainz_artistid = Column(String, nullable=True)
    musicbrainz_albumartistid = Column(String, nullable=True)
    musicbrainz_genre = Column(String, nullable=True)
    acoustid_fingerprint = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    cover_data = Column(String, nullable=True)  # Base64 encoded cover image data
    cover_mime_type = Column(String, nullable=True)
    bitrate = Column(Integer, nullable=True)
    date_added = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_modified = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    track_artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)  # Artiste principal de la piste
    featured_artists = Column(String, nullable=True)  # Artistes en featuring, séparés par des virgules

    # Nouveaux champs d'analyse audio
    bpm = Column(Float, nullable=True)
    key = Column(String, nullable=True)
    scale = Column(String, nullable=True)
    danceability = Column(Float, nullable=True)
    mood_happy = Column(Float, nullable=True)
    mood_aggressive = Column(Float, nullable=True)
    mood_party = Column(Float, nullable=True)
    mood_relaxed = Column(Float, nullable=True)
    instrumental = Column(Boolean, nullable=True)
    acoustic = Column(Boolean, nullable=True)
    tonal = Column(Boolean, nullable=True)
    genre_main = Column(String, nullable=True)

    # Relations
    track_artist = relationship("Artist", back_populates="tracks")
    album = relationship("Album", back_populates="tracks")
    genres = relationship("Genre", secondary="track_genres", back_populates="tracks")
    mood_tags = relationship("MoodTag", secondary=track_mood_tags, back_populates="tracks")
    genre_tags = relationship("GenreTag", secondary=track_genre_tags, back_populates="tracks")
    covers = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='track', foreign(Cover.entity_id)==Track.id)",
        viewonly=True
    )

