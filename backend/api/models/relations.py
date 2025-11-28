# from sqlalchemy.orm import relationship
# from .tags_model import track_mood_tags, track_genre_tags
# from .genres_model import artist_genres

# # Relations Artist <-> Album
# Artist.albums = relationship("Album", back_populates="album_artist")

# # Relations Artist <-> Track
# Artist.tracks = relationship("Track", back_populates="track_artist")
# Track.track_artist = relationship("Artist", back_populates="tracks")

# # Relations Album <-> Track
# Album.tracks = relationship("Track", back_populates="album")
# Track.album = relationship("Album", back_populates="tracks")
# Album.album_artist = relationship("Artist", back_populates="albums")

# # Relations Track <-> Genre (table secondaire)
# Track.genres = relationship("Genre", secondary="track_genres", back_populates="tracks")
# Genre.tracks = relationship("Track", secondary="track_genres", back_populates="genres")

# # Relations Artist <-> Genre (table secondaire)
# Artist.genres = relationship("Genre", secondary=artist_genres, back_populates="artists")
# Genre.artists = relationship("Artist", secondary=artist_genres, back_populates="genres")

# # Relations Track <-> MoodTag/GenreTag (table secondaire)
# Track.mood_tags = relationship("MoodTag", secondary=track_mood_tags, back_populates="tracks")
# MoodTag.tracks = relationship("Track", secondary=track_mood_tags, back_populates="mood_tags")

# Track.genre_tags = relationship("GenreTag", secondary=track_genre_tags, back_populates="tracks")
# GenreTag.tracks = relationship("Track", secondary=track_genre_tags, back_populates="genre_tags")

# # Relations Track <-> TrackVector
# Track.track_vector = relationship("TrackVector", back_populates="track", cascade="all", passive_deletes=True, uselist=False)
# TrackVector.track = relationship("Track", back_populates="track_vector", uselist=False)

# # Relations Cover <-> Artist/Album/Track (viewonly)
# Artist.covers = relationship(
#     "Cover",
#     primaryjoin="and_(Cover.entity_type=='artist', Artist.id==Cover.entity_id)",
#     lazy="selectin",
#     foreign_keys=[Cover.entity_id],
#     viewonly=True
# )
# Album.covers = relationship(
#     "Cover",
#     primaryjoin="and_(Cover.entity_type=='album', Album.id==Cover.entity_id)",
#     lazy="selectin",
#     foreign_keys=[Cover.entity_id],
#     viewonly=True
# )
# Track.covers = relationship(
#     "Cover",
#     primaryjoin="and_(Cover.entity_type=='track', Track.id==Cover.entity_id)",
#     lazy="selectin",
#     foreign_keys=[Cover.entity_id],
#     viewonly=True
# )

