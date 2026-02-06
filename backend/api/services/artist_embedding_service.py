# -*- coding: UTF-8 -*-
"""
Artist Embedding Service

Service for managing artist vector embeddings and Gaussian Mixture Model clustering.
Provides functionality for artist similarity and recommendation algorithms.
Uses TrackEmbeddings for track-level embeddings.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.artist_embeddings_model import (ArtistEmbedding,
                                                        GMMModel)
from backend.api.schemas.artist_embeddings_schema import (
    ArtistEmbeddingCreate, ArtistEmbeddingUpdate,
    ArtistSimilarityRecommendation, GMMTrainingRequest, GMMTrainingResponse)
from backend.api.services.vector_search_service import VectorSearchService
from backend.api.utils.logging import logger

# ML libraries - imported conditionally as they may not be available in all environments
try:
    import numpy as np
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries (numpy, sklearn) not available. GMM training will be disabled.")


class ArtistEmbeddingService:
    """Service for artist embeddings and GMM clustering."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_search = VectorSearchService(db)

    async def create_embedding(self, embedding_data: ArtistEmbeddingCreate) -> ArtistEmbedding:
        """Create a new artist embedding with vector search support."""
        try:
            # Store embedding in sqlite-vec for fast similarity search
            vector_success = await self.vector_search.add_artist_embedding(
                embedding_data.artist_name,
                embedding_data.vector
            )

            if not vector_success:
                logger.warning(f"Failed to store vector for artist: {embedding_data.artist_name}")

            # Store metadata in relational database
            cluster_probs_json = json.dumps(embedding_data.cluster_probabilities) if embedding_data.cluster_probabilities else None

            embedding = ArtistEmbedding(
                artist_name=embedding_data.artist_name,
                vector=json.dumps(embedding_data.vector),  # Keep JSON copy for compatibility
                cluster=embedding_data.cluster,
                cluster_probabilities=cluster_probs_json
            )

            self.db.add(embedding)
            await self.db.commit()
            await self.db.refresh(embedding)

            logger.info(f"Created embedding for artist: {embedding.artist_name}")
            return embedding

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating embedding for {embedding_data.artist_name}: {e}")
            raise

    async def get_embedding_by_artist(self, artist_name: str) -> Optional[ArtistEmbedding]:
        """Get embedding by artist name."""
        result = await self.db.execute(
            select(ArtistEmbedding).where(ArtistEmbedding.artist_name == artist_name)
        )
        return result.scalars().first()

    async def update_embedding(self, artist_name: str, update_data: ArtistEmbeddingUpdate) -> Optional[ArtistEmbedding]:
        """Update an existing artist embedding."""
        try:
            embedding = await self.get_embedding_by_artist(artist_name)
            if not embedding:
                return None

            if update_data.vector is not None:
                embedding.vector = json.dumps(update_data.vector)

            if update_data.cluster is not None:
                embedding.cluster = update_data.cluster

            if update_data.cluster_probabilities is not None:
                embedding.cluster_probabilities = json.dumps(update_data.cluster_probabilities)

            await self.db.commit()
            await self.db.refresh(embedding)

            logger.info(f"Updated embedding for artist: {artist_name}")
            return embedding

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating embedding for {artist_name}: {e}")
            raise

    async def get_all_embeddings(self, skip: int = 0, limit: int = 100) -> List[ArtistEmbedding]:
        """Get all artist embeddings with pagination."""
        result = await self.db.execute(
            select(ArtistEmbedding).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_embeddings_by_cluster(self, cluster: int) -> List[ArtistEmbedding]:
        """Get all embeddings for a specific cluster."""
        result = await self.db.execute(
            select(ArtistEmbedding).where(ArtistEmbedding.cluster == cluster)
        )
        return result.scalars().all()

    async def delete_embedding(self, artist_name: str) -> bool:
        """Delete an artist embedding."""
        try:
            embedding = await self.get_embedding_by_artist(artist_name)
            if not embedding:
                return False

            await self.db.delete(embedding)
            await self.db.commit()

            logger.info(f"Deleted embedding for artist: {artist_name}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting embedding for {artist_name}: {e}")
            raise

    async def train_gmm(self, request: GMMTrainingRequest) -> GMMTrainingResponse:
        """Train a Gaussian Mixture Model on artist embeddings."""
        if not ML_AVAILABLE:
            return GMMTrainingResponse(
                success=False,
                n_components=request.n_components,
                n_artists=0,
                log_likelihood=None,
                training_time=0,
                message="ML libraries not available"
            )

        start_time = datetime.utcnow()

        try:
            # Get all embeddings
            embeddings = await self.get_all_embeddings(limit=10000)  # Reasonable limit
            if len(embeddings) < request.n_components:
                raise ValueError(f"Not enough embeddings ({len(embeddings)}) for {request.n_components} components")

            # Extract vectors
            vectors = []
            artist_names = []
            for emb in embeddings:
                try:
                    vector = json.loads(emb.vector)
                    vectors.append(vector)
                    artist_names.append(emb.artist_name)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Skipping invalid vector for artist: {emb.artist_name}")
                    continue

            if len(vectors) < request.n_components:
                raise ValueError(f"Not enough valid vectors ({len(vectors)}) for {request.n_components} components")

            # Run ML operations in thread pool to avoid blocking
            def _train_gmm_model():
                import numpy as np
                from sklearn.mixture import GaussianMixture
                from sklearn.preprocessing import StandardScaler

                # Convert to numpy array
                X = np.array(vectors)

                # Standardize features
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)

                # Train GMM
                gmm = GaussianMixture(
                    n_components=request.n_components,
                    max_iter=request.max_iterations,
                    tol=request.convergence_threshold,
                    random_state=42
                )

                gmm.fit(X_scaled)

                # Get cluster assignments and probabilities
                clusters = gmm.predict(X_scaled)
                probabilities = gmm.predict_proba(X_scaled)

                return gmm, X_scaled, clusters, probabilities, scaler

            # Run training in thread pool
            gmm, X_scaled, clusters, probabilities, scaler = await asyncio.to_thread(_train_gmm_model)

            # Update embeddings with cluster information
            for i, (artist_name, cluster, probs) in enumerate(zip(artist_names, clusters, probabilities)):
                cluster_probs = {j: float(probs[j]) for j in range(request.n_components)}

                update_data = ArtistEmbeddingUpdate(
                    cluster=int(cluster),
                    cluster_probabilities=cluster_probs
                )
                await self.update_embedding(artist_name, update_data)

            # Save GMM model
            await self._save_gmm_model(gmm, request, X_scaled)

            training_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"GMM training completed: {request.n_components} components, {len(vectors)} artists")

            return GMMTrainingResponse(
                success=True,
                n_components=request.n_components,
                n_artists=len(vectors),
                log_likelihood=float(gmm.score(X_scaled)),
                training_time=training_time,
                message=f"Successfully trained GMM with {request.n_components} components on {len(vectors)} artists"
            )

        except Exception as e:
            training_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"GMM training failed: {e}")

            return GMMTrainingResponse(
                success=False,
                n_components=request.n_components,
                n_artists=0,
                log_likelihood=None,
                training_time=training_time,
                message=f"GMM training failed: {str(e)}"
            )

    async def _save_gmm_model(self, gmm, request: GMMTrainingRequest, X_scaled):
        """Save GMM model parameters to database."""
        try:
            # Deactivate previous models
            await self.db.execute(
                GMMModel.update().values(is_active=False)
            )

            # Save new model
            model = GMMModel(
                n_components=request.n_components,
                convergence_threshold=request.convergence_threshold,
                max_iterations=request.max_iterations,
                n_features=gmm.n_features_in_,
                log_likelihood=float(gmm.score(X_scaled)),
                model_weights=json.dumps(gmm.weights_.tolist()),
                model_means=json.dumps(gmm.means_.tolist()),
                model_covariances=json.dumps(gmm.covariances_.tolist()),
                is_active=True
            )

            self.db.add(model)
            await self.db.commit()

            logger.info(f"Saved GMM model with {request.n_components} components")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving GMM model: {e}")
            raise

    async def get_similar_artists(self, artist_name: str, limit: int = 10) -> ArtistSimilarityRecommendation:
        """Get similar artists based on GMM clustering."""
        try:
            # Get the artist's embedding
            embedding = await self.get_embedding_by_artist(artist_name)
            if not embedding:
                return ArtistSimilarityRecommendation(
                    artist_name=artist_name,
                    similar_artists=[],
                    cluster_based=False
                )

            # Get all artists in the same cluster
            cluster_artists = await self.get_embeddings_by_cluster(embedding.cluster)

            # Calculate similarities based on cluster probabilities
            similar_artists = []
            source_probs = json.loads(embedding.cluster_probabilities) if embedding.cluster_probabilities else {}

            for other_embedding in cluster_artists:
                if other_embedding.artist_name == artist_name:
                    continue

                other_probs = json.loads(other_embedding.cluster_probabilities) if other_embedding.cluster_probabilities else {}

                # Calculate similarity score based on probability distributions
                score = self._calculate_similarity_score(source_probs, other_probs)

                similar_artists.append({
                    "artist_name": other_embedding.artist_name,
                    "cluster": other_embedding.cluster,
                    "similarity_score": score
                })

            # Sort by similarity score and limit results
            similar_artists.sort(key=lambda x: x["similarity_score"], reverse=True)
            similar_artists = similar_artists[:limit]

            return ArtistSimilarityRecommendation(
                artist_name=artist_name,
                similar_artists=similar_artists,
                cluster_based=True
            )

        except Exception as e:
            logger.error(f"Error getting similar artists for {artist_name}: {e}")
            return ArtistSimilarityRecommendation(
                artist_name=artist_name,
                similar_artists=[],
                cluster_based=False
            )

    def _calculate_similarity_score(self, probs1: Dict[int, float], probs2: Dict[int, float]) -> float:
        """Calculate similarity score between two probability distributions."""
        try:
            # Use Jensen-Shannon divergence or simple dot product
            common_clusters = set(probs1.keys()) & set(probs2.keys())

            if not common_clusters:
                return 0.0

            # Simple dot product similarity
            score = sum(probs1.get(c, 0.0) * probs2.get(c, 0.0) for c in common_clusters)

            # Normalize by maximum possible score
            max_score = sum(max(probs1.get(c, 0.0), probs2.get(c, 0.0)) for c in common_clusters)
            return score / max_score if max_score > 0 else 0.0

        except Exception:
            return 0.0

    async def generate_artist_embeddings(self, artist_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate embeddings for artists by aggregating their tracks' embeddings.

        This method calculates artist embeddings as the centroid (mean) of all
        track embeddings for each artist, which is the standard approach used
        by music recommendation systems like Spotify, Last.fm, etc.

        Uses TrackEmbeddingsService to get track embeddings.

        Args:
            artist_names: List of artist names to process (None = all artists)

        Returns:
            Generation results
        """
        try:
            logger.info("[ARTIST EMBEDDING] Starting artist embedding generation from tracks")

            # Import Track model from library_api
            from backend.api.models.artists_model import \
                Artist as LibraryArtist

            # Get artists to process
            if artist_names:
                result = await self.db.execute(
                    select(LibraryArtist).where(LibraryArtist.name.in_(artist_names))
                )
                artists = result.scalars().all()
            else:
                result = await self.db.execute(select(LibraryArtist))
                artists = result.scalars().all()

            generated_count = 0
            skipped_count = 0

            for artist in artists:
                try:
                    # Check if embedding already exists
                    existing = await self.get_embedding_by_artist(artist.name)
                    if existing:
                        skipped_count += 1
                        continue

                    # Generate embedding by aggregating track embeddings
                    embedding_vector = await self._aggregate_track_embeddings_new(artist)

                    if embedding_vector:
                        from backend.api.schemas.artist_embeddings_schema import \
                            ArtistEmbeddingCreate
                        embedding_data = ArtistEmbeddingCreate(
                            artist_name=artist.name,
                            vector=embedding_vector,
                            cluster=None,
                            cluster_probabilities=None
                        )

                        await self.create_embedding(embedding_data)
                        generated_count += 1

                        # Progress logging
                        if generated_count % 10 == 0:
                            logger.info(f"[ARTIST EMBEDDING] Generated {generated_count} embeddings...")

                except Exception as e:
                    logger.error(f"[ARTIST EMBEDDING] Error processing artist {artist.name}: {e}")
                    continue

            logger.info(f"[ARTIST EMBEDDING] Generation completed: {generated_count} generated, {skipped_count} skipped")

            return {
                "success": True,
                "generated": generated_count,
                "skipped": skipped_count,
                "total_processed": generated_count + skipped_count
            }

        except Exception as e:
            logger.error(f"[ARTIST EMBEDDING] Generation failed: {e}")
            raise

    async def _aggregate_track_embeddings_new(self, artist) -> Optional[List[float]]:
        """
        Aggregate track embeddings from TrackEmbeddings table to create artist embedding.

        Uses TrackEmbeddingsService to get all embeddings for tracks of this artist.

        Args:
            artist: Artist object

        Returns:
            Centroid vector as list of floats, or None if no valid tracks
        """
        try:
            if not ML_AVAILABLE:
                logger.warning(f"ML libraries not available for aggregating embeddings for {artist.name}")
                return None

            # Get all tracks for this artist from the database
            from backend.api.models.tracks_model import Track

            result = await self.db.execute(
                select(Track.id).where(Track.track_artist_id == artist.id)
            )
            track_ids = [row[0] for row in result.fetchall()]

            if not track_ids:
                logger.warning(f"No tracks found for artist: {artist.name}")
                return None

            # Get track embeddings from TrackEmbeddings
            try:
                from backend.api.services.track_embeddings_service import \
                    TrackEmbeddingsService

                service = TrackEmbeddingsService(self.db)
                track_embeddings = await service.get_by_track_ids(track_ids, embedding_type='semantic')

                if not track_embeddings:
                    logger.debug(f"No semantic embeddings found for tracks of artist: {artist.name}")
                    # Try to use any available embedding type
                    track_embeddings = await service.get_by_track_ids(track_ids)

                if not track_embeddings:
                    logger.warning(f"No embeddings found for tracks of artist: {artist.name}")
                    return None

                # Extract vectors
                vectors = [emb.vector for emb in track_embeddings]

            except ImportError:
                logger.warning(f"TrackEmbeddingsService not available for artist: {artist.name}")
                return None
            except Exception as e:
                logger.error(f"Error getting track embeddings for artist {artist.name}: {e}")
                return None

            if not vectors:
                logger.warning(f"No valid track embeddings found for artist: {artist.name}")
                return None

            # Calculate centroid (mean) of all track embeddings in thread pool
            def _calculate_centroid():
                import numpy as np
                vectors_array = np.array(vectors)
                centroid = np.mean(vectors_array, axis=0)
                return centroid.tolist()

            embedding_vector = await asyncio.to_thread(_calculate_centroid)

            logger.info(f"Generated embedding for {artist.name} from {len(vectors)} tracks (TrackEmbeddings)")

            return embedding_vector

        except Exception as e:
            logger.error(f"Error aggregating embeddings for artist {artist.name}: {e}")
            return None

    async def get_track_embedding(self, track_id: int, embedding_type: str = 'semantic') -> Optional[List[float]]:
        """
        Get a track embedding using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding_type: Type of embedding to retrieve

        Returns:
            Embedding vector or None if not found
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            service = TrackEmbeddingsService(self.db)
            embedding = await service.get_single_by_track_id(track_id, embedding_type)

            return embedding.vector if embedding else None

        except ImportError:
            logger.warning("TrackEmbeddingsService not available")
            return None
        except Exception as e:
            logger.error(f"Error getting track embedding for {track_id}: {e}")
            return None

    async def generate_track_embeddings(
        self,
        track_id: int,
        embedding: List[float],
        embedding_type: str = 'semantic',
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Generate and store a track embedding using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding: Vector embedding
            embedding_type: Type of embedding
            embedding_source: Source of vectorization
            embedding_model: Model used

        Returns:
            True if successful
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            service = TrackEmbeddingsService(self.db)
            await service.create_or_update(
                track_id=track_id,
                vector=embedding,
                embedding_type=embedding_type,
                embedding_source=embedding_source,
                embedding_model=embedding_model
            )

            logger.debug(f"[ARTIST EMBEDDING] Generated embedding for track {track_id}")
            return True

        except ImportError:
            logger.warning("TrackEmbeddingsService not available")
            return False
        except Exception as e:
            logger.error(f"Error generating track embedding for {track_id}: {e}")
            return False

    async def find_similar_artists_vector(self, artist_name: str, limit: int = 10) -> List[ArtistSimilarityRecommendation]:
        """
        Find artists similar to the given artist using vector similarity search.

        This method uses sqlite-vec for fast similarity search based on embeddings.

        Args:
            artist_name: Name of the artist to find similar artists for
            limit: Maximum number of similar artists to return

        Returns:
            List of similar artists with similarity scores
        """
        try:
            # Get the embedding for the query artist
            query_embedding = await self.vector_search.get_artist_embedding(artist_name)

            if not query_embedding:
                logger.warning(f"No embedding found for artist: {artist_name}")
                return []

            # Find similar artists using vector search
            similar_results = await self.vector_search.find_similar_artists(query_embedding, limit + 1)  # +1 to exclude self

            # Convert to ArtistSimilarityRecommendation objects
            recommendations = []
            for result in similar_results:
                similar_artist_name = result["artist_name"]

                # Skip the artist itself
                if similar_artist_name == artist_name:
                    continue

                # Get additional info from database
                embedding = await self.get_embedding_by_artist(similar_artist_name)

                recommendation = ArtistSimilarityRecommendation(
                    artist_name=similar_artist_name,
                    similarity_score=result["similarity_score"],
                    distance=result["distance"],
                    cluster=embedding.cluster if embedding else None,
                    source="vector_similarity"
                )

                recommendations.append(recommendation)

                if len(recommendations) >= limit:
                    break

            logger.info(f"Found {len(recommendations)} similar artists for {artist_name} using vector search")
            return recommendations

        except Exception as e:
            logger.error(f"Error finding similar artists for {artist_name}: {e}")
            return []

    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get information about current clusters."""
        try:
            # Count artists per cluster
            cluster_counts = {}
            embeddings = await self.get_all_embeddings(limit=10000)

            for emb in embeddings:
                cluster = emb.cluster
                if cluster is not None:
                    cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

            # Get active GMM model
            result = await self.db.execute(
                select(GMMModel).where(GMMModel.is_active.is_(True))
            )
            active_model = result.scalars().first()

            return {
                "total_artists": len(embeddings),
                "clusters": cluster_counts,
                "n_clusters": len(cluster_counts),
                "gmm_model": {
                    "n_components": active_model.n_components if active_model else None,
                    "trained_at": active_model.trained_at.isoformat() if active_model else None,
                    "log_likelihood": active_model.log_likelihood if active_model else None
                } if active_model else None
            }

        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return {"error": str(e)}

    async def delete_track_embedding(self, track_id: int, embedding_type: Optional[str] = None) -> bool:
        """
        Delete track embeddings using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding_type: Specific type to delete (None = all)

        Returns:
            True if successful
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            service = TrackEmbeddingsService(self.db)
            result = await service.delete(track_id, embedding_type)

            logger.debug(f"Deleted embedding for track {track_id}")
            return result

        except ImportError:
            logger.warning("TrackEmbeddingsService not available")
            return False
        except Exception as e:
            logger.error(f"Error deleting track embedding for {track_id}: {e}")
            return False
