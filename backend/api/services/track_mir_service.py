# -*- coding: utf-8 -*-
"""
Service CRUD pour les données MIR (Music Information Retrieval).

Rôle:
    Fournit les opérations CRUD pour les modèles MIR:
    - TrackMIRRaw: Données MIR brutes
    - TrackMIRNormalized: Données MIR normalisées
    - TrackMIRScores: Scores MIR calculés
    - TrackMIRSyntheticTags: Tags synthétiques

Dépendances:
    - backend.api.models.track_mir_raw_model: TrackMIRRaw
    - backend.api.models.track_mir_normalized_model: TrackMIRNormalized
    - backend.api.models.track_mir_scores_model: TrackMIRScores
    - backend.api.models.track_mir_synthetic_tags_model: TrackMIRSyntheticTags
    - backend.api.utils.logging: logger
    - sqlalchemy.ext.asyncio: AsyncSession

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.track_mir_raw_model import TrackMIRRaw
from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
from backend.api.models.track_mir_scores_model import TrackMIRScores
from backend.api.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags
from backend.api.utils.logging import logger


class TrackMIRService:
    """
    Service CRUD pour les données MIR des pistes.

    Ce service encapsule toutes les opérations CRUD sur les tables MIR,
    permettant un accès centralisé et cohérent aux données MIR.

    Attributes:
        session: Session SQLAlchemy asynchrone pour les opérations DB

    Example:
        >>> async with async_session() as session:
        ...     service = TrackMIRService(session)
        ...     raw = await service.get_raw_by_track_id(1)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialise le service avec une session de base de données.

        Args:
            session: Session SQLAlchemy asynchrone
        """
        self.session = session

    # ==========================================================================
    # TrackMIRRaw (Données brutes)
    # ==========================================================================

    async def get_raw_by_track_id(self, track_id: int) -> Optional[TrackMIRRaw]:
        """
        Récupère les données MIR brutes d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            Les données MIR brutes ou None si non trouvées
        """
        result = await self.session.execute(
            select(TrackMIRRaw).where(TrackMIRRaw.track_id == track_id)
        )
        return result.scalars().first()

    async def create_or_update_raw(
        self,
        track_id: int,
        features_raw: Optional[Dict[str, Any]] = None,
        mir_source: Optional[str] = None,
        mir_version: Optional[str] = None,
    ) -> TrackMIRRaw:
        """
        Crée ou met à jour les données MIR brutes d'une piste.

        Args:
            track_id: ID de la piste
            features_raw: Dictionnaire des features MIR brutes
            mir_source: Source d'analyse
            mir_version: Version du pipeline MIR

        Returns:
            Les données MIR brutes créées ou mises à jour
        """
        if features_raw is None:
            features_raw = {}

        existing = await self.get_raw_by_track_id(track_id)
        current_time = datetime.utcnow()

        if existing:
            # Mise à jour
            existing.features_raw = features_raw
            existing.mir_source = mir_source or "graphql"
            existing.mir_version = mir_version or "1.0"
            existing.analyzed_at = current_time
            mir_raw = existing
        else:
            # Création
            mir_raw = TrackMIRRaw(
                track_id=track_id,
                features_raw=features_raw,
                mir_source=mir_source or "graphql",
                mir_version=mir_version or "1.0",
                analyzed_at=current_time,
            )
            self.session.add(mir_raw)

        await self.session.commit()
        await self.session.refresh(mir_raw)

        logger.info(f"[MIR_SERVICE] Raw créé/mis à jour pour track_id={track_id}")
        return mir_raw

    async def delete_raw(self, track_id: int) -> bool:
        """
        Supprime les données MIR brutes d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            True si supprimé, False si non trouvé
        """
        result = await self.session.execute(
            select(TrackMIRRaw).where(TrackMIRRaw.track_id == track_id)
        )
        existing = result.scalars().first()

        if not existing:
            return False

        await self.session.delete(existing)
        await self.session.commit()
        logger.info(f"[MIR_SERVICE] Raw supprimé pour track_id={track_id}")
        return True

    # ==========================================================================
    # TrackMIRNormalized (Données normalisées)
    # ==========================================================================

    async def get_normalized_by_track_id(
        self, track_id: int
    ) -> Optional[TrackMIRNormalized]:
        """
        Récupère les données MIR normalisées d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            Les données MIR normalisées ou None si non trouvées
        """
        result = await self.session.execute(
            select(TrackMIRNormalized).where(TrackMIRNormalized.track_id == track_id)
        )
        return result.scalars().first()

    async def create_or_update_normalized(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        camelot_key: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        genre_secondary: Optional[List[str]] = None,
        confidence_score: Optional[float] = None,
    ) -> TrackMIRNormalized:
        """
        Crée ou met à jour les données MIR normalisées d'une piste.

        Args:
            track_id: ID de la piste
            bpm: Tempo en BPM
            key: Tonalité
            scale: Mode (major/minor)
            camelot_key: Clé Camelot
            danceability: Score de dansabilité
            mood_*: Scores de mood
            instrumental: Score instrumental
            acoustic: Score acoustic
            tonal: Score tonal
            genre_main: Genre principal
            genre_secondary: Genres secondaires
            confidence_score: Score de confiance

        Returns:
            Les données MIR normalisées créées ou mises à jour
        """
        existing = await self.get_normalized_by_track_id(track_id)
        current_time = datetime.utcnow()

        if existing:
            # Mise à jour
            existing.bpm = bpm
            existing.key = key
            existing.scale = scale
            existing.camelot_key = camelot_key
            existing.danceability = danceability
            existing.mood_happy = mood_happy
            existing.mood_aggressive = mood_aggressive
            existing.mood_party = mood_party
            existing.mood_relaxed = mood_relaxed
            existing.instrumental = instrumental
            existing.acoustic = acoustic
            existing.tonal = tonal
            existing.genre_main = genre_main
            existing.genre_secondary = genre_secondary
            existing.confidence_score = confidence_score
            existing.normalized_at = current_time
            mir_norm = existing
        else:
            # Création
            mir_norm = TrackMIRNormalized(
                track_id=track_id,
                bpm=bpm,
                key=key,
                scale=scale,
                camelot_key=camelot_key,
                danceability=danceability,
                mood_happy=mood_happy,
                mood_aggressive=mood_aggressive,
                mood_party=mood_party,
                mood_relaxed=mood_relaxed,
                instrumental=instrumental,
                acoustic=acoustic,
                tonal=tonal,
                genre_main=genre_main,
                genre_secondary=genre_secondary or [],
                confidence_score=confidence_score,
                normalized_at=current_time,
            )
            self.session.add(mir_norm)

        await self.session.commit()
        await self.session.refresh(mir_norm)

        logger.info(f"[MIR_SERVICE] Normalized créé/mis à jour pour track_id={track_id}")
        return mir_norm

    async def delete_normalized(self, track_id: int) -> bool:
        """
        Supprime les données MIR normalisées d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            True si supprimé, False si non trouvé
        """
        result = await self.session.execute(
            select(TrackMIRNormalized).where(TrackMIRNormalized.track_id == track_id)
        )
        existing = result.scalars().first()

        if not existing:
            return False

        await self.session.delete(existing)
        await self.session.commit()
        logger.info(f"[MIR_SERVICE] Normalized supprimé pour track_id={track_id}")
        return True

    # ==========================================================================
    # TrackMIRScores (Scores calculés)
    # ==========================================================================

    async def get_scores_by_track_id(self, track_id: int) -> Optional[TrackMIRScores]:
        """
        Récupère les scores MIR d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            Les scores MIR ou None si non trouvés
        """
        result = await self.session.execute(
            select(TrackMIRScores).where(TrackMIRScores.track_id == track_id)
        )
        return result.scalars().first()

    async def create_or_update_scores(
        self,
        track_id: int,
        energy_score: Optional[float] = None,
        mood_valence: Optional[float] = None,
        dance_score: Optional[float] = None,
        acousticness: Optional[float] = None,
        complexity_score: Optional[float] = None,
        emotional_intensity: Optional[float] = None,
    ) -> TrackMIRScores:
        """
        Crée ou met à jour les scores MIR d'une piste.

        Args:
            track_id: ID de la piste
            energy_score: Score d'énergie
            mood_valence: Valence émotionnelle
            dance_score: Score de danseabilité
            acousticness: Score d'acousticité
            complexity_score: Score de complexité
            emotional_intensity: Intensité émotionnelle

        Returns:
            Les scores MIR créés ou mis à jour
        """
        existing = await self.get_scores_by_track_id(track_id)
        current_time = datetime.utcnow()

        if existing:
            # Mise à jour
            existing.energy_score = energy_score
            existing.mood_valence = mood_valence
            existing.dance_score = dance_score
            existing.acousticness = acousticness
            existing.complexity_score = complexity_score
            existing.emotional_intensity = emotional_intensity
            existing.calculated_at = current_time
            mir_scores = existing
        else:
            # Création
            mir_scores = TrackMIRScores(
                track_id=track_id,
                energy_score=energy_score,
                mood_valence=mood_valence,
                dance_score=dance_score,
                acousticness=acousticness,
                complexity_score=complexity_score,
                emotional_intensity=emotional_intensity,
                calculated_at=current_time,
            )
            self.session.add(mir_scores)

        await self.session.commit()
        await self.session.refresh(mir_scores)

        logger.info(f"[MIR_SERVICE] Scores créés/mis à jour pour track_id={track_id}")
        return mir_scores

    async def delete_scores(self, track_id: int) -> bool:
        """
        Supprime les scores MIR d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            True si supprimé, False si non trouvé
        """
        result = await self.session.execute(
            select(TrackMIRScores).where(TrackMIRScores.track_id == track_id)
        )
        existing = result.scalars().first()

        if not existing:
            return False

        await self.session.delete(existing)
        await self.session.commit()
        logger.info(f"[MIR_SERVICE] Scores supprimés pour track_id={track_id}")
        return True

    # ==========================================================================
    # TrackMIRSyntheticTags (Tags synthétiques)
    # ==========================================================================

    async def get_synthetic_tags_by_track_id(
        self, track_id: int
    ) -> List[TrackMIRSyntheticTags]:
        """
        Récupère les tags synthétiques d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            Liste des tags synthétiques
        """
        result = await self.session.execute(
            select(TrackMIRSyntheticTags).where(
                TrackMIRSyntheticTags.track_id == track_id
            )
        )
        return list(result.scalars().all())

    async def add_synthetic_tag(
        self,
        track_id: int,
        tag_name: str,
        tag_category: str,
        tag_score: float = 1.0,
        tag_source: str = "IA",
    ) -> TrackMIRSyntheticTags:
        """
        Ajoute un tag synthétique pour une piste.

        Args:
            track_id: ID de la piste
            tag_name: Nom du tag
            tag_category: Catégorie du tag
            tag_score: Score du tag [0.0-1.0]
            tag_source: Source du tag

        Returns:
            Le tag synthétique créé
        """
        current_time = datetime.utcnow()

        synthetic_tag = TrackMIRSyntheticTags(
            track_id=track_id,
            tag_name=tag_name,
            tag_category=tag_category,
            tag_score=tag_score,
            tag_source=tag_source,
            created_at=current_time,
        )
        self.session.add(synthetic_tag)

        await self.session.commit()
        await self.session.refresh(synthetic_tag)

        logger.info(
            f"[MIR_SERVICE] Tag synthétique ajouté: track_id={track_id}, "
            f"tag={tag_name}, category={tag_category}"
        )
        return synthetic_tag

    async def delete_synthetic_tags(self, track_id: int) -> int:
        """
        Supprime tous les tags synthétiques d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            Nombre de tags supprimés
        """
        result = await self.session.execute(
            select(TrackMIRSyntheticTags).where(
                TrackMIRSyntheticTags.track_id == track_id
            )
        )
        tags = result.scalars().all()

        count = len(tags)
        for tag in tags:
            await self.session.delete(tag)

        await self.session.commit()
        logger.info(f"[MIR_SERVICE] {count} tags synthétiques supprimés pour track_id={track_id}")
        return count

    async def delete_synthetic_tag_by_id(self, tag_id: int) -> bool:
        """
        Supprime un tag synthétique par son ID.

        Args:
            tag_id: ID du tag

        Returns:
            True si supprimé, False si non trouvé
        """
        result = await self.session.execute(
            select(TrackMIRSyntheticTags).where(TrackMIRSyntheticTags.id == tag_id)
        )
        tag = result.scalars().first()

        if not tag:
            return False

        await self.session.delete(tag)
        await self.session.commit()
        logger.info(f"[MIR_SERVICE] Tag synthétique supprimé: id={tag_id}")
        return True

    # ==========================================================================
    # Opérations globales
    # ==========================================================================

    async def delete_all_mir(self, track_id: int) -> bool:
        """
        Supprime toutes les données MIR d'une piste.

        Cette méthode supprime:
        - TrackMIRRaw
        - TrackMIRNormalized
        - TrackMIRScores
        - TrackMIRSyntheticTags

        Args:
            track_id: ID de la piste

        Returns:
            True si succès
        """
        # Supprimer les tags synthétiques
        await self.delete_synthetic_tags(track_id)

        # Supprimer les scores MIR
        await self.delete_scores(track_id)

        # Supprimer les données MIR normalisées
        await self.delete_normalized(track_id)

        # Supprimer les données MIR brutes
        await self.delete_raw(track_id)

        logger.info(f"[MIR_SERVICE] Toutes les données MIR supprimées pour track_id={track_id}")
        return True

    async def ensure_mir_entries(self, track_id: int) -> None:
        """
        S'assure que toutes les entrées MIR existent pour une piste.

        Crée les entrées si elles n'existent pas.

        Args:
            track_id: ID de la piste
        """
        current_time = datetime.utcnow()

        # TrackMIRRaw
        raw = await self.get_raw_by_track_id(track_id)
        if not raw:
            raw = TrackMIRRaw(
                track_id=track_id,
                features_raw={},
                mir_source="system",
                mir_version="1.0",
                analyzed_at=current_time,
            )
            self.session.add(raw)

        # TrackMIRNormalized
        norm = await self.get_normalized_by_track_id(track_id)
        if not norm:
            norm = TrackMIRNormalized(
                track_id=track_id,
                normalized_at=current_time,
            )
            self.session.add(norm)

        # TrackMIRScores
        scores = await self.get_scores_by_track_id(track_id)
        if not scores:
            scores = TrackMIRScores(
                track_id=track_id,
                calculated_at=current_time,
            )
            self.session.add(scores)

        await self.session.commit()
        logger.info(f"[MIR_SERVICE] Entrées MIR créées pour track_id={track_id}")

    # ==========================================================================
    # Méthodes de recherche et statistiques
    # ==========================================================================

    async def get_by_energy_range(
        self,
        min_energy: float = 0.0,
        max_energy: float = 1.0,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRScores]:
        """
        Récupère les pistes par plage d'énergie.

        Args:
            min_energy: Score d'énergie minimum
            max_energy: Score d'énergie maximum
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des scores MIR correspondant aux critères
        """
        result = await self.session.execute(
            select(TrackMIRScores)
            .where(
                and_(
                    TrackMIRScores.energy_score >= min_energy,
                    TrackMIRScores.energy_score <= max_energy,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_mood(
        self,
        mood: str,
        min_score: float = 0.5,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRNormalized]:
        """
        Récupère les pistes par mood.

        Args:
            mood: Mood à rechercher (happy, aggressive, party, relaxed)
            min_score: Score minimum pour le mood
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des tags MIR normalisés correspondant aux critères
        """
        mood_column = getattr(TrackMIRNormalized, f"mood_{mood}", None)
        if mood_column is None:
            logger.warning(f"[MIR_SERVICE] Mood invalide: {mood}")
            return []

        result = await self.session.execute(
            select(TrackMIRNormalized)
            .where(and_(mood_column >= min_score))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_bpm_range(
        self,
        min_bpm: float,
        max_bpm: float,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRNormalized]:
        """
        Récupère les pistes par plage de BPM.

        Args:
            min_bpm: BPM minimum
            max_bpm: BPM maximum
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des tags MIR normalisés correspondant aux critères
        """
        result = await self.session.execute(
            select(TrackMIRNormalized)
            .where(
                and_(
                    TrackMIRNormalized.bpm >= min_bpm,
                    TrackMIRNormalized.bpm <= max_bpm,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_camelot_key(
        self,
        camelot_key: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRNormalized]:
        """
        Récupère les pistes par clé Camelot.

        Args:
            camelot_key: Clé Camelot (ex: "8B", "12A")
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des tags MIR normalisés correspondant à la clé Camelot
        """
        result = await self.session.execute(
            select(TrackMIRNormalized)
            .where(TrackMIRNormalized.camelot_key == camelot_key)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_similar_tracks(
        self,
        track_id: int,
        limit: int = 20,
    ) -> List[TrackMIRScores]:
        """
        Trouve les pistes similaires basées sur les caractéristiques MIR.

        Args:
            track_id: ID de la piste de référence
            limit: Nombre maximum de résultats

        Returns:
            Liste des scores MIR des pistes similaires
        """
        # Récupérer les scores de la piste de référence
        source_scores = await self.get_scores_by_track_id(track_id)
        if not source_scores:
            logger.warning(f"[MIR_SERVICE] Pas de scores MIR pour track_id={track_id}")
            return []

        # Calculer la similarité basée sur les scores
        # On cherche des pistes avec des scores proches
        result = await self.session.execute(
            select(TrackMIRScores)
            .where(TrackMIRScores.track_id != track_id)
            .limit(limit * 3)  # On prend plus pour filtrer après
        )
        candidates = result.scalars().all()

        # Calculer la distance euclidienne simple
        def score_distance(scores: TrackMIRScores) -> float:
            if not scores:
                return float('inf')
            dist = 0.0
            if source_scores.energy_score is not None and scores.energy_score is not None:
                dist += abs(source_scores.energy_score - scores.energy_score) ** 2
            if source_scores.mood_valence is not None and scores.mood_valence is not None:
                dist += abs(source_scores.mood_valence - scores.mood_valence) ** 2
            if source_scores.dance_score is not None and scores.dance_score is not None:
                dist += abs(source_scores.dance_score - scores.dance_score) ** 2
            if source_scores.acousticness is not None and scores.acousticness is not None:
                dist += abs(source_scores.acousticness - scores.acousticness) ** 2
            return dist ** 0.5

        # Trier par distance et limiter
        scored = [(s, score_distance(s)) for s in candidates if s]
        scored.sort(key=lambda x: x[1])

        return [s for s, _ in scored[:limit]]

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques MIR globales.

        Returns:
            Dictionnaire des statistiques MIR
        """
        # Compter les pistes avec MIR
        raw_count = await self.session.execute(
            select(func.count(TrackMIRRaw.id))
        )
        total_tracks_with_mir = raw_count.scalar() or 0

        # Calculer la moyenne d'énergie
        energy_result = await self.session.execute(
            select(func.avg(TrackMIRScores.energy_score))
        )
        average_energy = energy_result.scalar() or 0.0

        # Calculer la moyenne de BPM
        bpm_result = await self.session.execute(
            select(func.avg(TrackMIRNormalized.bpm))
        )
        average_bpm = bpm_result.scalar() or 0.0

        # Top moods (basé sur les scores moyens)
        moods = ['happy', 'aggressive', 'party', 'relaxed']
        top_moods = []
        for mood in moods:
            mood_column = getattr(TrackMIRNormalized, f"mood_{mood}")
            result = await self.session.execute(
                select(func.avg(mood_column))
            )
            avg_score = result.scalar() or 0.0
            top_moods.append({'mood': mood, 'average_score': float(avg_score)})
        top_moods.sort(key=lambda x: x['average_score'], reverse=True)

        # Top genres
        genre_result = await self.session.execute(
            select(
                TrackMIRNormalized.genre_main,
                func.count(TrackMIRNormalized.id).label('count')
            )
            .where(TrackMIRNormalized.genre_main.isnot(None))
            .group_by(TrackMIRNormalized.genre_main)
            .order_by(func.count(TrackMIRNormalized.id).desc())
            .limit(10)
        )
        top_genres = [
            {'genre': row.genre_main, 'count': row.count}
            for row in genre_result.all()
        ]

        return {
            'total_tracks_with_mir': total_tracks_with_mir,
            'average_energy': float(average_energy),
            'average_bpm': float(average_bpm),
            'top_moods': top_moods,
            'top_genres': top_genres,
        }
