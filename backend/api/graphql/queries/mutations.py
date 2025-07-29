from __future__ import annotations
import strawberry
from ..strawchemy_init import strawchemy
from ..types.artist_type import ArtistCreateInput, ArtistGQL
#from ..types.albums_type import AlbumCreateInput, AlbumGQL
#from ..types.tracks_type import TrackCreateInput, TrackGQL

@strawberry.type
class Mutation:
    create_artist: ArtistGQL = strawchemy.create(ArtistCreateInput)
    create_artists : list[ArtistGQL] = strawchemy.create(ArtistCreateInput)


    #create_album: AlbumGQL = strawchemy.create(AlbumCreateInput)
    #create_albums: list[AlbumGQL] = strawchemy.create(AlbumCreateInput)
    #create_track: TrackGQL = strawchemy.create(TrackCreateInput)
    #create_tracks: list[TrackGQL] = strawchemy.create(TrackCreateInput)
    
    # Additional mutations can be added here as needed
    # For example, update_artist, delete_artist, etc.