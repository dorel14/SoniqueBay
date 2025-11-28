# -*- coding: UTF-8 -*-
"""
Artist GMM Worker Package

Workers for training Gaussian Mixture Models on artist embeddings
and managing artist similarity recommendations.
"""

from .artist_gmm_worker import (
    train_artist_gmm,
    generate_artist_embeddings,
    update_artist_clusters
)

__all__ = [
    "train_artist_gmm",
    "generate_artist_embeddings",
    "update_artist_clusters"
]