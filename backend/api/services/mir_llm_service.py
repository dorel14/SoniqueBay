# -*- coding: utf-8 -*-
"""
Service LLM pour l'exposition des données MIR (Music Information Retrieval).

Rôle:
    Expose les données MIR formatées pour les LLMs (Ollama, agents conversationnels),
    permettant de générer des résumés, suggestions de recherche et prompts de playlists.
    Intègre les synonyms dynamiques pour enrichir le contexte musical.

Dépendances:
    - backend.api.services.genre_taxonomy_service: GenreTaxonomyService
    - backend.api.services.synthetic_tags_service: SyntheticTagsService
    - backend.api.services.mir_synonym_service: MIRSynonymService
    - sqlalchemy.ext.asyncio: AsyncSession

Auteur: SoniqueBay Team
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.utils.logging import logger


class MIRLLMService:
    """
    Service pour l'exposition des données MIR aux LLM avec synonyms dynamiques.

    Ce service formate les données MIR (caractéristiques audio, scores, tags)
    pour les rendre exploitables par les LLMs dans le contexte conversationnel.
    Il intègre également les synonyms dynamiques pour enrichir le contexte musical.

    Attributes:
        session: Session SQLAlchemy asynchrone pour les opérations DB
        synonym_service: Service MIRSynonymService optionnel pour les synonyms

    Example:
        >>> async with async_session() as session:
        ...     service = MIRLLMService(session)
        ...     summary = await service.generate_track_summary(1)
        ...     context = await service.get_music_context_for_llm(1)
    """

    # Termes de fallback pour la rétrocompatibilité
    DEFAULT_GENRE_SYNONYMS: Dict[str, List[str]] = {
        "rock": ["rock", "hard rock", "classic rock"],
        "electronic": ["electronic", "electro", "edm", "techno"],
        "pop": ["pop", "popular", "mainstream"],
        "jazz": ["jazz", "swing", "bebop"],
        "classical": ["classical", "orchestral", "symphony"],
        "hip-hop": ["hip-hop", "rap", "hip hop"],
        "metal": ["metal", "heavy metal", "thrash"],
        "indie": ["indie", "independent", "alternative"],
    }

    DEFAULT_MOOD_SYNONYMS: Dict[str, List[str]] = {
        "happy": ["happy", "joyful", "upbeat", "cheerful"],
        "sad": ["sad", "melancholic", "emotional", "touching"],
        "energetic": ["energetic", "powerful", "punchy", "dynamic"],
        "relaxed": ["relaxed", "chill", "calm", "peaceful"],
        "aggressive": ["aggressive", "intense", "hard", "heavy"],
        "party": ["party", "danceable", "club", "fun"],
    }

    def __init__(
        self,
        session: AsyncSession,
        synonym_service: Optional[Any] = None,
    ) -> None:
        """
        Initialise le service LLM MIR avec une session de base de données.

        Args:
            session: Session SQLAlchemy asynchrone
            synonym_service: Service MIRSynonymService optionnel pour les synonyms dynamiques
        """
        self.session = session
        self.synonym_service = synonym_service
        logger.info("[MIR_LLM] Service LLM MIR initialisé")

    def _get_fallback_synonyms(
        self, tag_type: str, tag_value: str
    ) -> Dict[str, Any]:
        """
        Récupère les synonyms de fallback codés en dur.

        Args:
            tag_type: Type de tag ('genre' ou 'mood')
            tag_value: Valeur du tag

        Returns:
            Dictionnaire avec search_terms et related_tags
        """
        synonyms_dict = (
            self.DEFAULT_GENRE_SYNONYMS
            if tag_type == "genre"
            else self.DEFAULT_MOOD_SYNONYMS
        )

        # Chercher une correspondance exacte ou partielle
        tag_lower = tag_value.lower()

        # Recherche exacte
        if tag_lower in synonyms_dict:
            return {
                "search_terms": synonyms_dict[tag_lower],
                "related_tags": [],
                "source": "fallback",
                "confidence": 0.5,
            }

        # Recherche partielle
        for key, values in synonyms_dict.items():
            if tag_lower in key or key in tag_lower:
                return {
                    "search_terms": values,
                    "related_tags": [],
                    "source": "fallback",
                    "confidence": 0.4,
                }

        # Retour par défaut
        return {
            "search_terms": [tag_value],
            "related_tags": [],
            "source": "fallback",
            "confidence": 0.3,
        }

    async def _get_synonyms_for_context(
        self, tag_type: str, tag_value: str
    ) -> Dict[str, Any]:
        """
        Récupère les synonyms pour enrichir le contexte LLM.

        Essaie d'abord le service MIRSynonymService, puis fallback sur les
        synonyms codés en dur.

        Args:
            tag_type: Type de tag ('genre' ou 'mood')
            tag_value: Valeur du tag

        Returns:
            Dict avec search_terms, related_tags, source et confidence
        """
        try:
            if self.synonym_service:
                # Utiliser le service de synonyms dynamique
                synonym_data = await self.synonym_service.get_synonyms(
                    tag_type, tag_value
                )

                if synonym_data:
                    logger.debug(
                        f"[MIR_LLM] Synonyms dynamiques trouvés pour {tag_type}:{tag_value}"
                    )
                    return {
                        "search_terms": synonym_data.get(
                            "search_terms", synonym_data.get("synonyms", {}).get("search_terms", [])
                        ),
                        "related_tags": synonym_data.get(
                            "related_tags", synonym_data.get("synonyms", {}).get("related_tags", [])
                        ),
                        "usage_contexts": synonym_data.get(
                            "usage_contexts", synonym_data.get("synonyms", {}).get("usage_contexts", [])
                        ),
                        "translations": synonym_data.get("translations", {}),
                        "source": synonym_data.get("source", "dynamic"),
                        "confidence": synonym_data.get("confidence", 0.7),
                    }

            # Fallback sur les synonyms codés
            fallback = self._get_fallback_synonyms(tag_type, tag_value)
            logger.debug(
                f"[MIR_LLM] Utilisation fallback pour {tag_type}:{tag_value}"
            )
            return fallback

        except Exception as e:
            logger.warning(
                f"[MIR_LLM] Erreur récupération synonyms {tag_type}:{tag_value}: {e}"
            )
            return self._get_fallback_synonyms(tag_type, tag_value)

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

    async def get_music_context_for_llm(self, track_id: int) -> Dict[str, Any]:
        """
        Récupère le contexte musical enrichi avec synonyms dynamiques pour un track.

        Args:
            track_id: ID de la piste

        Returns:
            Contexte enrichi avec search_terms et related_tags
        """
        # Récupérer les données MIR existantes
        mir_data = await self.get_mir_data(track_id)

        if not mir_data:
            return {"error": "Aucune donnée MIR disponible"}

        # Générer le contexte de base
        context = self.generate_mir_context(track_id, mir_data)

        # Enrichir avec les synonyms dynamiques
        normalized = mir_data.get("normalized", {})

        # Enrichir avec les synonyms du genre
        genre = normalized.get("genre_main")
        if genre:
            genre_synonyms = await self._get_synonyms_for_context("genre", genre)
            context["genre_synonyms"] = genre_synonyms
            context["search_terms_genre"] = genre_synonyms.get("search_terms", [])

        # Enrichir avec les synonyms du mood dominant
        mood = context.get("mood")
        if mood and mood != "neutral":
            mood_synonyms = await self._get_synonyms_for_context("mood", mood)
            context["mood_synonyms"] = mood_synonyms
            context["search_terms_mood"] = mood_synonyms.get("search_terms", [])

        # Construire les search terms combinés
        all_search_terms = []
        if context.get("search_terms_genre"):
            all_search_terms.extend(context["search_terms_genre"])
        if context.get("search_terms_mood"):
            all_search_terms.extend(context["search_terms_mood"])

        context["combined_search_terms"] = list(set(all_search_terms))

        logger.debug(f"[MIR_LLM] Contexte enrichi pour track_id={track_id}")

        return context

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

    def generate_search_query_suggestions(
        self, mir_data: Dict[str, Any], synonyms_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Génère des suggestions de requêtes de recherche basées sur les données MIR
        et les synonyms dynamiques.

        Args:
            mir_data: Données MIR de la piste
            synonyms_context: Contexte des synonyms (optionnel)

        Returns:
            Liste de suggestions de requêtes enrichies
        """
        normalized = mir_data.get("normalized", {})
        scores = mir_data.get("scores", {})
        tags = mir_data.get("synthetic_tags", [])

        suggestions = []

        # Suggestions basées sur le genre avec synonyms
        genre = normalized.get("genre_main")
        if genre:
            suggestions.append(f"musique {genre}")
            suggestions.append(f"{genre} pour danser" if normalized.get("danceability", 0) > 0.5 else f"{genre} chill")

            # Enrichir avec les synonyms du genre
            if synonyms_context and "genre_synonyms" in synonyms_context:
                genre_synonyms = synonyms_context["genre_synonyms"]
                for term in genre_synonyms.get("search_terms", [])[:2]:
                    if term != genre:
                        suggestions.append(f"musique {term}")

        # Suggestions basées sur l'énergie
        energy = scores.get("energy_score", 0)
        if energy > 0.7:
            suggestions.append("musique énergique pour le sport")
            suggestions.append("pistes punchy et puissantes")
        elif energy < 0.4:
            suggestions.append("musique relaxante")
            suggestions.append("ambiance calme et sereine")

        # Suggestions basées sur le mood avec synonyms
        mood = self._get_mood_category(normalized)
        if mood == "happy":
            suggestions.append("musique joyeuse et positive")
        elif mood == "aggressive":
            suggestions.append("musique intense et agressive")
        elif mood == "relaxed":
            suggestions.append("musique douce et apaisante")

        # Enrichir avec les synonyms du mood
        if synonyms_context and "mood_synonyms" in synonyms_context:
            mood_synonyms = synonyms_context["mood_synonyms"]
            for term in mood_synonyms.get("search_terms", [])[:2]:
                if term.lower() != mood.lower():
                    suggestions.append(f"musique {term}")

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

        logger.debug(f"[MIR_LLM] {len(suggestions)} suggestions générées")

        return suggestions[:10]  # Limiter à 10 suggestions

    def generate_playlist_prompts(
        self, mir_data: Dict[str, Any], synonyms_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Génère des prompts pour la création de playlists basées sur les données MIR
        et les synonyms dynamiques.

        Args:
            mir_data: Données MIR de la piste
            synonyms_context: Contexte des synonyms (optionnel)

        Returns:
            Liste de prompts pour playlists enrichis
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

        # Enrichir avec les synonyms
        if synonyms_context:
            genre_synonyms = synonyms_context.get("genre_synonyms", {})
            mood_synonyms = synonyms_context.get("mood_synonyms", {})

            # Combiner les synonyms dans un prompt enrichi
            combined_terms = []
            combined_terms.extend(genre_synonyms.get("search_terms", [])[:2])
            combined_terms.extend(mood_synonyms.get("search_terms", [])[:2])

            if combined_terms:
                unique_terms = list(set(combined_terms))
                prompts.append(
                    f"Playlist {genre} avec les ambiances: {', '.join(unique_terms)}"
                )

        logger.debug(f"[MIR_LLM] {len(prompts)} prompts de playlists générés")

        return prompts

    def generate_synonym_enriched_prompt(
        self,
        prompt_template: str,
        context: Dict[str, Any],
        placeholder: str = "{synonyms}",
    ) -> str:
        """
        Génère un prompt enrichi avec les synonyms dynamiques.

        Args:
            prompt_template: Template du prompt avec placeholder pour les synonyms
            context: Contexte musical contenant les synonyms
            placeholder: Placeholder template

        Returns à remplacer dans le:
            Prompt enrichi avec les synonyms
        """
        # Extraire les synonyms du contexte
        synonyms_parts = []

        # Ajouter les search terms du genre
        genre_synonyms = context.get("genre_synonyms", {})
        search_terms_genre = genre_synonyms.get("search_terms", [])
        if search_terms_genre:
            synonyms_parts.append(f"Genres/Tags associés: {', '.join(search_terms_genre)}")

        # Ajouter les search terms du mood
        mood_synonyms = context.get("mood_synonyms", {})
        search_terms_mood = mood_synonyms.get("search_terms", [])
        if search_terms_mood:
            synonyms_parts.append(f"Ambiances/Moods: {', '.join(search_terms_mood)}")

        # Ajouter les related tags
        related_tags_genre = genre_synonyms.get("related_tags", [])
        related_tags_mood = mood_synonyms.get("related_tags", [])
        all_related = list(set(related_tags_genre + related_tags_mood))
        if all_related:
            synonyms_parts.append(f"Tags connexes: {', '.join(all_related)}")

        # Construire la chaîne de synonyms
        if synonyms_parts:
            synonyms_str = " | ".join(synonyms_parts)
        else:
            # Fallback sur les combined_search_terms
            combined_terms = context.get("combined_search_terms", [])
            synonyms_str = f"Termes de recherche: {', '.join(combined_terms)}" if combined_terms else ""

        # Remplacer le placeholder
        enriched_prompt = prompt_template.replace(placeholder, synonyms_str)

        logger.debug("[MIR_LLM] Prompt enrichi généré")

        return enriched_prompt

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
        include_synonyms: bool = True,
    ) -> str:
        """
        Génère une description complète de la piste pour les LLM.

        Args:
            track_id: ID de la piste
            track_title: Titre de la piste
            artist_name: Nom de l'artiste
            album_name: Nom de l'album (optionnel)
            include_synonyms: Inclure les synonyms dans la description

        Returns:
            Description formatée pour les LLM
        """
        # Récupérer les données MIR
        mir_data = await self.get_mir_data(track_id)

        if not mir_data:
            return f"Piste '{track_title}' par {artist_name}"

        # Générer le résumé MIR
        mir_summary = self.generate_track_summary(track_id, mir_data)

        # Récupérer le contexte enrichi avec synonyms
        synonyms_context = None
        if include_synonyms:
            synonyms_context = await self.get_music_context_for_llm(track_id)

        # Construire la description complète
        parts = [f"Piste: '{track_title}'"]
        parts.append(f"Artiste: {artist_name}")

        if album_name:
            parts.append(f"Album: {album_name}")

        if mir_summary:
            parts.append(f"Caractéristiques MIR: {mir_summary}")

        # Ajouter les synonyms si demandé
        if include_synonyms and synonyms_context:
            combined_terms = synonyms_context.get("combined_search_terms", [])
            if combined_terms:
                parts.append(f"Termes de recherche associés: {', '.join(combined_terms)}")

        description = " | ".join(parts)

        logger.debug(f"[MIR_LLM] Description générée pour track_id={track_id}")

        return description
