from __future__ import annotations
import strawberry
from backend.api.graphql.types.tracks_type import TrackType, TrackCreateInput, TrackUpdateInput


@strawberry.type
class TrackMutations:
    """Mutations for tracks."""

    @strawberry.mutation
    def create_track(self, data: TrackCreateInput, info: strawberry.types.Info) -> TrackType:
        """Create a new track."""
        from backend.services.track_service import TrackService
        from backend.api.schemas.tracks_schema import TrackCreate
        session = info.context.db
        service = TrackService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        track_data_dict = {
            'title': data.title,
            'path': data.path,
            'track_artist_id': data.track_artist_id,
            'album_id': data.album_id,
            'duration': data.duration,
            'track_number': data.track_number,
            'disc_number': data.disc_number,
            'year': data.year,
            'genre': data.genre,
            'file_type': data.file_type,
            'bitrate': data.bitrate,
            'featured_artists': data.featured_artists,
            'bpm': data.bpm,
            'key': data.key,
            'scale': data.scale,
            'danceability': data.danceability,
            'mood_happy': data.mood_happy,
            'mood_aggressive': data.mood_aggressive,
            'mood_party': data.mood_party,
            'mood_relaxed': data.mood_relaxed,
            'instrumental': data.instrumental,
            'acoustic': data.acoustic,
            'tonal': data.tonal,
            'camelot_key': data.camelot_key,
            'genre_main': data.genre_main,
            'musicbrainz_id': data.musicbrainz_id,
            'musicbrainz_albumid': data.musicbrainz_albumid,
            'musicbrainz_artistid': data.musicbrainz_artistid,
            'musicbrainz_albumartistid': data.musicbrainz_albumartistid,
            'acoustid_fingerprint': data.acoustid_fingerprint
        }
        track_create = TrackCreate(**track_data_dict)

        track = service.create_track(track_create)
        return TrackType(
            id=track.id,
            title=track.title,
            path=track.path,
            track_artist_id=track.track_artist_id,
            album_id=track.album_id,
            duration=track.duration,
            track_number=track.track_number,
            disc_number=track.disc_number,
            year=track.year,
            genre=track.genre,
            file_type=track.file_type,
            bitrate=track.bitrate,
            featured_artists=track.featured_artists,
            bpm=track.bpm,
            key=track.key,
            scale=track.scale,
            danceability=track.danceability,
            mood_happy=track.mood_happy,
            mood_aggressive=track.mood_aggressive,
            mood_party=track.mood_party,
            mood_relaxed=track.mood_relaxed,
            instrumental=track.instrumental,
            acoustic=track.acoustic,
            tonal=track.tonal,
            camelot_key=track.camelot_key,
            genre_main=track.genre_main,
            musicbrainz_id=track.musicbrainz_id,
            musicbrainz_albumid=track.musicbrainz_albumid,
            musicbrainz_artistid=track.musicbrainz_artistid,
            musicbrainz_albumartistid=track.musicbrainz_albumartistid,
            acoustid_fingerprint=track.acoustid_fingerprint,
            covers=[]
        )

    @strawberry.mutation
    def create_tracks(self, data: list[TrackCreateInput], info: strawberry.types.Info) -> list[TrackType]:
        """Create multiple tracks in batch."""
        from backend.services.track_service import TrackService
        from backend.api.schemas.tracks_schema import TrackCreate
        session = info.context.db
        service = TrackService(session)

        # Convertir les objets Strawberry en objets Pydantic
        tracks_data = []
        for track_input in data:
            track_data_dict = {
                'title': track_input.title,
                'path': track_input.path,
                'track_artist_id': track_input.track_artist_id,
                'album_id': track_input.album_id,
                'duration': track_input.duration,
                'track_number': track_input.track_number,
                'disc_number': track_input.disc_number,
                'year': track_input.year,
                'genre': track_input.genre,
                'file_type': track_input.file_type,
                'bitrate': track_input.bitrate,
                'featured_artists': track_input.featured_artists,
                'bpm': track_input.bpm,
                'key': track_input.key,
                'scale': track_input.scale,
                'danceability': track_input.danceability,
                'mood_happy': track_input.mood_happy,
                'mood_aggressive': track_input.mood_aggressive,
                'mood_party': track_input.mood_party,
                'mood_relaxed': track_input.mood_relaxed,
                'instrumental': track_input.instrumental,
                'acoustic': track_input.acoustic,
                'tonal': track_input.tonal,
                'camelot_key': track_input.camelot_key,
                'genre_main': track_input.genre_main,
                'musicbrainz_id': track_input.musicbrainz_id,
                'musicbrainz_albumid': track_input.musicbrainz_albumid,
                'musicbrainz_artistid': track_input.musicbrainz_artistid,
                'musicbrainz_albumartistid': track_input.musicbrainz_albumartistid,
                'acoustid_fingerprint': track_input.acoustid_fingerprint
            }
            tracks_data.append(TrackCreate(**track_data_dict))

        tracks = service.create_or_update_tracks_batch(tracks_data)
        return [
            TrackType(
                id=track.id,
                title=track.title,
                path=track.path,
                track_artist_id=track.track_artist_id,
                album_id=track.album_id,
                duration=track.duration,
                track_number=track.track_number,
                disc_number=track.disc_number,
                year=track.year,
                genre=track.genre,
                file_type=track.file_type,
                bitrate=track.bitrate,
                featured_artists=track.featured_artists,
                bpm=track.bpm,
                key=track.key,
                scale=track.scale,
                danceability=track.danceability,
                mood_happy=track.mood_happy,
                mood_aggressive=track.mood_aggressive,
                mood_party=track.mood_party,
                mood_relaxed=track.mood_relaxed,
                instrumental=track.instrumental,
                acoustic=track.acoustic,
                tonal=track.tonal,
                camelot_key=track.camelot_key,
                genre_main=track.genre_main,
                musicbrainz_id=track.musicbrainz_id,
                musicbrainz_albumid=track.musicbrainz_albumid,
                musicbrainz_artistid=track.musicbrainz_artistid,
                musicbrainz_albumartistid=track.musicbrainz_albumartistid,
                acoustid_fingerprint=track.acoustid_fingerprint,
                covers=[]
            )
            for track in tracks
        ]

    @strawberry.mutation
    def update_track_by_id(self, data: TrackUpdateInput, info: strawberry.types.Info) -> TrackType:
        """Update a track by ID."""
        from backend.services.track_service import TrackService
        session = info.context.db
        service = TrackService(session)

        # Créer un dictionnaire avec tous les champs pour l'update
        track_data_dict = {
            'title': data.title,
            'path': data.path,
            'track_artist_id': data.track_artist_id,
            'album_id': data.album_id,
            'duration': data.duration,
            'track_number': data.track_number,
            'disc_number': data.disc_number,
            'year': data.year,
            'genre': data.genre,
            'file_type': data.file_type,
            'bitrate': data.bitrate,
            'featured_artists': data.featured_artists,
            'bpm': data.bpm,
            'key': data.key,
            'scale': data.scale,
            'danceability': data.danceability,
            'mood_happy': data.mood_happy,
            'mood_aggressive': data.mood_aggressive,
            'mood_party': data.mood_party,
            'mood_relaxed': data.mood_relaxed,
            'instrumental': data.instrumental,
            'acoustic': data.acoustic,
            'tonal': data.tonal,
            'camelot_key': data.camelot_key,
            'genre_main': data.genre_main,
            'musicbrainz_id': data.musicbrainz_id,
            'musicbrainz_albumid': data.musicbrainz_albumid,
            'musicbrainz_artistid': data.musicbrainz_artistid,
            'musicbrainz_albumartistid': data.musicbrainz_albumartistid,
            'acoustid_fingerprint': data.acoustid_fingerprint
        }

        track = service.update_track(data.id, track_data_dict)
        if not track:
            raise ValueError(f"Track with id {data.id} not found")
        return TrackType(
            id=track.id,
            title=track.title,
            path=track.path,
            track_artist_id=track.track_artist_id,
            album_id=track.album_id,
            duration=track.duration,
            track_number=track.track_number,
            disc_number=track.disc_number,
            year=track.year,
            genre=track.genre,
            file_type=track.file_type,
            bitrate=track.bitrate,
            featured_artists=track.featured_artists,
            bpm=track.bpm,
            key=track.key,
            scale=track.scale,
            danceability=track.danceability,
            mood_happy=track.mood_happy,
            mood_aggressive=track.mood_aggressive,
            mood_party=track.mood_party,
            mood_relaxed=track.mood_relaxed,
            instrumental=track.instrumental,
            acoustic=track.acoustic,
            tonal=track.tonal,
            camelot_key=track.camelot_key,
            genre_main=track.genre_main,
            musicbrainz_id=track.musicbrainz_id,
            musicbrainz_albumid=track.musicbrainz_albumid,
            musicbrainz_artistid=track.musicbrainz_artistid,
            musicbrainz_albumartistid=track.musicbrainz_albumartistid,
            acoustid_fingerprint=track.acoustid_fingerprint,
            covers=[]
        )

    @strawberry.mutation
    def upsert_track(self, data: TrackCreateInput, info: strawberry.types.Info) -> TrackType:
        """Upsert a track (create if not exists, update if exists)."""
        from backend.services.track_service import TrackService
        from backend.api.schemas.tracks_schema import TrackCreate
        session = info.context.db
        service = TrackService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        track_data_dict = {
            'title': data.title,
            'path': data.path,
            'track_artist_id': data.track_artist_id,
            'album_id': data.album_id,
            'duration': data.duration,
            'track_number': data.track_number,
            'disc_number': data.disc_number,
            'year': data.year,
            'genre': data.genre,
            'file_type': data.file_type,
            'bitrate': data.bitrate,
            'featured_artists': data.featured_artists,
            'bpm': data.bpm,
            'key': data.key,
            'scale': data.scale,
            'danceability': data.danceability,
            'mood_happy': data.mood_happy,
            'mood_aggressive': data.mood_aggressive,
            'mood_party': data.mood_party,
            'mood_relaxed': data.mood_relaxed,
            'instrumental': data.instrumental,
            'acoustic': data.acoustic,
            'tonal': data.tonal,
            'camelot_key': data.camelot_key,
            'genre_main': data.genre_main,
            'musicbrainz_id': data.musicbrainz_id,
            'musicbrainz_albumid': data.musicbrainz_albumid,
            'musicbrainz_artistid': data.musicbrainz_artistid,
            'musicbrainz_albumartistid': data.musicbrainz_albumartistid,
            'acoustid_fingerprint': data.acoustid_fingerprint
        }
        track_create = TrackCreate(**track_data_dict)

        track = service.upsert_track(track_create)
        return TrackType(
            id=track.id,
            title=track.title,
            path=track.path,
            track_artist_id=track.track_artist_id,
            album_id=track.album_id,
            duration=track.duration,
            track_number=track.track_number,
            disc_number=track.disc_number,
            year=track.year,
            genre=track.genre,
            file_type=track.file_type,
            bitrate=track.bitrate,
            featured_artists=track.featured_artists,
            bpm=track.bpm,
            key=track.key,
            scale=track.scale,
            danceability=track.danceability,
            mood_happy=track.mood_happy,
            mood_aggressive=track.mood_aggressive,
            mood_party=track.mood_party,
            mood_relaxed=track.mood_relaxed,
            instrumental=track.instrumental,
            acoustic=track.acoustic,
            tonal=track.tonal,
            camelot_key=track.camelot_key,
            genre_main=track.genre_main,
            musicbrainz_id=track.musicbrainz_id,
            musicbrainz_albumid=track.musicbrainz_albumid,
            musicbrainz_artistid=track.musicbrainz_artistid,
            musicbrainz_albumartistid=track.musicbrainz_albumartistid,
            acoustid_fingerprint=track.acoustid_fingerprint,
            covers=[]
        )

    @strawberry.mutation
    def update_tracks(self, filter: str, data: str, info: strawberry.types.Info) -> list[TrackType]:
        """Update multiple tracks by filter."""
        from backend.services.track_service import TrackService
        session = info.context.db
        service = TrackService(session)
        filter_data = {"title": {"icontains": filter}}
        update_data = {"title": data}
        tracks = service.update_tracks_by_filter(filter_data, update_data)
        return [
            TrackType(
                id=track.id,
                title=track.title,
                path=track.path,
                track_artist_id=track.track_artist_id,
                album_id=track.album_id,
                duration=track.duration,
                track_number=track.track_number,
                disc_number=track.disc_number,
                year=track.year,
                genre=track.genre,
                file_type=track.file_type,
                bitrate=track.bitrate,
                featured_artists=track.featured_artists,
                bpm=track.bpm,
                key=track.key,
                scale=track.scale,
                danceability=track.danceability,
                mood_happy=track.mood_happy,
                mood_aggressive=track.mood_aggressive,
                mood_party=track.mood_party,
                mood_relaxed=track.mood_relaxed,
                instrumental=track.instrumental,
                acoustic=track.acoustic,
                tonal=track.tonal,
                camelot_key=track.camelot_key,
                genre_main=track.genre_main,
                musicbrainz_id=track.musicbrainz_id,
                musicbrainz_albumid=track.musicbrainz_albumid,
                musicbrainz_artistid=track.musicbrainz_artistid,
                musicbrainz_albumartistid=track.musicbrainz_albumartistid,
                acoustid_fingerprint=track.acoustid_fingerprint,
                covers=[]
            )
            for track in tracks
        ]