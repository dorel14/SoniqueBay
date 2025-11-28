from __future__ import annotations
import strawberry
from .artist_mutations import ArtistMutations
from .album_mutations import AlbumMutations
from .track_mutations import TrackMutations


@strawberry.type
class Mutation(ArtistMutations, AlbumMutations, TrackMutations):
    """Main mutation class combining all entity mutations."""
    pass


__all__ = ["Mutation", "ArtistMutations", "AlbumMutations", "TrackMutations"]