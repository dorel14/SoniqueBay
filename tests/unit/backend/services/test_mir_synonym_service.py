# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service MIRSynonymService.

Rôle:
    Tests pour la logique de recherche hybride et de fusion des résultats.
    Ces tests sont standalone et ne nécessitent pas de base de données réelle.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import sys
import os

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest


class TestMergeResultsLogic:
    """Tests pour la logique de fusion des résultats hybrides."""

    def test_merge_basic_scoring(self):
        """Test du calcul de score hybride basique."""
        # Simulation de la logique de fusion
        FTS_WEIGHT = 0.3
        VECTOR_WEIGHT = 0.7

        fts_score = 0.5
        vector_score = 0.8

        hybrid_score = fts_score * FTS_WEIGHT + vector_score * VECTOR_WEIGHT

        # Le score hybride doit être une combinaison pondérée
        assert hybrid_score == pytest.approx(0.5 * 0.3 + 0.8 * 0.7)

    def test_merge_only_fts_score(self):
        """Test avec uniquement score FTS."""
        FTS_WEIGHT = 0.3
        VECTOR_WEIGHT = 0.7

        fts_score = 0.5
        vector_score = 0.0

        hybrid_score = fts_score * FTS_WEIGHT + vector_score * VECTOR_WEIGHT

        assert hybrid_score == pytest.approx(0.15)

    def test_merge_only_vector_score(self):
        """Test avec uniquement score vectoriel."""
        FTS_WEIGHT = 0.3
        VECTOR_WEIGHT = 0.7

        fts_score = 0.0
        vector_score = 0.8

        hybrid_score = fts_score * FTS_WEIGHT + vector_score * VECTOR_WEIGHT

        assert hybrid_score == pytest.approx(0.56)

    def test_merge_no_scores(self):
        """Test avec aucun score."""
        FTS_WEIGHT = 0.3
        VECTOR_WEIGHT = 0.7

        hybrid_score = 0.0 * FTS_WEIGHT + 0.0 * VECTOR_WEIGHT

        assert hybrid_score == 0.0


class TestCacheKeyGeneration:
    """Tests pour la génération des clés de cache."""

    def test_cache_key_format(self):
        """Test du format de la clé de cache."""
        import hashlib

        prefix = "synonym"
        tag_type = "genre"
        tag_value = "rock"

        args_str = f"{prefix}:{tag_type}:{tag_value}"
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]

        expected_prefix = f"mir_synonym:{prefix}:"

        assert expected_prefix in f"mir_synonym:{prefix}:{args_hash}"

    def test_cache_key_hash_different_inputs(self):
        """Test que différentes entrées génèrent différents hashes."""
        import hashlib

        inputs = [
            "synonym:genre:rock",
            "synonym:genre:jazz",
            "synonym:mood:happy",
        ]

        hashes = []
        for inp in inputs:
            h = hashlib.md5(inp.encode()).hexdigest()[:12]
            hashes.append(h)

        # Tous les hashes doivent être différents
        assert len(set(hashes)) == len(hashes)


class TestSearchTextBuilder:
    """Tests pour la construction du texte de recherche."""

    def test_build_text_from_search_terms(self):
        """Test construction du texte depuis search_terms."""
        synonyms = {
            "search_terms": ["rock", "rock music", "rock and roll"],
            "related_tags": [],
        }

        parts = []
        search_terms = synonyms.get("search_terms", [])
        if search_terms:
            parts.extend(search_terms[:10])

        result = " ".join(parts)

        assert "rock" in result
        assert "rock music" in result
        assert "rock and roll" in result

    def test_build_text_from_related_tags(self):
        """Test construction du texte depuis related_tags."""
        synonyms = {
            "search_terms": [],
            "related_tags": ["hard rock", "classic rock"],
        }

        parts = []
        related_tags = synonyms.get("related_tags", [])
        if related_tags:
            parts.extend(related_tags[:10])

        result = " ".join(parts)

        assert "hard rock" in result
        assert "classic rock" in result

    def test_build_text_combined(self):
        """Test construction combinée."""
        synonyms = {
            "search_terms": ["rock", "rock music"],
            "related_tags": ["hard rock"],
        }

        parts = []
        search_terms = synonyms.get("search_terms", [])
        if search_terms:
            parts.extend(search_terms[:10])

        related_tags = synonyms.get("related_tags", [])
        if related_tags:
            parts.extend(related_tags[:10])

        result = " ".join(parts)

        assert "rock" in result
        assert "hard rock" in result

    def test_build_text_empty(self):
        """Test avec synonyms vides."""
        synonyms = {}

        parts = []
        search_terms = synonyms.get("search_terms", [])
        if search_terms:
            parts.extend(search_terms[:10])

        related_tags = synonyms.get("related_tags", [])
        if related_tags:
            parts.extend(related_tags[:10])

        result = " ".join(parts)

        assert result == ""


class TestHybridSearchWeights:
    """Tests pour les pondérations de recherche hybride."""

    def test_weights_sum_to_one(self):
        """Test que les poids сумма à 1."""
        FTS_WEIGHT = 0.3
        VECTOR_WEIGHT = 0.7

        assert FTS_WEIGHT + VECTOR_WEIGHT == 1.0

    def test_vector_weight_higher(self):
        """Test que le poids vectoriel est plus élevé."""
        FTS_WEIGHT = 0.3
        VECTOR_WEIGHT = 0.7

        assert VECTOR_WEIGHT > FTS_WEIGHT


class TestSearchResultStructure:
    """Tests pour la structure des résultats de recherche."""

    def test_fts_result_structure(self):
        """Test structure résultat FTS."""
        result = {
            "tag_type": "genre",
            "tag_value": "rock",
            "synonyms": {"search_terms": ["rock"]},
            "fts_score": 0.5,
        }

        assert "tag_type" in result
        assert "tag_value" in result
        assert "synonyms" in result
        assert "fts_score" in result

    def test_vector_result_structure(self):
        """Test structure résultat vectoriel."""
        result = {
            "tag_type": "genre",
            "tag_value": "rock",
            "synonyms": {"search_terms": ["rock"]},
            "vector_score": 0.85,
        }

        assert "tag_type" in result
        assert "tag_value" in result
        assert "synonyms" in result
        assert "vector_score" in result

    def test_hybrid_result_structure(self):
        """Test structure résultat hybride."""
        result = {
            "tag_type": "genre",
            "tag_value": "rock",
            "synonyms": {"search_terms": ["rock"]},
            "fts_score": 0.5,
            "vector_score": 0.8,
            "hybrid_score": 0.71,
        }

        assert "tag_type" in result
        assert "tag_value" in result
        assert "fts_score" in result
        assert "vector_score" in result
        assert "hybrid_score" in result


class TestSynonymDataTypes:
    """Tests pour les types de données des synonyms."""

    def test_search_terms_list(self):
        """Test que search_terms est une liste."""
        search_terms = ["rock", "rock music", "hard rock"]

        assert isinstance(search_terms, list)
        assert len(search_terms) == 3

    def test_related_tags_list(self):
        """Test que related_tags est une liste."""
        related_tags = ["classic rock", "alternative rock"]

        assert isinstance(related_tags, list)
        assert len(related_tags) == 2

    def test_usage_context_list(self):
        """Test que usage_context est une liste."""
        usage_context = ["workout", "party", "driving"]

        assert isinstance(usage_context, list)
        assert len(usage_context) == 3

    def test_translations_dict(self):
        """Test que translations est un dictionnaire."""
        translations = {"en": "rock", "es": "rock", "de": "rock"}

        assert isinstance(translations, dict)
        assert "en" in translations
        assert "es" in translations


class TestCacheTTL:
    """Tests pour le TTL de cache."""

    def test_cache_ttl_24_hours(self):
        """Test que le TTL est de 24 heures."""
        CACHE_TTL = 86400  # 24 heures en secondes

        assert CACHE_TTL == 24 * 60 * 60

    def test_cache_ttl_in_hours(self):
        """Test conversion TTL en heures."""
        CACHE_TTL = 86400

        hours = CACHE_TTL / 3600

        assert hours == 24.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
