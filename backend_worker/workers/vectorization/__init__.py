# -*- coding: UTF-8 -*-
"""
Vectorization Workers Package

Workers for generating embeddings from tracks and artists.
"""

from .track_vectorization_worker import (
    vectorize_tracks,
    vectorize_artist_tracks
)

__all__ = [
    "vectorize_tracks",
    "vectorize_artist_tracks"
]