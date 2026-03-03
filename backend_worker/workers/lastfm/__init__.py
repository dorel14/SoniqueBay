# -*- coding: UTF-8 -*-
"""
Last.fm Worker Package

Workers for fetching artist information from Last.fm API.
"""

from .lastfm_worker import (
    batch_fetch_lastfm_info,
    fetch_artist_lastfm_info,
    fetch_similar_artists,
)

__all__ = [
    "fetch_artist_lastfm_info",
    "fetch_similar_artists",
    "batch_fetch_lastfm_info"
]