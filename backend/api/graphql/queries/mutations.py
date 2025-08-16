from __future__ import annotations
import strawberry
from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.graphql.types.artist_type import  ArtistCreateInputType, ArtistFilterType, ArtistType, ArtistUpdateInputType, ArtistFilterUpdateInputType, ArtistUpsertConflictFieldsType, ArtistUpsertUpdateFieldsType
from backend.api.graphql.types.albums_type import AlbumCreateInputType, AlbumType,AlbumFilterType, AlbumFilterUpdateInputType, AlbumUpdateInputType, AlbumUpsertConflictFieldsType, AlbumUpsertUpdateFieldsType
from backend.api.graphql.types.tracks_type import TrackCreateInputType, TrackType, TrackFilterType, TrackFilterUpdateInputType, TrackUpdateInputType,TrackUpsertConflictFieldsType, TrackUpsertUpdateFieldsType

@strawberry.type
class Mutation:
    # Create Artist mutation
    # This mutation allows creating a single artist or multiple artists at once.
    # It uses the ArtistCreateInputType to define the input structure.
    # The create_artist field returns a single ArtistType, while create_artists returns a list of ArtistType.
    # This is useful for batch operations where you might want to create multiple artists in one go
    create_artist: ArtistType = strawchemy.create(ArtistCreateInputType)
    create_artists : list[ArtistType] = strawchemy.create(ArtistCreateInputType)

    # Upsert Artist mutation
    # This mutation allows inserting a new artist or updating an existing one based on conflict fields.
    # It uses ArtistCreateInputType for the input structure and ArtistUpsertConflictFieldsType to define the fields to check for conflicts.
    # ArtistUpsertUpdateFieldsType defines the fields to update if a conflict is found.
    # The upsert_artist field returns a single ArtistType, while upsert_artists returns a list of ArtistType.
    # This is useful for ensuring data consistency and avoiding duplicates.
    upsert_artist: ArtistType = strawchemy.upsert(ArtistCreateInputType, conflict_fields=ArtistUpsertConflictFieldsType, update_fields=ArtistUpsertUpdateFieldsType)
    upsert_artists: list[ArtistType] = strawchemy.upsert(ArtistCreateInputType, conflict_fields=ArtistUpsertConflictFieldsType, update_fields=ArtistUpsertUpdateFieldsType)
    # Update Artist mutation
    # This mutation allows updating existing artists. There are two versions:
    # update_artist_by_id updates a single artist by their ID, using ArtistUpdateInputType for the input structure.
    # update_artists updates multiple artists based on a filter, using ArtistFilterUpdateInputType for the update data and ArtistFilterType for the filter criteria.
    # update_artist_by_id returns a single ArtistType, while update_artists returns a list of ArtistType.
    # This is useful for modifying artist details or applying batch updates based on specific conditions.
    update_artist_by_id: ArtistType = strawchemy.update_by_ids(ArtistUpdateInputType)
    update_artists : list[ArtistType] = strawchemy.update(ArtistFilterUpdateInputType, ArtistFilterType)


    # Create Album mutation
    # Similar to the artist creation, this mutation allows for creating a single album or multiple albums
    # It uses AlbumCreateInputType for the input structure.
    # The create_album field returns a single AlbumType, while create_albums returns a list of AlbumType.
    # This is useful for batch operations where you might want to create multiple albums
    # in one go.
    create_album: AlbumType = strawchemy.create(AlbumCreateInputType)
    create_albums: list[AlbumType] = strawchemy.create(AlbumCreateInputType)
    update_album_by_id: AlbumType = strawchemy.update_by_ids(AlbumUpdateInputType)
    update_albums: list[AlbumType] = strawchemy.update(AlbumFilterUpdateInputType, AlbumFilterType)
    upsert_album: AlbumType = strawchemy.upsert(AlbumCreateInputType, conflict_fields=AlbumUpsertConflictFieldsType, update_fields=AlbumUpsertUpdateFieldsType)
    upsert_albums: list[AlbumType] = strawchemy.upsert(AlbumCreateInputType, conflict_fields=AlbumUpsertConflictFieldsType, update_fields=AlbumUpsertUpdateFieldsType)
    # Create Track mutation
    # This mutation allows creating a single track or multiple tracks at once.
    # It uses TrackCreateInputType to define the input structure.
    # The create_track field returns a single TrackType, while create_tracks returns a list of TrackType.
    # This is useful for batch operations where you might want to create multiple tracks in one go.
    create_track: TrackType = strawchemy.create(TrackCreateInputType)
    create_tracks: list[TrackType] = strawchemy.create(TrackCreateInputType)
    update_track_by_id: TrackType = strawchemy.update_by_ids(TrackUpdateInputType)
    update_tracks: list[TrackType] = strawchemy.update(TrackFilterUpdateInputType, AlbumFilterType)  
    upsert_track: TrackType = strawchemy.upsert(TrackCreateInputType, conflict_fields=TrackUpsertConflictFieldsType, update_fields=TrackUpsertUpdateFieldsType)
    # Additional mutations can be added here as needed

