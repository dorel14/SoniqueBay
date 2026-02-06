# -*- coding: utf-8 -*-
"""
Mutations GraphQL pour l'API SoniqueBay.

Rôle:
    Regroupe toutes les mutations GraphQL disponibles dans l'API.

Auteur: SoniqueBay Team
"""

from .track_audio_features_mutations import TrackAudioFeaturesMutation
from .track_embeddings_mutations import TrackEmbeddingsMutation
from .track_metadata_mutations import TrackMetadataMutation
from .track_mir_mutations import TrackMIRMutation

__all__ = [
    "TrackAudioFeaturesMutation",
    "TrackEmbeddingsMutation",
    "TrackMetadataMutation",
    "TrackMIRMutation",
]
