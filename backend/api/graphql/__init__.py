# -*- coding: utf-8 -*-
"""
Module GraphQL pour l'API SoniqueBay.

Rôle:
    Regroupe tous les types, queries et mutations GraphQL disponibles
    dans l'API. Point d'entrée unique pour l'interface GraphQL.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.graphql.types: Types GraphQL
    - backend.api.graphql.queries: Queries GraphQL
    - backend.api.graphql.mutations: Mutations GraphQL

Auteur: SoniqueBay Team
"""

# Types
# Mutations
from backend.api.graphql.mutations import (
    TrackAudioFeaturesMutation,
    TrackEmbeddingsMutation,
    TrackMetadataMutation,
)

# Queries
from backend.api.graphql.queries import (
    TrackAudioFeaturesQuery,
    TrackEmbeddingsQuery,
    TrackMetadataQuery,
)
from backend.api.graphql.types import (
    AlbumCreateInput,
    # Types de base
    AlbumType,
    AlbumUpdateInput,
    ArtistCreateInput,
    ArtistType,
    ArtistUpdateInput,
    CoverType,
    GenreTagType,
    GenreType,
    MetadataKeyStatistics,
    MetadataSourceStatistics,
    MoodTagType,
    SimilarTrackResult,
    TrackAudioFeaturesInput,
    TrackAudioFeaturesSearchInput,
    # Track Audio Features
    TrackAudioFeaturesType,
    TrackAudioFeaturesUpdateInput,
    TrackCreateInput,
    TrackEmbeddingsInput,
    TrackEmbeddingsSearchInput,
    TrackEmbeddingsSimilarityInput,
    # Track Embeddings
    TrackEmbeddingsType,
    TrackEmbeddingsUpdateInput,
    TrackMetadataBatchInput,
    TrackMetadataBatchResult,
    TrackMetadataDeleteInput,
    TrackMetadataInput,
    TrackMetadataSearchInput,
    TrackMetadataStatistics,
    # Track Metadata
    TrackMetadataType,
    TrackMetadataUpdateInput,
    TrackType,
    TrackUpdateInput,
    TrackVectorType,
)

__all__ = [
    # Types de base
    "AlbumType",
    "AlbumCreateInput",
    "AlbumUpdateInput",
    "ArtistType",
    "ArtistCreateInput",
    "ArtistUpdateInput",
    "CoverType",
    "GenreType",
    "GenreTagType",
    "MoodTagType",
    "TrackType",
    "TrackCreateInput",
    "TrackUpdateInput",
    "TrackVectorType",
    # Track Audio Features Types
    "TrackAudioFeaturesType",
    "TrackAudioFeaturesInput",
    "TrackAudioFeaturesUpdateInput",
    "TrackAudioFeaturesSearchInput",
    # Track Embeddings Types
    "TrackEmbeddingsType",
    "SimilarTrackResult",
    "TrackEmbeddingsInput",
    "TrackEmbeddingsUpdateInput",
    "TrackEmbeddingsSearchInput",
    "TrackEmbeddingsSimilarityInput",
    # Track Metadata Types
    "TrackMetadataType",
    "TrackMetadataBatchResult",
    "MetadataKeyStatistics",
    "MetadataSourceStatistics",
    "TrackMetadataStatistics",
    "TrackMetadataInput",
    "TrackMetadataUpdateInput",
    "TrackMetadataBatchInput",
    "TrackMetadataSearchInput",
    "TrackMetadataDeleteInput",
    # Queries
    "TrackAudioFeaturesQuery",
    "TrackEmbeddingsQuery",
    "TrackMetadataQuery",
    # Mutations
    "TrackAudioFeaturesMutation",
    "TrackEmbeddingsMutation",
    "TrackMetadataMutation",
]
