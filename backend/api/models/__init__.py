# Import all models to resolve circular dependencies
from backend.api.models import *  # noqa: F403
from backend.api.models.agent_model import AgentModel as AgentModel
from backend.api.models.albums_model import Album as Album
from backend.api.models.artist_embeddings_model import GMMModel as GMMModel
from backend.api.models.artist_similar_model import ArtistSimilar as ArtistSimilar
from backend.api.models.artists_model import Artist as Artist
from backend.api.models.covers_model import Cover as Cover
from backend.api.models.covers_model import EntityCoverType as EntityCoverType
from backend.api.models.genres_model import Genre as Genre
from backend.api.models.genres_model import album_genres as album_genres
from backend.api.models.genres_model import artist_genres as artist_genres
from backend.api.models.scan_sessions_model import ScanSession as ScanSession
from backend.api.models.tracks_model import Track as Track
from backend.api.models.artist_embeddings_model import ArtistEmbedding
from backend.api.models.track_mir_raw_model import TrackMIRRaw as TrackMIRRaw
from backend.api.models.track_mir_normalized_model import TrackMIRNormalized as TrackMIRNormalized
from backend.api.models.track_mir_scores_model import TrackMIRScores as TrackMIRScores
from backend.api.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags as TrackMIRSyntheticTags

# Import all models to resolve circular dependencies
from backend.api.models import *  # noqa: F403
