# -*- coding: utf-8 -*-
"""
Queries GraphQL pour l'API SoniqueBay.

Rôle:
    Regroupe toutes les queries GraphQL disponibles dans l'API.

Auteur: SoniqueBay Team
"""

from .track_audio_features_queries import TrackAudioFeaturesQuery
from .track_embeddings_queries import TrackEmbeddingsQuery
from .track_metadata_queries import TrackMetadataQuery
from .track_mir_queries import TrackMIRQuery

__all__ = [
    "TrackAudioFeaturesQuery",
    "TrackEmbeddingsQuery",
    "TrackMetadataQuery",
    "TrackMIRQuery",
]
