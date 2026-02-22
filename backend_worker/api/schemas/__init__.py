"""
Schemas Pydantic pour l'API backend_worker.
"""
from .embedding_schema import EmbeddingRequest, EmbeddingResponse

__all__ = ["EmbeddingRequest", "EmbeddingResponse"]
