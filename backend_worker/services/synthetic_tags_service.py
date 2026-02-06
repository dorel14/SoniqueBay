"""Service de génération de tags synthétiques.

Ce service génère des tags synthétiques haut niveau à partir des caractéristiques
audio normalisées pour enrichir les métadonnées des tracks.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional
from backend_worker.utils.logging import logger


class SyntheticTagsService:
    """Service pour la génération de tags synthétiques.
    
    Ce service génère des tags synthétiques haut niveau basés sur les caractéristiques
    audio normalisées. Les tags sont organisés en catégories:
    
    - **Mood**: dark, bright, energetic, chill, melancholic, aggressive, uplifting
    - **Energy**: high_energy, medium_energy, low_energy
    - **Atmosphere**: dancefloor, ambient, intimate, epic
    - **Usage**: workout, focus, background, party
    
    Chaque tag inclut un score de confiance et une explication.
    """
    
    def __init__(self) -> None:
        """Initialise le service de tags synthétiques."""
        logger.info("[SyntheticTagsService] Initialisation du service de tags synthétiques")
    
    def generate_mood_tags(self, features: dict, scores: dict) -> list[dict]:
        """Génère les tags de mood.
        
        Tags générés: dark, bright, energetic, chill, melancholic, aggressive, uplifting
        
        Args:
            features: Caractéristiques normalisées
            scores: Scores calculés
            
        Returns:
            Liste de dictionnaires {tag, score, confidence}
        """
        mood_tags = []
        
        valence = scores.get('valence', 0.0)
        energy = scores.get('energy_score', 0.0)
        intensity = scores.get('emotional_intensity', 0.0)
        
        # Dark: valence négative
        if valence < 0:
            dark_score = abs(valence)
            mood_tags.append({
                'tag': 'dark',
                'score': dark_score,
                'confidence': min(1.0, dark_score + 0.2),
                'reason': f"valence négative ({valence:.2f})"
            })
        
        # Bright: valence positive
        if valence > 0:
            bright_score = valence
            mood_tags.append({
                'tag': 'bright',
                'score': bright_score,
                'confidence': min(1.0, bright_score + 0.2),
                'reason': f"valence positive ({valence:.2f})"
            })
        
        # Energetic: energy élevée
        if energy > 0.6:
            energy_score = energy
            mood_tags.append({
                'tag': 'energetic',
                'score': energy_score,
                'confidence': energy_score,
                'reason': f"energy élevée ({energy:.2f})"
            })
        
        # Chill: energy basse
        if energy < 0.4:
            chill_score = 1.0 - energy
            mood_tags.append({
                'tag': 'chill',
                'score': chill_score,
                'confidence': chill_score,
                'reason': f"energy basse ({energy:.2f})"
            })
        
        # Melancholic: valence négative + intensité modérée
        if valence < -0.2 and 0.3 < intensity < 0.7:
            melancholic_score = abs(valence) * intensity
            mood_tags.append({
                'tag': 'melancholic',
                'score': melancholic_score,
                'confidence': min(1.0, melancholic_score + 0.3),
                'reason': "valence négative + intensité modérée"
            })
        
        # Aggressive: intensité élevée
        if intensity > 0.6:
            aggressive_score = intensity
            mood_tags.append({
                'tag': 'aggressive',
                'score': aggressive_score,
                'confidence': aggressive_score,
                'reason': f"intensité élevée ({intensity:.2f})"
            })
        
        # Uplifting: valence positive + energy élevée
        if valence > 0.3 and energy > 0.5:
            uplifting_score = (valence + energy) / 2
            mood_tags.append({
                'tag': 'uplifting',
                'score': uplifting_score,
                'confidence': uplifting_score,
                'reason': "valence positive + energy élevée"
            })
        
        # Trier par score décroissant
        mood_tags.sort(key=lambda x: x['score'], reverse=True)
        
        logger.debug(f"[SyntheticTags] Mood tags générés: {len(mood_tags)}")
        return mood_tags
    
    def generate_energy_tags(self, features: dict, scores: dict) -> list[dict]:
        """Génère les tags d'énergie.
        
        Tags générés: high_energy, medium_energy, low_energy
        
        Args:
            features: Caractéristiques normalisées
            scores: Scores calculés
            
        Returns:
            Liste de dictionnaires {tag, score, confidence}
        """
        energy_tags = []
        
        energy = scores.get('energy_score', 0.5)
        bpm = features.get('bpm', 0.5)
        dance = scores.get('dance_score', 0.5)
        
        # High energy: energy > 0.7
        if energy > 0.7:
            energy_tags.append({
                'tag': 'high_energy',
                'score': energy,
                'confidence': energy,
                'reason': f"energy={energy:.2f}, dance={dance:.2f}"
            })
        
        # Low energy: energy < 0.3
        elif energy < 0.3:
            low_energy_score = 1.0 - energy
            energy_tags.append({
                'tag': 'low_energy',
                'score': low_energy_score,
                'confidence': low_energy_score,
                'reason': f"energy={energy:.2f}"
            })
        
        # Medium energy: 0.3 <= energy <= 0.7
        else:
            energy_tags.append({
                'tag': 'medium_energy',
                'score': 1.0 - abs(energy - 0.5) * 2,
                'confidence': 0.8,
                'reason': f"energy modérée ({energy:.2f})"
            })
        
        logger.debug(f"[SyntheticTags] Energy tags générés: {len(energy_tags)}")
        return energy_tags
    
    def generate_atmosphere_tags(self, features: dict, scores: dict) -> list[dict]:
        """Génère les tags d'atmosphère.
        
        Tags générés: dancefloor, ambient, intimate, epic
        
        Args:
            features: Caractéristiques normalisées
            scores: Scores calculés
            
        Returns:
            Liste de dictionnaires {tag, score, confidence}
        """
        atmosphere_tags = []
        
        dance = scores.get('dance_score', 0.5)
        acousticness = scores.get('acousticness', 0.5)
        complexity = scores.get('complexity_score', 0.5)
        instrumental = features.get('instrumental', 0.5)
        
        # Dancefloor: dance élevé + instrumental bas
        if dance > 0.6 and instrumental < 0.5:
            dancefloor_score = (dance + (1.0 - instrumental)) / 2
            atmosphere_tags.append({
                'tag': 'dancefloor',
                'score': dancefloor_score,
                'confidence': dancefloor_score,
                'reason': f"dance={dance:.2f}, instrumental={instrumental:.2f}"
            })
        
        # Ambient: instrumental élevé + acousticness élevé
        if instrumental > 0.5 and acousticness > 0.4:
            ambient_score = (instrumental + acousticness) / 2
            atmosphere_tags.append({
                'tag': 'ambient',
                'score': ambient_score,
                'confidence': ambient_score,
                'reason': f"instrumental={instrumental:.2f}, acousticness={acousticness:.2f}"
            })
        
        # Intimate: acousticness élevé + dance bas + complexity bas
        if acousticness > 0.5 and dance < 0.4 and complexity < 0.5:
            intimate_score = (acousticness + (1.0 - dance)) / 2
            atmosphere_tags.append({
                'tag': 'intimate',
                'score': intimate_score,
                'confidence': intimate_score,
                'reason': "ambiance intime détectée"
            })
        
        # Epic: complexity élevée + instrumental modéré
        if complexity > 0.6 and 0.3 < instrumental < 0.7:
            epic_score = (complexity + (1.0 - abs(instrumental - 0.5))) / 2
            atmosphere_tags.append({
                'tag': 'epic',
                'score': epic_score,
                'confidence': epic_score,
                'reason': f"complexité élevée ({complexity:.2f})"
            })
        
        logger.debug(f"[SyntheticTags] Atmosphere tags générés: {len(atmosphere_tags)}")
        return atmosphere_tags
    
    def generate_usage_tags(self, features: dict, scores: dict) -> list[dict]:
        """Génère les tags d'usage.
        
        Tags générés: workout, focus, background, party
        
        Args:
            features: Caractéristiques normalisées
            scores: Scores calculés
            
        Returns:
            Liste de dictionnaires {tag, score, confidence}
        """
        usage_tags = []
        
        dance = scores.get('dance_score', 0.5)
        energy = scores.get('energy_score', 0.5)
        valence = scores.get('valence', 0.0)
        acousticness = scores.get('acousticness', 0.5)
        
        # Workout: high energy + dance + valence positive
        if energy > 0.7 and dance > 0.6 and valence > 0:
            workout_score = (energy + dance + valence) / 3
            usage_tags.append({
                'tag': 'workout',
                'score': workout_score,
                'confidence': workout_score,
                'reason': "energy élevée + dance + valence positive"
            })
        
        # Focus: energy modérée + acousticness + complexité
        focus_score = (energy * 0.5 + acousticness * 0.5)
        if 0.3 < energy < 0.6 and acousticness > 0.4:
            usage_tags.append({
                'tag': 'focus',
                'score': focus_score,
                'confidence': focus_score,
                'reason': "energy modérée + acousticness"
            })
        
        # Background: low energy + acousticness + instrumental
        instrumental = features.get('instrumental', 0.5)
        if energy < 0.4 and acousticness > 0.3:
            background_score = ((1.0 - energy) + acousticness + instrumental) / 3
            usage_tags.append({
                'tag': 'background',
                'score': background_score,
                'confidence': background_score,
                'reason': "energy basse + acousticness"
            })
        
        # Party: high dance + high energy + valence positive
        if dance > 0.6 and energy > 0.6 and valence > 0.2:
            party_score = (dance + energy + valence) / 3
            usage_tags.append({
                'tag': 'party',
                'score': party_score,
                'confidence': party_score,
                'reason': "dance élevée + energy + valence positive"
            })
        
        logger.debug(f"[SyntheticTags] Usage tags générés: {len(usage_tags)}")
        return usage_tags
    
    def calculate_tag_explainability(self, tag_name: str, features: dict, scores: dict) -> dict:
        """Calcule l'explicabilité d'un tag.
        
        Args:
            tag_name: Nom du tag
            features: Caractéristiques normalisées
            scores: Scores calculés
            
        Returns:
            Dictionnaire avec les facteurs d'explication
        """
        explainability = {
            'tag': tag_name,
            'factors': [],
            'confidence': 0.0,
            'source': 'inference'
        }
        
        # Map des tags vers les caractéristiques sources
        tag_sources = {
            'dark': ['valence'],
            'bright': ['valence'],
            'energetic': ['energy_score'],
            'chill': ['energy_score'],
            'aggressive': ['emotional_intensity'],
            'dancefloor': ['dance_score', 'instrumental'],
            'ambient': ['instrumental', 'acousticness'],
            'workout': ['energy_score', 'dance_score', 'valence'],
            'party': ['dance_score', 'energy_score', 'valence'],
            'focus': ['energy_score', 'acousticness'],
            'background': ['energy_score', 'acousticness', 'instrumental'],
        }
        
        sources = tag_sources.get(tag_name, [])
        
        for source in sources:
            if source in scores:
                explainability['factors'].append({
                    'source': source,
                    'value': scores[source],
                    'weight': 1.0 / len(sources) if sources else 1.0
                })
        
        if explainability['factors']:
            explainability['confidence'] = sum(
                f['value'] * f['weight'] for f in explainability['factors']
            )
            explainability['source'] = 'features_analysis'
        
        return explainability
    
    def generate_all_synthetic_tags(self, features: dict, scores: dict) -> dict:
        """Génère tous les tags synthétiques.
        
        Args:
            features: Caractéristiques normalisées
            scores: Scores calculés
            
        Returns:
            Dictionnaire complet avec tous les tags par catégorie
        """
        logger.info(f"[SyntheticTags] Début de la génération des tags synthétiques")
        
        result = {
            'mood_tags': [],
            'energy_tags': [],
            'atmosphere_tags': [],
            'usage_tags': [],
            'all_tags': [],
            'total_tags': 0,
        }
        
        # Générer les tags par catégorie
        result['mood_tags'] = self.generate_mood_tags(features, scores)
        result['energy_tags'] = self.generate_energy_tags(features, scores)
        result['atmosphere_tags'] = self.generate_atmosphere_tags(features, scores)
        result['usage_tags'] = self.generate_usage_tags(features, scores)
        
        # Combiner tous les tags
        all_tags = (
            result['mood_tags'] +
            result['energy_tags'] +
            result['atmosphere_tags'] +
            result['usage_tags']
        )
        
        # Trier par score décroissant
        all_tags.sort(key=lambda x: x['score'], reverse=True)
        
        # Ajouter l'explicabilité à chaque tag
        for tag in all_tags:
            tag['explainability'] = self.calculate_tag_explainability(
                tag['tag'], features, scores
            )
        
        result['all_tags'] = all_tags
        result['total_tags'] = len(all_tags)
        
        # Logger les résultats
        logger.info(f"[SyntheticTags] {result['total_tags']} tags générés:")
        logger.info(f"  - Mood: {len(result['mood_tags'])}")
        logger.info(f"  - Energy: {len(result['energy_tags'])}")
        logger.info(f"  - Atmosphere: {len(result['atmosphere_tags'])}")
        logger.info(f"  - Usage: {len(result['usage_tags'])}")
        
        return result
    
    def get_tags_for_filtering(self, synthetic_tags: dict, min_score: float = 0.5) -> dict:
        """Extrait les tags filtrables pour les requêtes.
        
        Args:
            synthetic_tags: Dictionnaire des tags synthétiques
            min_score: Score minimum pour inclusion
            
        Returns:
            Dictionnaire des tags filtrables
        """
        filtering_tags = {
            'moods': [],
            'energy_level': None,
            'atmospheres': [],
            'usages': []
        }
        
        # Moods
        for tag in synthetic_tags.get('mood_tags', []):
            if tag['score'] >= min_score:
                filtering_tags['moods'].append(tag['tag'])
        
        # Energy level (prendre le premier)
        for tag in synthetic_tags.get('energy_tags', []):
            if tag['score'] >= min_score:
                filtering_tags['energy_level'] = tag['tag']
                break
        
        # Atmospheres
        for tag in synthetic_tags.get('atmosphere_tags', []):
            if tag['score'] >= min_score:
                filtering_tags['atmospheres'].append(tag['tag'])
        
        # Usages
        for tag in synthetic_tags.get('usage_tags', []):
            if tag['score'] >= min_score:
                filtering_tags['usages'].append(tag['tag'])
        
        return filtering_tags
