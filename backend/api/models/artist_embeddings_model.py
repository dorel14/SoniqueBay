# -*- coding: UTF-8 -*-
"""
Artist Embeddings Model

SQLAlchemy models for artist vector embeddings and GMM clustering.
"""

from __future__ import annotations
from sqlalchemy import String, Integer, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.api.utils.database import Base, TimestampMixin


class ArtistEmbedding(Base, TimestampMixin):
    """Model for storing artist vector embeddings."""

    __tablename__ = 'artist_embeddings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    vector: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string of vector
    cluster: Mapped[int] = mapped_column(Integer, nullable=True)
    cluster_probabilities: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string of probabilities


class GMMModel(Base, TimestampMixin):
    """Model for storing trained Gaussian Mixture Models."""

    __tablename__ = 'gmm_models'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    n_components: Mapped[int] = mapped_column(Integer, nullable=False)
    convergence_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    n_features: Mapped[int] = mapped_column(Integer, nullable=False)
    log_likelihood: Mapped[float] = mapped_column(Float, nullable=True)
    model_weights: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    model_means: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    model_covariances: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)