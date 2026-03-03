# -*- coding: utf-8 -*-
"""
Service métier pour la gestion des caractéristiques audio des pistes.

Rôle:
    Fournit les opérations CRUD et les requêtes spécifiques pour les
    caractéristiques audio extraites des pistes musicales (BPM, tonalité,
    mood, etc.) utilisées pour les recommandations et l'analyse musicale.

Dépendances:
    - backend.api.models.track_audio_features_model: TrackAudioFeatures
    - backend.api.utils.logging: logger
    - sqlalchemy.ext.asyncio: AsyncSession

Auteur: SoniqueBay Team
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.track_audio_features_model import TrackAudioFeatures
from backend.api.utils.logging import logger


class TrackAudioFeaturesService:
    """
    Service métier pour la gestion des caractéristiques audio des pistes.

    Ce service fournit toutes les opérations CRUD pour les caractéristiques audio,
    ainsi que des fonctionnalités de recherche avancée par BPM, tonalité, mood, etc.

    Attributes:
        session: Session SQLAlchemy asynchrone pour les opérations DB

    Example:
        >>> async with async_session() as session:
        ...     service = TrackAudioFeaturesService(session)
        ...     features = await service.get_by_track_id(1)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialise le service avec une session de base de données.

        Args:
            session: Session SQLAlchemy asynchrone
        """
        self.session = session

    async def get_by_id(self, features_id: int) -> Optional[TrackAudioFeatures]:
        """
        Récupère les caractéristiques audio par leur ID.

        Args:
            features_id: ID des caractéristiques audio

        Returns:
            Les caractéristiques audio ou None si non trouvées
        """
        result = await self.session.execute(
            select(TrackAudioFeatures).where(TrackAudioFeatures.id == features_id)
        )
        return result.scalars().first()

    async def get_by_track_id(self, track_id: int) -> Optional[TrackAudioFeatures]:
        """
        Récupère les caractéristiques audio d'une piste par track_id.

        Args:
            track_id: ID de la piste

        Returns:
            Les caractéristiques audio ou None si non trouvées
        """
        result = await self.session.execute(
            select(TrackAudioFeatures).where(TrackAudioFeatures.track_id == track_id)
        )
        return result.scalars().first()

    async def get_by_track_ids(self, track_ids: List[int]) -> List[TrackAudioFeatures]:
        """
        Récupère les caractéristiques audio pour plusieurs pistes.

        Args:
            track_ids: Liste des IDs de pistes

        Returns:
            Liste des caractéristiques audio trouvées
        """
        if not track_ids:
            return []

        result = await self.session.execute(
            select(TrackAudioFeatures).where(
                TrackAudioFeatures.track_id.in_(track_ids)
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        camelot_key: Optional[str] = None,
        analysis_source: Optional[str] = None,
    ) -> TrackAudioFeatures:
        """
        Crée de nouvelles caractéristiques audio pour une piste.

        Args:
            track_id: ID de la piste
            bpm: Tempo en BPM
            key: Tonalité musicale
            scale: Mode (major/minor)
            danceability: Score de dansabilité (0-1)
            mood_happy: Score mood happy (0-1)
            mood_aggressive: Score mood aggressive (0-1)
            mood_party: Score mood party (0-1)
            mood_relaxed: Score mood relaxed (0-1)
            instrumental: Score instrumental (0-1)
            acoustic: Score acoustic (0-1)
            tonal: Score tonal (0-1)
            genre_main: Genre principal détecté
            camelot_key: Clé Camelot pour DJ
            analysis_source: Source d'analyse (librosa, acoustid, tags)

        Returns:
            Les caractéristiques audio créées

        Raises:
            IntegrityError: Si les caractéristiques existent déjà pour cette piste
        """
        features = TrackAudioFeatures(
            track_id=track_id,
            bpm=bpm,
            key=key,
            scale=scale,
            danceability=danceability,
            mood_happy=mood_happy,
            mood_aggressive=mood_aggressive,
            mood_party=mood_party,
            mood_relaxed=mood_relaxed,
            instrumental=instrumental,
            acoustic=acoustic,
            tonal=tonal,
            genre_main=genre_main,
            camelot_key=camelot_key,
            analysis_source=analysis_source,
            analyzed_at=datetime.utcnow(),
        )

        try:
            self.session.add(features)
            await self.session.commit()
            await self.session.refresh(features)
            logger.info(f"[AUDIO_FEATURES] Créées pour track_id={track_id}")
            return features
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                f"[AUDIO_FEATURES] Erreur création pour track_id={track_id}: {e}"
            )
            raise

    async def create_or_update(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        camelot_key: Optional[str] = None,
        analysis_source: Optional[str] = None,
    ) -> TrackAudioFeatures:
        """
        Crée ou met à jour les caractéristiques audio d'une piste.

        Args:
            track_id: ID de la piste
            **kwargs: Tous les champs des caractéristiques audio

        Returns:
            Les caractéristiques audio créées ou mises à jour
        """
        existing = await self.get_by_track_id(track_id)

        if existing:
            return await self.update(
                track_id=track_id,
                bpm=bpm,
                key=key,
                scale=scale,
                danceability=danceability,
                mood_happy=mood_happy,
                mood_aggressive=mood_aggressive,
                mood_party=mood_party,
                mood_relaxed=mood_relaxed,
                instrumental=instrumental,
                acoustic=acoustic,
                tonal=tonal,
                genre_main=genre_main,
                camelot_key=camelot_key,
                analysis_source=analysis_source,
            )
        else:
            return await self.create(
                track_id=track_id,
                bpm=bpm,
                key=key,
                scale=scale,
                danceability=danceability,
                mood_happy=mood_happy,
                mood_aggressive=mood_aggressive,
                mood_party=mood_party,
                mood_relaxed=mood_relaxed,
                instrumental=instrumental,
                acoustic=acoustic,
                tonal=tonal,
                genre_main=genre_main,
                camelot_key=camelot_key,
                analysis_source=analysis_source,
            )

    async def update(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        camelot_key: Optional[str] = None,
        analysis_source: Optional[str] = None,
    ) -> Optional[TrackAudioFeatures]:
        """
        Met à jour les caractéristiques audio d'une piste.

        Args:
            track_id: ID de la piste
            **kwargs: Champs à mettre à jour (None = inchangé)

        Returns:
            Les caractéristiques audio mises à jour ou None si non trouvées
        """
        features = await self.get_by_track_id(track_id)
        if not features:
            logger.warning(
                f"[AUDIO_FEATURES] Mise à jour impossible: track_id={track_id} non trouvé"
            )
            return None

        # Mise à jour des champs non-None
        update_data = {
            'bpm': bpm,
            'key': key,
            'scale': scale,
            'danceability': danceability,
            'mood_happy': mood_happy,
            'mood_aggressive': mood_aggressive,
            'mood_party': mood_party,
            'mood_relaxed': mood_relaxed,
            'instrumental': instrumental,
            'acoustic': acoustic,
            'tonal': tonal,
            'genre_main': genre_main,
            'camelot_key': camelot_key,
            'analysis_source': analysis_source,
        }

        for field, value in update_data.items():
            if value is not None:
                setattr(features, field, value)

        features.analyzed_at = datetime.utcnow()
        features.date_modified = func.now()

        await self.session.commit()
        await self.session.refresh(features)
        logger.info(f"[AUDIO_FEATURES] Mises à jour pour track_id={track_id}")
        return features

    async def delete(self, track_id: int) -> bool:
        """
        Supprime les caractéristiques audio d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            True si supprimé, False si non trouvé
        """
        features = await self.get_by_track_id(track_id)
        if not features:
            return False

        await self.session.delete(features)
        await self.session.commit()
        logger.info(f"[AUDIO_FEATURES] Supprimées pour track_id={track_id}")
        return True

    async def delete_by_id(self, features_id: int) -> bool:
        """
        Supprime les caractéristiques audio par leur ID.

        Args:
            features_id: ID des caractéristiques audio

        Returns:
            True si supprimé, False si non trouvé
        """
        features = await self.get_by_id(features_id)
        if not features:
            return False

        await self.session.delete(features)
        await self.session.commit()
        logger.info(f"[AUDIO_FEATURES] Supprimées id={features_id}")
        return True

    async def get_tracks_without_features(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère les IDs des pistes sans caractéristiques audio.

        Utile pour les tâches d'analyse audio à effectuer.

        Args:
            limit: Nombre maximum de résultats

        Returns:
            Liste des IDs de pistes sans caractéristiques
        """
        from backend.api.models.tracks_model import Track

        result = await self.session.execute(
            select(Track.id)
            .outerjoin(
                TrackAudioFeatures,
                Track.id == TrackAudioFeatures.track_id
            )
            .where(TrackAudioFeatures.id.is_(None))
            .limit(limit)
        )
        return [{'track_id': row[0]} for row in result.all()]

    async def search_by_bpm_range(
        self,
        min_bpm: float,
        max_bpm: float,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackAudioFeatures]:
        """
        Recherche les pistes par plage de BPM.

        Args:
            min_bpm: BPM minimum
            max_bpm: BPM maximum
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio dans la plage de BPM
        """
        result = await self.session.execute(
            select(TrackAudioFeatures)
            .where(
                and_(
                    TrackAudioFeatures.bpm >= min_bpm,
                    TrackAudioFeatures.bpm <= max_bpm
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(TrackAudioFeatures.bpm)
        )
        return list(result.scalars().all())

    async def search_by_key(
        self,
        key: str,
        scale: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackAudioFeatures]:
        """
        Recherche les pistes par tonalité.

        Args:
            key: Tonalité musicale (C, C#, D, etc.)
            scale: Mode optionnel (major/minor)
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio correspondantes
        """
        query = select(TrackAudioFeatures).where(
            TrackAudioFeatures.key.ilike(key)
        )

        if scale:
            query = query.where(TrackAudioFeatures.scale.ilike(scale))

        result = await self.session.execute(
            query.offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_camelot_key(
        self, camelot_key: str, skip: int = 0, limit: int = 100
    ) -> List[TrackAudioFeatures]:
        """
        Recherche les pistes par clé Camelot (harmonie DJ).

        Args:
            camelot_key: Clé Camelot (ex: "8B", "12A")
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio correspondantes
        """
        result = await self.session.execute(
            select(TrackAudioFeatures)
            .where(TrackAudioFeatures.camelot_key == camelot_key)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_mood(
        self,
        happy_min: Optional[float] = None,
        relaxed_min: Optional[float] = None,
        party_min: Optional[float] = None,
        aggressive_max: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackAudioFeatures]:
        """
        Recherche les pistes par critères de mood.

        Args:
            happy_min: Score minimum pour mood_happy
            relaxed_min: Score minimum pour mood_relaxed
            party_min: Score minimum pour mood_party
            aggressive_max: Score maximum pour mood_aggressive
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio correspondantes
        """
        query = select(TrackAudioFeatures)
        conditions = []

        if happy_min is not None:
            conditions.append(TrackAudioFeatures.mood_happy >= happy_min)
        if relaxed_min is not None:
            conditions.append(TrackAudioFeatures.mood_relaxed >= relaxed_min)
        if party_min is not None:
            conditions.append(TrackAudioFeatures.mood_party >= party_min)
        if aggressive_max is not None:
            conditions.append(TrackAudioFeatures.mood_aggressive <= aggressive_max)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(
            query.offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_similar_by_bpm_and_key(
        self,
        track_id: int,
        bpm_tolerance: float = 5.0,
        use_compatible_keys: bool = True,
        limit: int = 20
    ) -> List[TrackAudioFeatures]:
        """
        Trouve les pistes similaires par BPM et tonalité compatible.

        Args:
            track_id: ID de la piste de référence
            bpm_tolerance: Tolérance de BPM (±)
            use_compatible_keys: Utiliser les tonalités harmoniquement compatibles
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio similaires
        """
        reference = await self.get_by_track_id(track_id)
        if not reference or not reference.bpm:
            return []

        # Recherche par plage de BPM
        min_bpm = reference.bpm - bpm_tolerance
        max_bpm = reference.bpm + bpm_tolerance

        query = select(TrackAudioFeatures).where(
            and_(
                TrackAudioFeatures.track_id != track_id,
                TrackAudioFeatures.bpm >= min_bpm,
                TrackAudioFeatures.bpm <= max_bpm
            )
        )

        # Filtre par tonalité compatible si demandé et si key existe
        if use_compatible_keys and reference.camelot_key:
            # Tonalités compatibles (même nombre, lettre adjacente ou ±1)
            camelot_num = int(reference.camelot_key[:-1])
            camelot_letter = reference.camelot_key[-1]

            compatible_keys = [
                f"{camelot_num}{camelot_letter}",  # Même tonalité
                f"{((camelot_num) % 12) or 12}{camelot_letter}",  # +1
                f"{((camelot_num - 2) % 12) + 1}{camelot_letter}",  # -1
            ]

            # Ajouter tonalité relative (même nombre, lettre opposée)
            relative_letter = "B" if camelot_letter == "A" else "A"
            compatible_keys.append(f"{camelot_num}{relative_letter}")

            query = query.where(
                TrackAudioFeatures.camelot_key.in_(compatible_keys)
            )
        elif reference.key:
            query = query.where(TrackAudioFeatures.key == reference.key)

        result = await self.session.execute(
            query.limit(limit).order_by(
                func.abs(TrackAudioFeatures.bpm - reference.bpm)
            )
        )
        return list(result.scalars().all())

    async def count_analyzed_tracks(self) -> int:
        """
        Compte le nombre de pistes ayant des caractéristiques audio.

        Returns:
            Nombre de pistes analysées
        """
        result = await self.session.execute(
            select(func.count(TrackAudioFeatures.id))
        )
        return result.scalar() or 0

    async def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur l'analyse audio.

        Returns:
            Dictionnaire des statistiques (count, bpm range, etc.)
        """
        stats = {}

        # Nombre total
        stats['total_analyzed'] = await self.count_analyzed_tracks()

        # BPM moyen, min, max
        bpm_stats = await self.session.execute(
            select(
                func.avg(TrackAudioFeatures.bpm),
                func.min(TrackAudioFeatures.bpm),
                func.max(TrackAudioFeatures.bpm)
            ).where(TrackAudioFeatures.bpm.isnot(None))
        )
        avg_bpm, min_bpm, max_bpm = bpm_stats.first()
        stats['bpm'] = {
            'average': round(avg_bpm, 2) if avg_bpm else None,
            'min': min_bpm,
            'max': max_bpm
        }

        # Répartition par source d'analyse
        source_result = await self.session.execute(
            select(
                TrackAudioFeatures.analysis_source,
                func.count(TrackAudioFeatures.id)
            ).group_by(TrackAudioFeatures.analysis_source)
        )
        stats['by_source'] = {
            row[0] or 'unknown': row[1] for row in source_result.all()
        }

        return stats

    # ==========================================================================
    # === Phase 10: Intégration MIR ===========================================
    # ==========================================================================

    async def create_with_mir_integration(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        camelot_key: Optional[str] = None,
        mir_source: Optional[str] = None,
        mir_version: Optional[str] = None,
        confidence_score: Optional[float] = None,
    ) -> TrackAudioFeatures:
        """
        Crée les caractéristiques audio avec intégration du pipeline MIR.

        Cette méthode crée les features audio en intégrant les données MIR
        (source, version, score de confiance) pour une traçabilité complète.

        Args:
            track_id: ID de la piste
            bpm: Tempo en BPM
            key: Tonalité musicale
            scale: Mode (major/minor)
            danceability: Score de dansabilité (0-1)
            mood_happy: Score mood happy (0-1)
            mood_aggressive: Score mood aggressive (0-1)
            mood_party: Score mood party (0-1)
            mood_relaxed: Score mood relaxed (0-1)
            instrumental: Score instrumental (0-1)
            acoustic: Score acoustic (0-1)
            tonal: Score tonal (0-1)
            genre_main: Genre principal détecté
            camelot_key: Clé Camelot pour DJ
            mir_source: Source MIR (acoustid, standards, librosa, essentia)
            mir_version: Version du pipeline MIR
            confidence_score: Score de confiance global [0.0-1.0]

        Returns:
            Les caractéristiques audio créées avec métadonnées MIR

        Raises:
            IntegrityError: Si les caractéristiques existent déjà pour cette piste
        """
        features = TrackAudioFeatures(
            track_id=track_id,
            bpm=bpm,
            key=key,
            scale=scale,
            danceability=danceability,
            mood_happy=mood_happy,
            mood_aggressive=mood_aggressive,
            mood_party=mood_party,
            mood_relaxed=mood_relaxed,
            instrumental=instrumental,
            acoustic=acoustic,
            tonal=tonal,
            genre_main=genre_main,
            camelot_key=camelot_key,
            analysis_source=mir_source,
            analyzed_at=datetime.utcnow(),
        )

        # Ajouter les champs MIR si fournis
        if hasattr(features, 'mir_source'):
            features.mir_source = mir_source
        if hasattr(features, 'mir_version'):
            features.mir_version = mir_version
        if hasattr(features, 'confidence_score'):
            features.confidence_score = confidence_score

        try:
            self.session.add(features)
            await self.session.commit()
            await self.session.refresh(features)
            logger.info(
                f"[AUDIO_FEATURES] Créées avec MIR pour track_id={track_id}: "
                f"source={mir_source}, confidence={confidence_score}"
            )
            return features
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                f"[AUDIO_FEATURES] Erreur création MIR pour track_id={track_id}: {e}"
            )
            raise

    async def update_with_mir_integration(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        camelot_key: Optional[str] = None,
        mir_source: Optional[str] = None,
        mir_version: Optional[str] = None,
        confidence_score: Optional[float] = None,
    ) -> Optional[TrackAudioFeatures]:
        """
        Met à jour les caractéristiques audio avec intégration MIR.

        Args:
            track_id: ID de la piste
            ... (autres paramètres optionnels)
            mir_source: Source MIR
            mir_version: Version du pipeline MIR
            confidence_score: Score de confiance

        Returns:
            Les caractéristiques audio mises à jour ou None si non trouvées
        """
        features = await self.get_by_track_id(track_id)
        if not features:
            logger.warning(
                f"[AUDIO_FEATURES] Mise à jour MIR impossible: track_id={track_id} non trouvé"
            )
            return None

        # Mise à jour des champs non-None
        update_data = {
            'bpm': bpm,
            'key': key,
            'scale': scale,
            'danceability': danceability,
            'mood_happy': mood_happy,
            'mood_aggressive': mood_aggressive,
            'mood_party': mood_party,
            'mood_relaxed': mood_relaxed,
            'instrumental': instrumental,
            'acoustic': acoustic,
            'tonal': tonal,
            'genre_main': genre_main,
            'camelot_key': camelot_key,
            'analysis_source': mir_source,
        }

        for field, value in update_data.items():
            if value is not None:
                setattr(features, field, value)

        # Mise à jour des champs MIR
        if mir_source is not None and hasattr(features, 'mir_source'):
            features.mir_source = mir_source
        if mir_version is not None and hasattr(features, 'mir_version'):
            features.mir_version = mir_version
        if confidence_score is not None and hasattr(features, 'confidence_score'):
            features.confidence_score = confidence_score

        features.analyzed_at = datetime.utcnow()
        features.date_modified = func.now()

        await self.session.commit()
        await self.session.refresh(features)
        logger.info(
            f"[AUDIO_FEATURES] Mises à jour avec MIR pour track_id={track_id}: "
            f"confidence={confidence_score}"
        )
        return features
