from __future__ import annotations
from typing import Optional, List

import strawberry

from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.track_audio_features_type import (
    TrackAudioFeaturesType,
)
from backend.api.graphql.types.track_embeddings_type import TrackEmbeddingsType
from backend.api.graphql.types.track_metadata_type import TrackMetadataType
from backend.api.graphql.types.track_mir_type import (
    TrackMIRRawType,
    TrackMIRNormalizedType,
    TrackMIRScoresType,
    TrackMIRSyntheticTagType,
)
from backend.api.utils.logging import logger


@strawberry.type
class TrackType:
    """
    Type GraphQL pour une piste musicale.

    Ce type maintient la rétrocompatibilité en exposant les caractéristiques
    audio (bpm, key, etc.) comme des propriétés calculées qui lisent depuis
    la relation audio_features.

    Attributes:
        # Champs de base
        id: Identifiant unique
        title: Titre de la piste
        path: Chemin du fichier
        track_artist_id: ID de l'artiste principal
        album_id: ID de l'album
        duration: Durée en secondes
        track_number: Numéro de piste
        disc_number: Numéro de disque
        year: Année de sortie
        genre: Genre musical
        file_type: Type de fichier
        bitrate: Débit binaire
        featured_artists: Artistes en featuring

        # Relations vers les nouvelles tables
        audio_features: Caractéristiques audio détaillées
        embeddings: Liste des embeddings vectoriels
        metadata_entries: Métadonnées enrichies

        # Propriétés calculées (rétrocompatibilité)
        bpm, key, scale, etc.: Lus depuis audio_features

        # Autres champs
        musicbrainz_id: ID MusicBrainz
        acoustid_fingerprint: Empreinte AcoustID
        covers: Pochettes associées
    """

    # Champs de base
    id: int
    title: str | None
    path: str
    track_artist_id: int
    album_id: int | None
    duration: float | None
    track_number: str | None
    disc_number: str | None
    year: str | None
    genre: str | None
    file_type: str | None
    bitrate: int | None
    featured_artists: str | None

    # Champs MusicBrainz/AcoustID
    musicbrainz_id: str | None
    musicbrainz_albumid: str | None
    musicbrainz_artistid: str | None
    musicbrainz_albumartistid: str | None
    acoustid_fingerprint: str | None

    # Relations
    covers: list[CoverType] = strawberry.field(default_factory=list)

    # Nouvelles relations (stockées dans l'instance SQLAlchemy)
    # audio_features: Optional[TrackAudioFeaturesType] = None
    # embeddings: list[TrackEmbeddingsType] = strawberry.field(default_factory=list)
    # metadata_entries: list[TrackMetadataType] = strawberry.field(default_factory=list)

    # Propriétés calculées pour la rétrocompatibilité
    @strawberry.field
    def bpm(self) -> float | None:
        """Tempo en BPM (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.bpm
        return None

    @strawberry.field
    def key(self) -> str | None:
        """Tonalité musicale (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.key
        return None

    @strawberry.field
    def scale(self) -> str | None:
        """Mode (major/minor) (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.scale
        return None

    @strawberry.field
    def danceability(self) -> float | None:
        """Score de dansabilité (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.danceability
        return None

    @strawberry.field
    def mood_happy(self) -> float | None:
        """Score mood happy (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.mood_happy
        return None

    @strawberry.field
    def mood_aggressive(self) -> float | None:
        """Score mood aggressive (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.mood_aggressive
        return None

    @strawberry.field
    def mood_party(self) -> float | None:
        """Score mood party (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.mood_party
        return None

    @strawberry.field
    def mood_relaxed(self) -> float | None:
        """Score mood relaxed (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.mood_relaxed
        return None

    @strawberry.field
    def instrumental(self) -> float | None:
        """Score instrumental (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.instrumental
        return None

    @strawberry.field
    def acoustic(self) -> float | None:
        """Score acoustic (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.acoustic
        return None

    @strawberry.field
    def tonal(self) -> float | None:
        """Score tonal (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.tonal
        return None

    @strawberry.field
    def camelot_key(self) -> str | None:
        """Clé Camelot pour DJ (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.camelot_key
        return None

    @strawberry.field
    def genre_main(self) -> str | None:
        """Genre principal détecté (depuis audio_features)."""
        if hasattr(self, "audio_features") and self.audio_features:
            return self.audio_features.genre_main
        return None

    # Résolveurs pour les nouvelles relations
    @strawberry.field
    def audio_features(self) -> TrackAudioFeaturesType | None:
        """
        Récupère les caractéristiques audio détaillées de la piste.

        Returns:
            Les caractéristiques audio ou None si non analysées
        """
        # Le résolveur sera appelé avec l'instance SQLAlchemy
        # La relation est chargée via lazy='selectin' dans le modèle
        if hasattr(self, "_audio_features"):
            features = self._audio_features
            if features:
                return TrackAudioFeaturesType(
                    id=features.id,
                    track_id=features.track_id,
                    bpm=features.bpm,
                    key=features.key,
                    scale=features.scale,
                    danceability=features.danceability,
                    mood_happy=features.mood_happy,
                    mood_aggressive=features.mood_aggressive,
                    mood_party=features.mood_party,
                    mood_relaxed=features.mood_relaxed,
                    instrumental=features.instrumental,
                    acoustic=features.acoustic,
                    tonal=features.tonal,
                    genre_main=features.genre_main,
                    camelot_key=features.camelot_key,
                    analysis_source=features.analysis_source,
                    analyzed_at=features.analyzed_at,
                    date_added=features.date_added,
                    date_modified=features.date_modified,
                )
        return None

    @strawberry.field
    def embeddings(self) -> list[TrackEmbeddingsType]:
        """
        Récupère les embeddings vectoriels de la piste.

        Returns:
            Liste des embeddings (peut être vide)
        """
        if hasattr(self, "_embeddings"):
            return [
                TrackEmbeddingsType(
                    id=emb.id,
                    track_id=emb.track_id,
                    embedding_type=emb.embedding_type,
                    embedding_source=emb.embedding_source,
                    embedding_model=emb.embedding_model,
                    created_at=emb.created_at,
                    date_added=emb.date_added,
                    date_modified=emb.date_modified,
                )
                for emb in self._embeddings or []
            ]
        return []

    @strawberry.field
    def metadata(self) -> list[TrackMetadataType]:
        """
        Récupère les métadonnées enrichies de la piste.

        Returns:
            Liste des métadonnées (peut être vide)
        """
        if hasattr(self, "_metadata_entries"):
            return [
                TrackMetadataType(
                    id=meta.id,
                    track_id=meta.track_id,
                    metadata_key=meta.metadata_key,
                    metadata_value=meta.metadata_value,
                    metadata_source=meta.metadata_source,
                    created_at=meta.created_at,
                    date_added=meta.date_added,
                    date_modified=meta.date_modified,
                )
                for meta in self._metadata_entries or []
            ]
        return []

    # Résolveurs pour les relations MIR
    @strawberry.field
    def mir_raw(self) -> TrackMIRRawType | None:
        """
        Récupère les tags MIR bruts de la piste.

        Returns:
            Les tags MIR bruts ou None si non disponibles
        """
        if hasattr(self, "_mir_raw") and self._mir_raw:
            raw = self._mir_raw
            return TrackMIRRawType(
                id=raw.id,
                track_id=raw.track_id,
                bpm=raw.bpm,
                key=raw.key,
                scale=raw.scale,
                danceability=raw.danceability,
                mood_happy=raw.mood_happy,
                mood_aggressive=raw.mood_aggressive,
                mood_party=raw.mood_party,
                mood_relaxed=raw.mood_relaxed,
                instrumental=raw.instrumental,
                acoustic=raw.acoustic,
                tonal=raw.tonal,
                genre_tags=list(raw.genre_tags) if raw.genre_tags else [],
                mood_tags=list(raw.mood_tags) if raw.mood_tags else [],
                analysis_source=raw.analysis_source,
                created_at=raw.created_at,
                date_added=raw.date_added,
                date_modified=raw.date_modified,
            )
        return None

    @strawberry.field
    def mir_normalized(self) -> TrackMIRNormalizedType | None:
        """
        Récupère les tags MIR normalisés de la piste.

        Returns:
            Les tags MIR normalisés ou None si non disponibles
        """
        if hasattr(self, "_mir_normalized") and self._mir_normalized:
            norm = self._mir_normalized
            return TrackMIRNormalizedType(
                id=norm.id,
                track_id=norm.track_id,
                bpm_score=norm.bpm_score,
                bpm_raw=norm.bpm_raw,
                key=norm.key,
                scale=norm.scale,
                camelot_key=norm.camelot_key,
                danceability=norm.danceability,
                mood_happy=norm.mood_happy,
                mood_aggressive=norm.mood_aggressive,
                mood_party=norm.mood_party,
                mood_relaxed=norm.mood_relaxed,
                instrumental=norm.instrumental,
                acoustic=norm.acoustic,
                tonal=norm.tonal,
                genre_main=norm.genre_main,
                genre_secondary=list(norm.genre_secondary) if norm.genre_secondary else [],
                confidence_score=norm.confidence_score,
                created_at=norm.created_at,
                date_added=norm.date_added,
                date_modified=norm.date_modified,
            )
        return None

    @strawberry.field
    def mir_scores(self) -> TrackMIRScoresType | None:
        """
        Récupère les scores MIR calculés de la piste.

        Returns:
            Les scores MIR ou None si non calculés
        """
        if hasattr(self, "_mir_scores") and self._mir_scores:
            scores = self._mir_scores
            return TrackMIRScoresType(
                id=scores.id,
                track_id=scores.track_id,
                energy_score=scores.energy_score,
                mood_valence=scores.mood_valence,
                dance_score=scores.dance_score,
                acousticness=scores.acousticness,
                complexity_score=scores.complexity_score,
                emotional_intensity=scores.emotional_intensity,
                created_at=scores.created_at,
                date_added=scores.date_added,
                date_modified=scores.date_modified,
            )
        return None

    @strawberry.field
    def mir_synthetic_tags(self) -> list[TrackMIRSyntheticTagType]:
        """
        Récupère les tags synthétiques de la piste.

        Returns:
            Liste des tags synthétiques (peut être vide)
        """
        if hasattr(self, "_mir_synthetic_tags"):
            return [
                TrackMIRSyntheticTagType(
                    id=tag.id,
                    track_id=tag.track_id,
                    tag_name=tag.tag_name,
                    tag_category=tag.tag_category,
                    tag_score=tag.tag_score,
                    generation_source=tag.generation_source,
                    created_at=tag.created_at,
                    date_added=tag.date_added,
                    date_modified=tag.date_modified,
                )
                for tag in self._mir_synthetic_tags or []
            ]
        return []


@strawberry.input
class TrackCreateInput:
    title: str | None = None
    path: str
    track_artist_id: int
    album_id: int | None = None
    duration: float | None = None
    track_number: str | None = None
    disc_number: str | None = None
    year: str | None = None
    genre: str | None = None
    file_type: str | None = None
    bitrate: int | None = None
    featured_artists: str | None = None
    bpm: float | None = None
    key: str | None = None
    scale: str | None = None
    danceability: float | None = None
    mood_happy: float | None = None
    mood_aggressive: float | None = None
    mood_party: float | None = None
    mood_relaxed: float | None = None
    instrumental: float | None = None
    acoustic: float | None = None
    tonal: float | None = None
    camelot_key: str | None = None
    genre_main: str | None = None
    musicbrainz_id: str | None = None
    musicbrainz_albumid: str | None = None
    musicbrainz_artistid: str | None = None
    musicbrainz_albumartistid: str | None = None
    acoustid_fingerprint: str | None = None


@strawberry.input
class TrackUpdateInput:
    id: int
    title: str | None = None
    path: str | None = None
    track_artist_id: int | None = None
    album_id: int | None = None
    duration: float | None = None
    track_number: str | None = None
    disc_number: str | None = None
    year: str | None = None
    genre: str | None = None
    file_type: str | None = None
    bitrate: int | None = None
    featured_artists: str | None = None
    bpm: float | None = None
    key: str | None = None
    scale: str | None = None
    danceability: float | None = None
    mood_happy: float | None = None
    mood_aggressive: float | None = None
    mood_party: float | None = None
    mood_relaxed: float | None = None
    instrumental: float | None = None
    acoustic: float | None = None
    tonal: float | None = None
    camelot_key: str | None = None
    genre_main: str | None = None
    musicbrainz_id: str | None = None
    musicbrainz_albumid: str | None = None
    musicbrainz_artistid: str | None = None
    musicbrainz_albumartistid: str | None = None
    acoustid_fingerprint: str | None = None