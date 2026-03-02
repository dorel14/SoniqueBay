"""
Modèles SQLAlchemy autonomes pour backend_worker.

Ces modèles sont copiés depuis backend/api/models pour permettre
l'utilisation de SQLAlchemy async dans les workers Celery sans dépendance
au conteneur backend (architecture microservices Docker).
"""

from backend_worker.models.base import Base, TimestampMixin
from backend_worker.models.covers_model import Cover, EntityCoverType
from backend_worker.models.genres_model import Genre, artist_genres, album_genres
from backend_worker.models.artists_model import Artist
from backend_worker.models.albums_model import Album
from backend_worker.models.tracks_model import Track, GenreTag, MoodTag, track_genre_tags, track_mood_tags
from backend_worker.models.settings_model import Setting
from backend_worker.models.scan_sessions_model import ScanSession
from backend_worker.models.artist_embeddings_model import ArtistEmbedding, GMMModel
from backend_worker.models.artist_similar_model import ArtistSimilar
from backend_worker.models.agent_model import AgentModel
from backend_worker.models.track_mir_raw_model import TrackMIRRaw
from backend_worker.models.track_mir_normalized_model import TrackMIRNormalized
from backend_worker.models.track_mir_scores_model import TrackMIRScores
from backend_worker.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags
from backend_worker.models.track_embeddings_model import TrackEmbeddings
from backend_worker.models.chat_models import Conversation, ChatMessage, ChatSession, ConversationSummary
from backend_worker.models.user_model import User
from backend_worker.models.conversation_model import Conversation as OldConversation  # Compat

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
