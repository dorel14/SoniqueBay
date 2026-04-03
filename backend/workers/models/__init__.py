"""
Modèles SQLAlchemy autonomes pour backend_worker.

Ces modèles sont copiés depuis backend/api/models pour permettre
l'utilisation de SQLAlchemy async dans les workers Celery sans dépendance
au conteneur backend (architecture microservices Docker).
"""

from backend.workers.models.agent_model import AgentModel
from backend.workers.models.albums_model import Album
from backend.workers.models.artist_embeddings_model import ArtistEmbedding, GMMModel
from backend.workers.models.artist_similar_model import ArtistSimilar
from backend.workers.models.artists_model import Artist
from backend.workers.models.base import Base, TimestampMixin
from backend.workers.models.chat_models import (
    ChatMessage,
    ChatSession,
    Conversation,
    ConversationSummary,
)
from backend.workers.models.covers_model import Cover, EntityCoverType
from backend.workers.models.genres_model import Genre, album_genres, artist_genres
from backend.workers.models.scan_sessions_model import ScanSession
from backend.workers.models.settings_model import Setting
from backend.workers.models.tags_model import (
    GenreTag,
    MoodTag,
    track_genre_tags,
    track_mood_tags,
)
from backend.workers.models.track_embeddings_model import TrackEmbeddings
from backend.workers.models.track_mir_normalized_model import TrackMIRNormalized
from backend.workers.models.track_mir_raw_model import TrackMIRRaw
from backend.workers.models.track_mir_scores_model import TrackMIRScores
from backend.workers.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags
from backend.workers.models.tracks_model import Track
from backend.workers.models.user_model import User

__all__ = [
    'Base',
    'TimestampMixin',
    'Cover',
    'EntityCoverType',
    'Genre',
    'artist_genres',
    'album_genres',
    'Artist',
    'Album',
    'Track',
    'GenreTag',
    'MoodTag',
    'track_genre_tags',
    'track_mood_tags',
    'Setting',
    'ScanSession',
    'ArtistEmbedding',
    'GMMModel',
    'ArtistSimilar',
    'AgentModel',
    'TrackMIRRaw',
    'TrackMIRNormalized',
    'TrackMIRScores',
    'TrackMIRSyntheticTags',
    'TrackEmbeddings',
    'Conversation',
    'ChatMessage',
    'ChatSession',
    'ConversationSummary',
    'User',
]
