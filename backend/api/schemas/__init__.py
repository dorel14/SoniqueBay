"""
Schémas Pydantic pour la validation des données
"""
from .base_schema import BaseSchema
from typing import TYPE_CHECKING

# Imports des schémas
from backend.api.schemas.albums_schema import AlbumBase, AlbumCreate, Album, AlbumWithRelations
from backend.api.schemas.artists_schema import ArtistBase, ArtistCreate, Artist, ArtistWithRelations
from backend.api.schemas.genres_schema import GenreBase, GenreCreate, Genre, GenreWithTracks
from backend.api.schemas.tracks_schema import TrackBase, TrackCreate, Track, TrackWithRelations
from backend.api.schemas.settings_schema import SettingBase, SettingCreate, Setting
from backend.api.schemas.search_schema import SearchResult, SearchQuery
from backend.api.schemas.scan_schema import ScanRequest
from backend.api.schemas.agent_score_schema import (
    AgentScoreBase,
    AgentScoreCreate,
    AgentScoreUpdate,
    AgentScore,
    AgentScoreWithMetrics,
    AgentScoreListResponse
)
from backend.api.schemas.track_vectors_schema import TrackVectorCreate, TrackVectorResponse
from backend.api.schemas.artist_embeddings_schema import (
    ArtistEmbeddingCreate,
    ArtistEmbeddingUpdate,
    GMMTrainingRequest,
    GMMTrainingResponse,
    ArtistSimilarityRecommendation
)
from backend.api.schemas.track_audio_features_schema import (
    TrackAudioFeaturesBase,
    TrackAudioFeaturesCreate,
    TrackAudioFeaturesUpdate,
    TrackAudioFeatures,
    TrackAudioFeaturesWithTrack,
    TrackAudioFeaturesCompact,
)
from backend.api.schemas.track_embeddings_schema import (
    TrackEmbeddingsBase,
    TrackEmbeddingsCreate,
    TrackEmbeddingsUpdate,
    TrackEmbeddings,
    TrackEmbeddingsWithVector,
    TrackEmbeddingsWithTrack,
    TrackEmbeddingsVectorOnly,
    TrackSimilarityResult,
    EmbeddingBatchRequest,
    EmbeddingBatchResponse,
)
from backend.api.schemas.track_metadata_schema import (
    TrackMetadataBase,
    TrackMetadataCreate,
    TrackMetadataUpdate,
    TrackMetadata,
    TrackMetadataWithTrack,
    TrackMetadataCompact,
    TrackMetadataByKey,
    TrackMetadataBySource,
    TrackMetadataBatchCreate,
    TrackMetadataBatchResponse,
    TrackMetadataFilter,
    TrackMetadataStats,
    CommonMetadataKeys,
)

if TYPE_CHECKING:
    from backend.api.schemas.albums_schema import Album
    from backend.api.schemas.artists_schema import Artist
    from backend.api.schemas.genres_schema import Genre
    from backend.api.schemas.tracks_schema import Track
    from backend.api.schemas.settings_schema import Setting

__all__ = [
    'BaseSchema',
    'AlbumBase', 'AlbumCreate', 'Album', 'AlbumWithRelations',
    'ArtistBase', 'ArtistCreate', 'Artist', 'ArtistWithRelations',
    'GenreBase', 'GenreCreate', 'Genre', 'GenreWithTracks',
    'TrackBase', 'TrackCreate', 'Track', 'TrackWithRelations',
    'SearchResult', 'SearchQuery',
    'SettingBase', 'SettingCreate', 'Setting',
    'ScanRequest',
    'AgentScoreBase', 'AgentScoreCreate', 'AgentScoreUpdate', 'AgentScore', 'AgentScoreWithMetrics', 'AgentScoreListResponse',
    'TrackVectorCreate', 'TrackVectorResponse',
    'ArtistEmbeddingCreate', 'ArtistEmbeddingUpdate', 'GMMTrainingRequest', 'GMMTrainingResponse', 'ArtistSimilarityRecommendation',
    # TrackAudioFeatures schemas
    'TrackAudioFeaturesBase', 'TrackAudioFeaturesCreate', 'TrackAudioFeaturesUpdate',
    'TrackAudioFeatures', 'TrackAudioFeaturesWithTrack', 'TrackAudioFeaturesCompact',
    # TrackEmbeddings schemas
    'TrackEmbeddingsBase', 'TrackEmbeddingsCreate', 'TrackEmbeddingsUpdate',
    'TrackEmbeddings', 'TrackEmbeddingsWithVector', 'TrackEmbeddingsWithTrack',
    'TrackEmbeddingsVectorOnly', 'TrackSimilarityResult',
    'EmbeddingBatchRequest', 'EmbeddingBatchResponse',
    # TrackMetadata schemas
    'TrackMetadataBase', 'TrackMetadataCreate', 'TrackMetadataUpdate',
    'TrackMetadata', 'TrackMetadataWithTrack', 'TrackMetadataCompact',
    'TrackMetadataByKey', 'TrackMetadataBySource',
    'TrackMetadataBatchCreate', 'TrackMetadataBatchResponse',
    'TrackMetadataFilter', 'TrackMetadataStats', 'CommonMetadataKeys',
]