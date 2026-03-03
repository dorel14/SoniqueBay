"""
Schémas Pydantic pour la validation des données
"""
from typing import TYPE_CHECKING

from backend.api.schemas.agent_score_schema import (
    AgentScore,
    AgentScoreBase,
    AgentScoreCreate,
    AgentScoreListResponse,
    AgentScoreUpdate,
    AgentScoreWithMetrics,
)

# Imports des schémas
from backend.api.schemas.albums_schema import (
    Album,
    AlbumBase,
    AlbumCreate,
    AlbumWithRelations,
)
from backend.api.schemas.artist_embeddings_schema import (
    ArtistEmbeddingCreate,
    ArtistEmbeddingUpdate,
    ArtistSimilarityRecommendation,
    GMMTrainingRequest,
    GMMTrainingResponse,
)
from backend.api.schemas.artists_schema import (
    Artist,
    ArtistBase,
    ArtistCreate,
    ArtistWithRelations,
)
from backend.api.schemas.genres_schema import (
    Genre,
    GenreBase,
    GenreCreate,
    GenreWithTracks,
)
from backend.api.schemas.gmm_schema import (
    ClusteringTaskResponse,
    ClusterResponse,
    ClusterStatusResponse,
    RefreshClustersResponse,
    SimilarArtistsResponse,
)
from backend.api.schemas.mir_schema import (
    MIRNormalizedPayload,
    MIRNormalizedResponse,
    MIRRawPayload,
    MIRRawResponse,
    MIRScoresPayload,
    MIRScoresResponse,
    MIRStoragePayload,
    MIRStorageResponse,
    MIRSummaryResponse,
    SyntheticTagPayload,
    SyntheticTagResponse,
)
from backend.api.schemas.scan_schema import ScanRequest
from backend.api.schemas.search_schema import SearchQuery, SearchResult
from backend.api.schemas.settings_schema import Setting, SettingBase, SettingCreate
from backend.api.schemas.synonyms_schema import (
    DeleteResponse,
    GenerateRequest,
    SearchResponse,
    SearchResultItem,
    SynonymRequest,
    SynonymResponse,
    TriggerTaskResponse,
)
from backend.api.schemas.track_audio_features_schema import (
    TrackAudioFeatures,
    TrackAudioFeaturesBase,
    TrackAudioFeaturesCompact,
    TrackAudioFeaturesCreate,
    TrackAudioFeaturesUpdate,
    TrackAudioFeaturesWithTrack,
)
from backend.api.schemas.track_embeddings_schema import (
    EmbeddingBatchRequest,
    EmbeddingBatchResponse,
    TrackEmbeddings,
    TrackEmbeddingsBase,
    TrackEmbeddingsCreate,
    TrackEmbeddingsUpdate,
    TrackEmbeddingsVectorOnly,
    TrackEmbeddingsWithTrack,
    TrackEmbeddingsWithVector,
    TrackSimilarityResult,
)
from backend.api.schemas.track_metadata_schema import (
    CommonMetadataKeys,
    TrackMetadata,
    TrackMetadataBase,
    TrackMetadataBatchCreate,
    TrackMetadataBatchResponse,
    TrackMetadataByKey,
    TrackMetadataBySource,
    TrackMetadataCompact,
    TrackMetadataCreate,
    TrackMetadataFilter,
    TrackMetadataStats,
    TrackMetadataUpdate,
    TrackMetadataWithTrack,
)
from backend.api.schemas.track_vectors_schema import (
    TrackVectorCreate,
    TrackVectorResponse,
)
from backend.api.schemas.tracks_schema import (
    Track,
    TrackBase,
    TrackCreate,
    TrackWithRelations,
)

from .base_schema import BaseSchema

if TYPE_CHECKING:
    from backend.api.schemas.albums_schema import Album
    from backend.api.schemas.artists_schema import Artist
    from backend.api.schemas.genres_schema import Genre
    from backend.api.schemas.settings_schema import Setting
    from backend.api.schemas.tracks_schema import Track

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
    # GMM schemas
    'ClusterResponse', 'SimilarArtistsResponse', 'ClusterStatusResponse',
    'ClusteringTaskResponse', 'RefreshClustersResponse',
    # MIR schemas
    'MIRRawPayload', 'MIRNormalizedPayload', 'MIRScoresPayload',
    'SyntheticTagPayload', 'MIRStoragePayload', 'MIRStorageResponse',
    'MIRSummaryResponse', 'MIRRawResponse', 'MIRNormalizedResponse',
    'MIRScoresResponse', 'SyntheticTagResponse',
    # Synonyms schemas
    'SynonymRequest', 'SynonymResponse', 'SearchResultItem',
    'SearchResponse', 'TriggerTaskResponse', 'DeleteResponse', 'GenerateRequest',
]