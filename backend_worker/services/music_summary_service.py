"""Service de résumé musical (Music Summary Service).

Ce service génère un résumé complet d'un track musical en synthétisant les données
des autres services MIR (normalization, scoring, synthetic tags).

Le résumé inclut:
- Les tags sources avec métadonnées
- Les caractéristiques normalisées
- Les scores calculés
- Les tags synthétiques générés
- Un résumé textuel descriptif
- Le contexte musical
- Des suggestions de recherche

Ce service utilise désormais les synonyms dynamiques via l'API REST plutôt que
des dictionnaires codés en dur, permettant une recherche plus riche et extensible.

Auteur: SoniqueBay Team
Version: 1.1.0 - Refactorisé pour utiliser les synonyms dynamiques via Ollama
"""

import os
from typing import Optional

import httpx

from backend_worker.utils.logging import logger


class MusicSummaryService:
    """Service pour la génération de résumés musicaux avec synonyms dynamiques.
    
    Ce service agrège les données de plusieurs sources MIR pour créer un résumé
    complet et cohérent d'un track musical. Il est utilisé par:
    
    - Le moteur de recommandations (contexte des tracks)
    - L'interface utilisateur (affichage des caractéristiques)
    - L'agent IA (contexte pour les conversations)
    - La recherche (suggestions basées sur les caractéristiques)
    
    Relations avec autres services:
    - MIRNormalizationService: pour les caractéristiques normalisées
    - MIRScoringService: pour les scores globaux
    - SyntheticTagsService: pour les tags synthétiques
    - OllamaSynonymService: pour les termes de recherche dynamiques (via API REST)
    """
    
    # Configuration API
    LIBRARY_API_URL = os.getenv("API_URL", "http://api:8001")
    API_TIMEOUT = 30  # secondes
    
    # Mapping des genres vers les termes de recherche associés (FALLBACK)
    GENRE_SEARCH_TERMS = {
        'rock': ['rock', 'rock classique', 'rock alternatif', 'rock indé'],
        'pop': ['pop', 'musique pop', 'pop moderne', 'tubes pop'],
        'jazz': ['jazz', 'musique jazz', 'jazz moderne', 'smooth jazz'],
        'classical': ['classique', 'musique classique', 'classique moderne'],
        'electronic': ['électronique', 'EDM', 'musique electronique', 'dance'],
        'hip-hop': ['hip-hop', 'rap', 'urbain', 'street'],
        'metal': ['metal', 'heavy metal', 'metal alternatif'],
        'indie': ['indie', 'musique indé', 'alternatif indé'],
        'alternative': ['alternatif', 'alternative rock', 'musique alternative'],
        'folk': ['folk', 'musique folk', 'folk acoustique'],
        'country': ['country', 'musique country', 'country moderne'],
        'reggae': ['reggae', 'musique reggae', 'reggae roots'],
        'blues': ['blues', 'blues rock', 'blues acoustique'],
        'soul': ['soul', 'musique soul', 'neo soul'],
        'funk': ['funk', 'musique funk', 'funk moderne'],
        'rnb': ['R&B', 'RnB', 'musique R&B'],
        'world': ['world', 'musique du monde', 'international'],
    }
    
    # Mapping des moods vers les termes de recherche (FALLBACK)
    MOOD_SEARCH_TERMS = {
        'happy': ['musique joyeuse', 'titres gais', 'bonne humeur'],
        'sad': ['musique mélancolique', 'titres tristes', 'émotion'],
        'energetic': ['musique énergétique', 'titres dynamiques', 'punchy'],
        'chill': ['musique relaxante', 'titres chill', 'détente'],
        'aggressive': ['musique intense', 'titres puissants', 'énergique'],
        'dark': ['musique sombre', 'atmosphère dark', 'titres mystérieux'],
        'bright': ['musique lumineuse', 'titres positifs', 'ambiance lumineuse'],
        'uplifting': ['musique motivante', 'titres uplifting', 'ambiance positive'],
    }
    
    # Mapping des usages vers les termes de recherche (FALLBACK)
    USAGE_SEARCH_TERMS = {
        'workout': ['musique pour le sport', 'titres entraînement', 'sport music'],
        'focus': ['musique pour la concentration', 'titres focus', 'travail'],
        'party': ['musique party', 'titres fête', 'dance'],
        'background': ["musique d'arrière-plan", 'ambiance', 'titres doux'],
        'workout': ['musique pour le sport', 'musique énergétique', 'entraînement'],
    }
    
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        """Initialise le service de résumé musical.
        
        Args:
            http_client: Client HTTP async optionnel. Si non fourni, un nouveau
                        instance sera créée lors des appels API.
        """
        self._http_client = http_client
        self._synonym_cache: dict[str, dict] = {}  # Cache en mémoire pour les synonyms
        logger.info("[MusicSummaryService] Service de résumé musical initialisé")
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Récupère ou crée le client HTTP async.
        
        Returns:
            Client HTTP async prêt pour les appels API
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self.API_TIMEOUT)
        return self._http_client
    
    async def _close(self) -> None:
        """Ferme les ressources du service (client HTTP)."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("[MusicSummaryService] Client HTTP fermé")
    
    def _get_cache_key(self, tag_type: str, tag_value: str) -> str:
        """Génère une clé de cache pour un tag.
        
        Args:
            tag_type: Type de tag ('genre', 'mood', 'usage')
            tag_value: Valeur du tag
            
        Returns:
            Clé de cache unique
        """
        return f"{tag_type}:{tag_value.lower()}"
    
    async def _get_synonyms(self, tag_type: str, tag_value: str) -> Optional[dict]:
        """Récupère les synonyms via l'API REST.
        
        Cette méthode interroge l'endpoint GET /api/synonyms/{tag_type}/{tag_value}
        pour obtenir les termes de recherche dynamiques générés par Ollama.
        
        Args:
            tag_type: 'genre', 'mood' ou 'usage'
            tag_value: Nom du tag
            
        Returns:
            Dict des synonyms contenant 'search_terms', 'related_tags', etc.
            ou None si pas trouvé ou erreur API
        """
        cache_key = self._get_cache_key(tag_type, tag_value)
        
        # Vérifier le cache en mémoire
        if cache_key in self._synonym_cache:
            logger.debug(f"[MusicSummaryService] Cache hit pour {cache_key}")
            return self._synonym_cache[cache_key]
        
        try:
            client = self._get_http_client()
            url = f"{self.LIBRARY_API_URL}/api/synonyms/{tag_type}/{tag_value}"
            
            logger.debug(f"[MusicSummaryService] Appel API: GET {url}")
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                synonyms = {
                    'search_terms': data.get('search_terms', []),
                    'related_tags': data.get('related_tags', {}),
                    'usage_context': data.get('usage_contexts', []),
                    'translations': data.get('translations', {}),
                    'confidence': data.get('confidence', 1.0),
                }
                # Stocker dans le cache
                self._synonym_cache[cache_key] = synonyms
                logger.info(f"[MusicSummaryService] Synonyms récupérés pour {cache_key}")
                return synonyms
            elif response.status_code == 404:
                logger.debug(f"[MusicSummaryService] Pas de synonyms pour {cache_key}")
                return None
            else:
                logger.warning(
                    f"[MusicSummaryService] Erreur API {response.status_code} "
                    f"pour {cache_key}"
                )
                return None
                
        except httpx.RequestError as e:
            logger.error(f"[MusicSummaryService] Erreur requête API: {e}")
            return None
        except Exception as e:
            logger.error(f"[MusicSummaryService] Erreur inattendue: {e}")
            return None
    
    async def _search_synonyms(
        self, query: str, tag_type: Optional[str] = None
    ) -> list[dict]:
        """Recherche de synonyms via l'API REST avec recherche hybride.
        
        Cette méthode utilise l'endpoint GET /api/synonyms/search pour effectuer
        une recherche hybride combinant FTS PostgreSQL et recherche vectorielle.
        
        Args:
            query: Terme de recherche
            tag_type: Optionnel, filtrer par type ('genre' ou 'mood')
            
        Returns:
            Liste de dictionnaires contenant les synonyms trouvés
        """
        try:
            client = self._get_http_client()
            params = {'q': query}
            if tag_type:
                params['tag_type'] = tag_type
            
            url = f"{self.LIBRARY_API_URL}/api/synonyms/search"
            logger.debug(f"[MusicSummaryService] Recherche API: {url}?{params}")
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                logger.info(
                    f"[MusicSummaryService] {len(results)} résultats pour '{query}'"
                )
                return results
            else:
                logger.warning(
                    f"[MusicSummaryService] Erreur recherche API {response.status_code}"
                )
                return []
                
        except httpx.RequestError as e:
            logger.error(f"[MusicSummaryService] Erreur requête search: {e}")
            return []
        except Exception as e:
            logger.error(f"[MusicSummaryService] Erreur search inattendue: {e}")
            return []
    
    def _extract_search_terms(self, synonyms: Optional[dict]) -> list[str]:
        """Extrait les termes de recherche d'un dict de synonyms.
        
        Args:
            synonyms: Dict des synonyms (search_terms, related_tags, etc.)
            
        Returns:
            Liste aplatie et dédupliquée des termes de recherche
        """
        if not synonyms:
            return []
        
        terms = []
        
        # Extraire search_terms
        search_terms = synonyms.get('search_terms', [])
        if isinstance(search_terms, list):
            terms.extend(search_terms)
        
        # Aplatir related_tags
        related_tags = synonyms.get('related_tags', {})
        if isinstance(related_tags, dict):
            for tag_list in related_tags.values():
                if isinstance(tag_list, list):
                    terms.extend(tag_list)
        
        # Extraire usage_context
        usage_context = synonyms.get('usage_context', [])
        if isinstance(usage_context, list):
            terms.extend(usage_context)
        
        # Retourner une liste dédupliquée en préservant l'ordre
        return list(dict.fromkeys(terms))
    
    def _get_fallback_terms(
        self, tag_type: str, tag_value: str, category: str = 'genre'
    ) -> list[str]:
        """Récupère les termes de recherche depuis le fallback hardcodé.
        
        Args:
            tag_type: Type de tag
            tag_value: Valeur du tag
            category: Catégorie ('genre', 'mood', 'usage')
            
        Returns:
            Liste des termes de recherche
        """
        tag_lower = tag_value.lower()
        
        if category == 'genre':
            return self.GENRE_SEARCH_TERMS.get(tag_lower, [])
        elif category == 'mood':
            return self.MOOD_SEARCH_TERMS.get(tag_lower, [])
        elif category == 'usage':
            return self.USAGE_SEARCH_TERMS.get(tag_lower, [])
        
        return []
    
    async def _get_search_terms(
        self, tag_type: str, tag_value: str, category: str = 'genre'
    ) -> list[str]:
        """Récupère les termes de recherche avec fallback.
        
        Tente d'abord d'obtenir les synonyms via l'API, puis utilise
        les dictionnaires hardcodés en cas d'échec.
        
        Args:
            tag_type: Type de tag ('genre', 'mood', 'usage')
            tag_value: Valeur du tag
            category: Catégorie pour le fallback
            
        Returns:
            Liste des termes de recherche
        """
        # Essayer d'abord l'API dynamique
        synonyms = await self._get_synonyms(tag_type, tag_value)
        
        if synonyms:
            terms = self._extract_search_terms(synonyms)
            if terms:
                logger.debug(
                    f"[MusicSummaryService] Terms dynamiques pour "
                    f"{tag_type}:{tag_value}: {len(terms)} termes"
                )
                return terms
        
        # Fallback sur les dictionnaires hardcodés
        terms = self._get_fallback_terms(tag_type, tag_value, category)
        logger.debug(
            f"[MusicSummaryService] Terms fallback pour "
            f"{tag_type}:{tag_value}: {len(terms)} termes"
        )
        return terms
    
    def _format_key_display(
        self, key: Optional[str], scale: Optional[str],
        camelot_key: Optional[str]
    ) -> str:
        """Formate l'affichage de la tonalité.
        
        Args:
            key: Tonalité (C, C#, etc.)
            scale: Mode (major, minor)
            camelot_key: Clé Camelot (8B, 5Am, etc.)
            
        Returns:
            Chaîne formatée de la tonalité
        """
        parts = []
        if key:
            parts.append(key.upper())
        if scale:
            parts.append(scale.capitalize())
        if camelot_key:
            parts.append(f"({camelot_key})")
        
        return " ".join(parts) if parts else "Inconnue"
    
    def _get_mood_from_features(self, normalized: dict) -> Optional[str]:
        """Détermine le mood principal à partir des caractéristiques.
        
        Args:
            normalized: Caractéristiques normalisées
            
        Returns:
            Mood principal ou None
        """
        moods = {
            'happy': normalized.get('mood_happy'),
            'aggressive': normalized.get('mood_aggressive'),
            'party': normalized.get('mood_party'),
            'relaxed': normalized.get('mood_relaxed'),
        }
        
        # Prendre le mood avec le score le plus élevé
        valid_moods = {k: v for k, v in moods.items() if v is not None and v > 0.3}
        
        if valid_moods:
            return max(valid_moods.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _get_energy_level(self, energy_score: Optional[float]) -> Optional[str]:
        """Détermine le niveau d'énergie à partir du score.
        
        Args:
            energy_score: Score d'énergie [0.0-1.0]
            
        Returns:
            Niveau d'énergie ou None
        """
        if energy_score is None:
            return None
        
        if energy_score > 0.7:
            return 'high'
        elif energy_score < 0.3:
            return 'low'
        else:
            return 'medium'
    
    def generate_summary_text(
        self, normalized: dict, synthetic_tags: list[dict],
        track_info: Optional[dict] = None
    ) -> str:
        """Génère un résumé textuel du track.
        
        Args:
            normalized: Caractéristiques normalisées
            synthetic_tags: Tags synthétiques générés
            track_info: Informations optionnelles sur le track
            
        Returns:
            Résumé textuel descriptif
        """
        parts = []
        
        # Genre principal
        genre = normalized.get('genre_main')
        if genre:
            parts.append(f"un titre {genre}")
        
        # Mood
        mood = self._get_mood_from_features(normalized)
        if mood:
            mood_labels = {
                'happy': 'au mood joyeux',
                'aggressive': 'au mood agressif',
                'party': 'festif',
                'relaxed': 'détendu',
            }
            mood_label = mood_labels.get(mood, f"au mood {mood}")
            parts.append(mood_label)
        
        # Energy keywords
        energy_score = normalized.get('energy_score')
        if energy_score:
            if energy_score > 0.7:
                parts.append('énergétique')
            elif energy_score < 0.4:
                parts.append('calme')
        
        # Danceability
        danceability = normalized.get('danceability')
        if danceability and danceability > 0.6:
            parts.append('plutôt dansable')
        
        # BPM
        bpm = normalized.get('bpm')
        if bpm:
            bpm_int = int(bpm)
            if bpm_int > 120:
                parts.append(f"avec un tempo de {bpm_int} BPM")
        
        # Camelot key
        camelot_key = normalized.get('camelot_key')
        if camelot_key:
            parts.append(f"(clé Camelot: {camelot_key})")
        
        # Top synthetic tags
        if synthetic_tags:
            top_tags = [t['tag'] for t in sorted(
                synthetic_tags, key=lambda x: x.get('score', 0), reverse=True
            )][:2]
            if top_tags:
                parts.append(f"Tags: {', '.join(top_tags)}")
        
        # Construire le résumé
        if parts:
            # Insérer "un titre" au début si pas déjà présent
            if not parts[0].startswith('un titre'):
                summary = ", ".join(parts)
            else:
                summary = ", ".join(parts)
        else:
            summary = "un titre musical"
        
        return summary
    
    def generate_context(
        self, track_id: int, normalized: dict, scores: dict,
        synthetic_tags: list[dict], source: str
    ) -> dict:
        """Génère le contexte musical complet d'un track.
        
        Args:
            track_id: Identifiant du track
            normalized: Caractéristiques normalisées
            scores: Scores calculés
            synthetic_tags: Tags synthétiques
            source: Source des données MIR
            
        Returns:
            Dictionnaire du contexte musical
        """
        context = {
            'track_id': track_id,
            'genre': normalized.get('genre_main'),
            'mood': self._get_mood_from_features(normalized),
            'energy': scores.get('energy_score'),
            'danceability': normalized.get('danceability'),
            'bpm': normalized.get('bpm'),
            'key': self._format_key_display(
                normalized.get('key'),
                normalized.get('scale'),
                normalized.get('camelot_key')
            ),
            'camelot_key': normalized.get('camelot_key'),
            'synthetic_tags': [t['tag'] for t in synthetic_tags],
            'source': source,
            'confidence_score': normalized.get('confidence_score', 0.0),
        }
        
        # Ajouter les genres secondaires
        if normalized.get('genre_secondary'):
            context['genre_secondary'] = normalized['genre_secondary']
        
        # Ajouter les scores principaux
        context['scores'] = {
            'energy': scores.get('energy_score'),
            'valence': scores.get('valence'),
            'dance': scores.get('dance_score'),
            'intensity': scores.get('emotional_intensity'),
        }
        
        return context
    
    async def generate_search_suggestions(
        self, normalized: dict, synthetic_tags: list[dict],
        track_title: Optional[str] = None
    ) -> list[str]:
        """Génère des suggestions de recherche basées sur les caractéristiques.
        
        Cette méthode utilise désormais les synonyms dynamiques via l'API REST
        pour obtenir des termes de recherche plus riches et contextuels, avec
        fallback sur les dictionnaires hardcodés en cas d'indisponibilité.
        
        Args:
            normalized: Caractéristiques normalisées
            synthetic_tags: Tags synthétiques
            track_title: Titre optionnel du track
            
        Returns:
            Liste de suggestions de recherche
        """
        suggestions = set()
        
        # Genre principal
        genre = normalized.get('genre_main')
        if genre:
            genre_lower = genre.lower()
            
            # Utiliser les synonyms dynamiques pour le genre
            genre_terms = await self._get_search_terms(
                'genre', genre_lower, category='genre'
            )
            suggestions.update(genre_terms)
            
            # Suggestions génériques par genre (fallback)
            if genre_lower in ['rock', 'metal']:
                suggestions.add(f"musique {genre_lower}")
                suggestions.add(f"{genre_lower} puissant")
                suggestions.add(f"{genre_lower} energetique")
            elif genre_lower in ['pop', 'dance', 'electronic']:
                suggestions.add(f"musique {genre_lower}")
                suggestions.add(f"{genre_lower} dansant")
                suggestions.add(f"{genre_lower} pour faire la fête")
            elif genre_lower in ['jazz', 'blues', 'soul']:
                suggestions.add(f"musique {genre_lower}")
                suggestions.add(f"{genre_lower} instrumental")
        
        # Mood
        mood = self._get_mood_from_features(normalized)
        if mood:
            mood_lower = mood.lower()
            
            # Utiliser les synonyms dynamiques pour le mood
            mood_terms = await self._get_search_terms(
                'mood', mood_lower, category='mood'
            )
            suggestions.update(mood_terms)
            
            # Mood combinés (fallback)
            if mood_lower == 'happy':
                suggestions.add('musique positive')
                suggestions.add('titres qui mettent de bonne humeur')
            elif mood_lower == 'energetic':
                suggestions.add('musique dynamique')
                suggestions.add('titres punchy')
            elif mood_lower == 'chill':
                suggestions.add('musique chill')
                suggestions.add('titres relaxants')
        
        # Energy level
        energy_score = normalized.get('energy_score')
        if energy_score:
            if energy_score > 0.7:
                suggestions.add('musique énergétique')
                suggestions.add('titres puissants')
                suggestions.add('musique pour le sport')
            elif energy_score < 0.4:
                suggestions.add('musique calme')
                suggestions.add('titres doux')
                suggestions.add('musique relaxante')
        
        # Danceability
        danceability = normalized.get('danceability')
        if danceability and danceability > 0.6:
            suggestions.add('musique pour danser')
            suggestions.add('titres dancefloor')
            suggestions.add('musique festive')
        
        # BPM
        bpm = normalized.get('bpm')
        if bpm:
            bpm_int = int(bpm)
            if bpm_int > 120:
                suggestions.add('musique rapide')
                suggestions.add('titres entraînants')
            elif bpm_int < 100:
                suggestions.add('musique lente')
                suggestions.add('titres doux')
        
        # Synthetic tags
        for tag_info in synthetic_tags:
            tag = tag_info.get('tag', '').lower()
            category = tag_info.get('category', '')
            
            if category == 'mood':
                mood_terms = await self._get_search_terms(
                    'mood', tag, category='mood'
                )
                suggestions.update(mood_terms)
            elif category == 'usage':
                usage_terms = await self._get_search_terms(
                    'usage', tag, category='usage'
                )
                suggestions.update(usage_terms)
            
            # Suggestions spécifiques par tag (fallback)
            if tag == 'workout':
                suggestions.add("musique pour s'entraîner")
                suggestions.add('playlist sport')
            elif tag == 'party':
                suggestions.add('musique de fête')
                suggestions.add('playlist派对')
            elif tag == 'focus':
                suggestions.add('musique pour étudier')
                suggestions.add('musique de concentration')
            elif tag == 'dancefloor':
                suggestions.add('titres pour la piste de danse')
                suggestions.add('musique de club')
        
        # Suggestions basées sur le titre (si disponible)
        if track_title:
            # Ajouter le titre comme suggestion partielle
            words = track_title.split()
            if len(words) > 2:
                suggestions.add(f"titres comme {words[0]} {words[1]}")
        
        # Convertir en liste triée et limiter
        suggestions_list = sorted(list(suggestions))[:10]
        
        logger.debug(f"[MusicSummary] {len(suggestions_list)} suggestions générées")
        return suggestions_list
    
    def create_summary(
        self, track_id: int, raw_tags: list[str], source: str,
        normalized: dict, scores: dict,
        synthetic_tags: list[dict],
        track_info: Optional[dict] = None
    ) -> dict:
        """Crée le résumé complet d'un track musical.
        
        Cette méthode est le point d'entrée principal du service. Elle agrège
        toutes les données MIR pour créer un résumé structuré.
        
        Args:
            track_id: Identifiant du track
            raw_tags: Tags bruts sources
            source: Source des données MIR
            normalized: Caractéristiques normalisées
            scores: Scores calculés
            synthetic_tags: Tags synthétiques générés
            track_info: Informations optionnelles sur le track
            
        Returns:
            Dictionnaire complet du résumé musical
        """
        logger.info(f"[MusicSummary] Création du résumé pour track {track_id}")
        
        # Générer le résumé textuel
        summary_text = self.generate_summary_text(
            normalized, synthetic_tags, track_info
        )
        
        # Générer le contexte
        context = self.generate_context(
            track_id, normalized, scores, synthetic_tags, source
        )
        
        # Générer les suggestions de recherche
        # Note: create_summary est synchrone, on utilise donc une boucle
        # event loop si disponible, sinon on génère des suggestions basiques
        import asyncio
        
        track_title = track_info.get('title') if track_info else None
        
        try:
            # Tenter d'obtenir une event loop pour les appels async
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si une loop est déjà en cours, créer une tâche
                search_suggestions = []
            else:
                # Sinon exécuter la coroutine
                search_suggestions = loop.run_until_complete(
                    self.generate_search_suggestions(
                        normalized, synthetic_tags, track_title
                    )
                )
        except RuntimeError:
            # Pas de loop disponible en synchrone, générer suggestions basiques
            search_suggestions = []
        
        # Si pas de suggestions async, générer des suggestions synchrones basiques
        if not search_suggestions:
            search_suggestions = self._generate_basic_suggestions(
                normalized, synthetic_tags, track_title
            )
        
        # Construire le résumé complet
        summary = {
            'track_id': track_id,
            'tags': raw_tags,
            'source': source,
            'version': '1.1',
            'normalized': {
                'bpm': normalized.get('bpm'),
                'key': normalized.get('key'),
                'scale': normalized.get('scale'),
                'camelot_key': normalized.get('camelot_key'),
                'danceability': normalized.get('danceability'),
                'mood_happy': normalized.get('mood_happy'),
                'mood_aggressive': normalized.get('mood_aggressive'),
                'mood_party': normalized.get('mood_party'),
                'mood_relaxed': normalized.get('mood_relaxed'),
                'instrumental': normalized.get('instrumental'),
                'acoustic': normalized.get('acoustic'),
                'tonal': normalized.get('tonal'),
                'genre_main': normalized.get('genre_main'),
                'genre_secondary': normalized.get('genre_secondary', []),
                'confidence_score': normalized.get('confidence_score', 0.0),
            },
            'scores': {
                'energy_score': scores.get('energy_score'),
                'mood_valence': scores.get('valence'),
                'dance_score': scores.get('dance_score'),
                'acousticness': scores.get('acousticness'),
                'complexity_score': scores.get('complexity_score'),
                'emotional_intensity': scores.get('emotional_intensity'),
            },
            'synthetic_tags': [
                {
                    'tag': t['tag'],
                    'score': t.get('score', 0.0),
                    'category': t.get('category', 'unknown'),
                    'source': t.get('source', 'calculated'),
                }
                for t in synthetic_tags
            ],
            'summary': summary_text,
            'context': context,
            'search_suggestions': search_suggestions,
        }
        
        logger.info(f"[MusicSummary] Résumé créé pour track {track_id}")
        return summary
    
    def _generate_basic_suggestions(
        self, normalized: dict, synthetic_tags: list[dict],
        track_title: Optional[str] = None
    ) -> list[str]:
        """Génère des suggestions basiques en mode synchrone.
        
        Cette méthode est utilisée lorsque les appels async ne sont pas possibles.
        Elle utilise les dictionnaires fallback.
        
        Args:
            normalized: Caractéristiques normalisées
            synthetic_tags: Tags synthétiques
            track_title: Titre optionnel du track
            
        Returns:
            Liste de suggestions de recherche basiques
        """
        suggestions = set()
        
        # Genre
        genre = normalized.get('genre_main')
        if genre:
            genre_lower = genre.lower()
            if genre_lower in self.GENRE_SEARCH_TERMS:
                suggestions.update(self.GENRE_SEARCH_TERMS[genre_lower])
        
        # Mood
        mood = self._get_mood_from_features(normalized)
        if mood:
            mood_lower = mood.lower()
            if mood_lower in self.MOOD_SEARCH_TERMS:
                suggestions.update(self.MOOD_SEARCH_TERMS[mood_lower])
        
        # Energy
        energy_score = normalized.get('energy_score')
        if energy_score:
            if energy_score > 0.7:
                suggestions.update(['musique énergétique', 'titres puissants'])
            elif energy_score < 0.4:
                suggestions.update(['musique calme', 'titres doux'])
        
        # Danceability
        danceability = normalized.get('danceability')
        if danceability and danceability > 0.6:
            suggestions.update(['musique pour danser', 'titres dancefloor'])
        
        # BPM
        bpm = normalized.get('bpm')
        if bpm:
            bpm_int = int(bpm)
            if bpm_int > 120:
                suggestions.update(['musique rapide', 'titres entraînants'])
            elif bpm_int < 100:
                suggestions.update(['musique lente', 'titres doux'])
        
        # Tags synthétiques
        for tag_info in synthetic_tags:
            tag = tag_info.get('tag', '').lower()
            category = tag_info.get('category', '')
            
            if category == 'mood' and tag in self.MOOD_SEARCH_TERMS:
                suggestions.update(self.MOOD_SEARCH_TERMS[tag])
            elif category == 'usage' and tag in self.USAGE_SEARCH_TERMS:
                suggestions.update(self.USAGE_SEARCH_TERMS[tag])
        
        return sorted(list(suggestions))[:10]
    
    def extract_summary_for_api(self, full_summary: dict) -> dict:
        """Extrait une version simplifiée du résumé pour l'API.
        
        Args:
            full_summary: Résumé complet
            
        Returns:
            Version simplifiée pour l'API
        """
        return {
            'track_id': full_summary['track_id'],
            'summary': full_summary['summary'],
            'genre': full_summary['normalized']['genre_main'],
            'mood': full_summary['context']['mood'],
            'bpm': full_summary['normalized']['bpm'],
            'key': full_summary['context']['key'],
            'camelot_key': full_summary['normalized']['camelot_key'],
            'energy_score': full_summary['scores']['energy_score'],
            'dance_score': full_summary['scores']['dance_score'],
            'synthetic_tags': full_summary['context']['synthetic_tags'],
            'confidence_score': full_summary['normalized']['confidence_score'],
        }
    
    def compare_summaries(self, summary1: dict, summary2: dict) -> dict:
        """Compare deux résumés pour identifier les similarités et différences.
        
        Args:
            summary1: Premier résumé
            summary2: Deuxième résumé
            
        Returns:
            Dictionnaire de comparaison
        """
        comparison = {
            'similar_genre': summary1['normalized']['genre_main'] == summary2['normalized']['genre_main'],
            'similar_mood': summary1['context']['mood'] == summary2['context']['mood'],
            'bpm_difference': abs(
                (summary1['normalized']['bpm'] or 0) - (summary2['normalized']['bpm'] or 0)
            ),
            'energy_difference': abs(
                (summary1['scores']['energy_score'] or 0) - (summary2['scores']['energy_score'] or 0)
            ),
            'dance_difference': abs(
                (summary1['scores']['dance_score'] or 0) - (summary2['scores']['dance_score'] or 0)
            ),
            'common_tags': list(set(
                summary1['context']['synthetic_tags']
            ) & set(summary2['context']['synthetic_tags'])),
            'compatibility_score': 0.0,
        }
        
        # Calculer un score de compatibilité
        factors = []
        
        if comparison['similar_genre']:
            factors.append(0.3)
        
        if comparison['similar_mood']:
            factors.append(0.2)
        
        if comparison['bpm_difference'] < 10:
            factors.append(0.2)
        elif comparison['bpm_difference'] < 20:
            factors.append(0.1)
        
        energy_diff = comparison['energy_difference']
        if energy_diff < 0.2:
            factors.append(0.15)
        
        dance_diff = comparison['dance_difference']
        if dance_diff < 0.2:
            factors.append(0.15)
        
        comparison['compatibility_score'] = min(1.0, sum(factors))
        
        return comparison
