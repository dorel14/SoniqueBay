# -*- coding: utf-8 -*-
"""
Service LLM pour l'exposition des données MIR (Music Information Retrieval).

Rôle:
    Expose les données MIR formatées pour les LLMs (Ollama, agents conversationnels),
    permettant de générer des résumés, suggestions de recherche et prompts de playlists.

Dépendances:
    - backend.api.services.mir_normalization_service: MIRNormalizationService
    - backend.api.services.mir_scoring_service: MIRScoringService
    - backend.api.services.genre_taxonomy_service: GenreTaxonomyService
    - backend.api.services.synthetic_tags_service: SyntheticTagsService
    - sqlalchemy.ext.asyncio: AsyncSession

Auteur: SoniqueBay Team
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.utils.logging import logger


class MIRLLMService:
    """
    Service pour l'exposition des données MIR aux LLM.

    Ce service formate les données MIR (caractéristiques audio, scores, tags)
    pour les rendre exploitables par les LLMs dans le contexte conversationnel.

    Attributes:
        session: Session SQLAlchemy asynchrone pour les opérations DB

    Example:
        >>> async with async_session() as session:
        ...     service = MIRLLMService(session)
        ...     summary = await service.generate_track_summary(1)
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialise le service LLM MIR avec une session de base de données.

        Args:
            session: Session SQLAlchemy asynchrone
        """
        self.session = session
        logger.info("[MIR_LLM] Service LLM MIR initialisé")

    async def get_mir_data(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère toutes les données MIR pour une piste.

        Args:
            track_id: ID de la piste

        Returns:
            Dictionnaire contenant toutes les données MIR ou None si non trouvé
        """
        try:
            from backend.api.models.track_mir_raw_model import TrackMIRRaw
            from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
            from backend.api.models.track_mir_scores_model import TrackMIRScores
            from backend.api.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags
            from sqlalchemy import select

            # Récupérer les données MIR brutes
            raw_result = await self.session.execute(
                select(TrackMIRRaw).where(TrackMIRRaw.track_id == track_id)
            )
            raw_data = raw_result.scalars().first()

            # Récupérer les données normalisées
            normalized_result = await self.session.execute(
                select(TrackMIRNormalized).where(TrackMIRNormalized.track_id == track_id)
            )
            normalized_data = normalized_result.scalars().first()

            # Récupérer les scores
            scores_result = await self.session.execute(
                select(TrackMIRScores).where(TrackMIRScores.track_id == track_id)
            )
            scores_data = scores_result.scalars().first()

            # Récupérer les tags synthétiques
            tags_result = await self.session.execute(
                select(TrackMIRSyntheticTags).where(TrackMIRSyntheticTags.track_id == track_id)
            )
            synthetic_tags = tags_result.scalars().all()

            if not raw_data and not normalized_data:
                logger.warning(f"[MIR_LLM] Aucune donnée MIR pour track_id={track_id}")
                return None

            return {
                "raw": raw_data.features_raw if raw_data else None,
                "normalized": {
                    "bpm": normalized_data.bpm if normalized_data else None,
                    "key": normalized_data.key if normalized_data else None,
                    "scale": normalized_data.scale if normalized_data else None,
                    "danceability": normalized_data.danceability if normalized_data else None,
                    "mood_happy": normalized_data.mood_happy if normalized_data else None,
                    "mood_aggressive": normalized_data.mood_aggressive if normalized_data else None,
                    "mood_party": normalized_data.mood_party if normalized_data else None,
                    "mood_relaxed": normalized_data.mood_relaxed if normalized_data else None,
                    "instrumental": normalized_data.instrumental if normalized_data else None,
                    "acoustic": normalized_data.acoustic if normalized_data else None,
                    "tonal": normalized_data.tonal if normalized_data else None,
                    "genre_main": normalized_data.genre_main if normalized_data else None,
                    "camelot_key": normalized_data.camelot_key if normalized_data else None,
                } if normalized_data else None,
                "scores": {
                    "energy_score": scores_data.energy_score if scores_data else None,
                    "mood_valence": scores_data.mood_valence if scores_data else None,
                    "dance_score": scores_data.dance_score if scores_data else None,
                    "acousticness": scores_data.acousticness if scores_data else None,
                    "complexity_score": scores_data.complexity_score if scores_data else None,
                    "emotional_intensity": scores_data.emotional_intensity if scores_data else None,
                } if scores_data else None,
                "synthetic_tags": [
                    {"name": tag.tag_name, "score": tag.tag_score, "category": tag.tag_category}
                    for tag in synthetic_tags
                ],
                "source": raw_data.mir_source if raw_data else None,
                "version": raw_data.mir_version if raw_data else None,
            }

        except Exception as e:
            logger.error(f"[MIR_LLM] Erreur récupération données MIR: {e}")
            return None

    def generate_track_summary(self, track_id: int, mir_data: Dict[str, Any]) -> str:
        """
        Génère un résumé textuel de la piste pour les LLM.

        Args:
            track_id: ID de la piste
            mir_data: Données MIR de la piste

        Returns:
            Résumé textuel de la piste
        """
        normalized = mir_data.get("normalized", {})
        scores = mir_data.get("scores", {})
        tags = mir_data.get("synthetic_tags", [])
        source = mir_data.get("source", "unknown")

        # Déterminer le mood global
        mood_desc = []
        if normalized.get("mood_happy", 0) > 0.6:
            mood_desc.append("joyeux")
        elif normalized.get("mood_happy", 0) < 0.4:
            if normalized.get("mood_aggressive", 0) > 0.6:
                mood_desc.append("agressif")
            elif normalized.get("mood_relaxed", 0) > 0.6:
                mood_desc.append("relaxant")
            else:
                mood_desc.append("mélancolique")

        # Déterminer l'énergie
        energy = scores.get("energy_score", 0)
        if energy > 0.7:
            energy_desc = "énergique"
        elif energy > 0.4:
            energy_desc = "modérément énergétique"
        else:
            energy_desc = "calme"

        # Déterminer la danseabilité
        danceability = normalized.get("danceability", 0)
        if danceability > 0.7:
            dance_desc = "dansable"
        elif danceability > 0.4:
            dance_desc = "plutôt dansable"
        else:
            dance_desc = "peu dansable"

        # Construire le résumé
        summary_parts = []

        if normalized.get("genre_main"):
            summary_parts.append(f"un titre {normalized['genre_main']}")

        if mood_desc:
            summary_parts.append(f"au mood {' et '.join(mood_desc)}")

        summary_parts.append(f"{energy_desc}")
        summary_parts.append(f"et {dance_desc}")

        if normalized.get("bpm"):
            summary_parts.append(f"avec un BPM de {int(normalized['bpm'])}")

        if normalized.get("camelot_key"):
            summary_parts.append(f"(clé Camelot: {normalized['camelot_key']})")

        # Ajouter les tags synthétiques pertinents
        top_tags = [t["name"] for t in sorted(tags, key=lambda x: x["score"], reverse=True)[:5]]
        if top_tags:
            summary_parts.append(f"Tags: {', '.join(top_tags)}")

        summary = " ".join(summary_parts)

        logger.debug(f"[MIR_LLM] Résumé généré pour track_id={track_id}: {summary[:100]}...")

        return summary

    def generate_mir_context(self, track_id: int, mir_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère le contexte MIR structuré pour les prompts LLM.

        Args:
            track_id: ID de la piste
            mir_data: Données MIR de la piste

        Returns:
            Dictionnaire structuré du contexte MIR
        """
        normalized = mir_data.get("normalized", {})
        scores = mir_data.get("scores", {})
        tags = mir_data.get("synthetic_tags", [])

        context = {
            "genre": normalized.get("genre_main", "unknown"),
            "mood": self._get_mood_category(normalized),
            "energy": round(scores.get("energy_score", 0), 2),
            "danceability": round(normalized.get("danceability", 0), 2),
            "bpm": int(normalized.get("bpm")) if normalized.get("bpm") else None,
            "key": normalized.get("camelot_key") or normalized.get("key"),
            "synthetic_tags": [t["name"] for t in tags],
            "source": mir_data.get("source", "unknown"),
        }

        logger.debug(f"[MIR_LLM] Contexte MIR généré pour track_id={track_id}")

        return context

    def generate_search_query_suggestions(self, mir_data: Dict[str, Any]) -> List[str]:
        """
        Génère des suggestions de requêtes de recherche basées sur les données MIR.

        Args:
            mir_data: Données MIR de la piste

        Returns:
            Liste de suggestions de requêtes
        """
        normalized = mir_data.get("normalized", {})
        scores = mir_data.get("scores", {})
        tags = mir_data.get("synthetic_tags", [])

        suggestions = []

        # Suggestions basées sur le genre
        genre = normalized.get("genre_main")
        if genre:
            suggestions.append(f"musique {genre}")
            suggestions.append(f"{genre} pour danser" if normalized.get("danceability", 0) > 0.5 else f"{genre} chill")

        # Suggestions basées sur l'énergie
        energy = scores.get("energy_score", 0)
        if energy > 0.7:
            suggestions.append("musique énergique pour le sport")
            suggestions.append("pistes punchy et puissantes")
        elif energy < 0.4:
            suggestions.append("musique relaxante")
            suggestions.append("ambiance calme et sereine")

        # Suggestions basées sur le mood
        mood = self._get_mood_category(normalized)
        if mood == "happy":
            suggestions.append("musique joyeuse et positive")
        elif mood == "aggressive":
            suggestions.append("musique intense et agressive")
        elif mood == "relaxed":
            suggestions.append("musique douce et apaisante")

        # Suggestions basées sur les tags synthétiques
        for tag in tags[:3]:
            suggestions.append(f"pistes {tag['name']}")

        # Suggestions basées sur le BPM
        bpm = normalized.get("bpm")
        if bpm:
            if bpm > 120:
                suggestions.append(f"musique rapide BPM {int(bpm)}+")
            elif bpm < 100:
                suggestions.append(f"musique lente BPM {int(bpm)}-")

        logger.debug(
            f"[MIR_LLM] {len(suggestions)} suggestions générées"
        )

        return suggestions[:10]  # Limiter à 10 suggestions

    def generate_playlist_prompts(self, mir_data: Dict[str, Any]) -> List[str]:
        """
        Génère des prompts pour la création de playlists basées sur les données MIR.

        Args:
            mir_data: Données MIR de la piste

        Returns:
            Liste de prompts pour playlists
        """
        normalized = mir_data.get("normalized", {})
        scores = mir_data.get("scores", {})
        tags = mir_data.get("synthetic_tags", [])

        prompts = []

        genre = normalized.get("genre_main", "musique")
        mood = self._get_mood_category(normalized)
        energy = scores.get("energy_score", 0)
        danceability = normalized.get("danceability", 0)

        # Prompt principal basé sur le mood et l'énergie
        if energy > 0.7:
            prompts.append(f"Playlist {genre} énergétique pour le sport ou une soirée")
            prompts.append(f"Mix {genre} punchy et puissant pour te motiver")
        elif energy < 0.4:
            prompts.append(f"Playlist {genre} chill pour la relaxation")
            prompts.append(f"Musique {genre} douce pour travailler ou méditer")
        else:
            prompts.append(f"Playlist {genre} équilibrée entre énergie et calme")

        # Prompt basé sur la danseabilité
        if danceability > 0.7:
            prompts.append(f"Playlist {genre} pour danser toute la nuit")
            prompts.append(f"Mix {genre} avec un bon beat pour faire la fête")

        # Prompt basé sur les tags
        top_tags = [t["name"] for t in sorted(tags, key=lambda x: x["score"], reverse=True)[:3]]
        if top_tags:
            prompts.append(f"Playlist {genre} avec des vibes {', '.join(top_tags)}")

        # Prompt basé sur le BPM
        bpm = normalized.get("bpm")
        if bpm:
            if 100 <= bpm <= 130:
                prompts.append(f"Playlist {genre} au tempo optimal (~{int(bpm)} BPM)")
            elif bpm > 140:
                prompts.append(f"Playlist {genre} rapide et intense ({int(bpm)} BPM)")

        logger.debug(
            f"[MIR_LLM] {len(prompts)} prompts de playlists générés"
        )

        return prompts

    def _get_mood_category(self, normalized: Dict[str, Any]) -> str:
        """
        Détermine la catégorie de mood dominante.

        Args:
            normalized: Données MIR normalisées

        Returns:
            Catégorie de mood: "happy", "aggressive", "relaxed", "party", ou "neutral"
        """
        moods = {
            "happy": normalized.get("mood_happy", 0),
            "aggressive": normalized.get("mood_aggressive", 0),
            "relaxed": normalized.get("mood_relaxed", 0),
            "party": normalized.get("mood_party", 0),
        }

        max_mood = max(moods, key=moods.get)
        if moods[max_mood] > 0.5:
            return max_mood
        return "neutral"

    async def generate_track_description_for_llm(
        self,
        track_id: int,
        track_title: str,
        artist_name: str,
        album_name: Optional[str] = None,
    ) -> str:
        """
        Génère une description complète de la piste pour les LLM.

        Args:
            track_id: ID de la piste
            track_title: Titre de la piste
            artist_name: Nom de l'artiste
            album_name: Nom de l'album (optionnel)

        Returns:
            Description formatée pour les LLM
        """
        # Récupérer les données MIR
        mir_data = await self.get_mir_data(track_id)

        if not mir_data:
            return f"Piste '{track_title}' par {artist_name}"

        # Générer le résumé MIR
        mir_summary = self.generate_track_summary(track_id, mir_data)

        # Construire la description complète
        parts = [f"Piste: '{track_title}'"]
        parts.append(f"Artiste: {artist_name}")

        if album_name:
            parts.append(f"Album: {album_name}")

        if mir_summary:
            parts.append(f"Caractéristiques MIR: {mir_summary}")

        description = " | ".join(parts)

        logger.debug(f"[MIR_LLM] Description générée pour track_id={track_id}")

        return description
