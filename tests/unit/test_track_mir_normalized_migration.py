# -*- coding: utf-8 -*-
"""
Tests unitaires pour la migration track_mir_normalized.

Rôle:
    Vérifie que le modèle TrackMIRNormalized fonctionne correctement
    avec toutes les colonnes (ancien et nouveau schéma).

Auteur: SoniqueBay Team
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestTrackMIRNormalizedModel:
    """Tests pour le modèle TrackMIRNormalized."""

    def test_model_has_all_new_schema_columns(self):
        """Vérifie que le modèle a toutes les colonnes du nouveau schéma."""
        # Import du modèle
        from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
        
        # Vérifier les colonnes du nouveau schéma
        assert hasattr(TrackMIRNormalized, 'bpm')
        assert hasattr(TrackMIRNormalized, 'key')
        assert hasattr(TrackMIRNormalized, 'scale')
        assert hasattr(TrackMIRNormalized, 'danceability')
        assert hasattr(TrackMIRNormalized, 'mood_happy')
        assert hasattr(TrackMIRNormalized, 'mood_aggressive')
        assert hasattr(TrackMIRNormalized, 'mood_party')
        assert hasattr(TrackMIRNormalized, 'mood_relaxed')
        assert hasattr(TrackMIRNormalized, 'instrumental')
        assert hasattr(TrackMIRNormalized, 'acoustic')
        assert hasattr(TrackMIRNormalized, 'tonal')
        assert hasattr(TrackMIRNormalized, 'genre_main')
        assert hasattr(TrackMIRNormalized, 'genre_secondary')
        assert hasattr(TrackMIRNormalized, 'camelot_key')
        assert hasattr(TrackMIRNormalized, 'confidence_score')
        assert hasattr(TrackMIRNormalized, 'normalized_at')

    def test_model_has_all_old_schema_columns(self):
        """Vérifie que le modèle conserve les colonnes de l'ancien schéma."""
        from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
        
        # Vérifier les colonnes de l'ancien schéma
        assert hasattr(TrackMIRNormalized, 'loudness')
        assert hasattr(TrackMIRNormalized, 'tempo')
        assert hasattr(TrackMIRNormalized, 'energy')
        assert hasattr(TrackMIRNormalized, 'valence')
        assert hasattr(TrackMIRNormalized, 'acousticness')
        assert hasattr(TrackMIRNormalized, 'instrumentalness')
        assert hasattr(TrackMIRNormalized, 'speechiness')
        assert hasattr(TrackMIRNormalized, 'liveness')
        assert hasattr(TrackMIRNormalized, 'dynamic_range')
        assert hasattr(TrackMIRNormalized, 'spectral_complexity')
        assert hasattr(TrackMIRNormalized, 'harmonic_complexity')
        assert hasattr(TrackMIRNormalized, 'perceptual_roughness')
        assert hasattr(TrackMIRNormalized, 'auditory_roughness')
        assert hasattr(TrackMIRNormalized, 'normalization_source')
        assert hasattr(TrackMIRNormalized, 'normalization_version')
        assert hasattr(TrackMIRNormalized, 'normalization_date')

    def test_model_to_dict_includes_all_columns(self):
        """Vérifie que to_dict() inclut toutes les colonnes."""
        from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
        
        # Créer une instance mock
        instance = MagicMock(spec=TrackMIRNormalized)
        instance.id = 1
        instance.track_id = 100
        instance.bpm = 120.0
        instance.key = "C"
        instance.scale = "major"
        instance.danceability = 0.8
        instance.mood_happy = 0.7
        instance.mood_aggressive = 0.2
        instance.mood_party = 0.6
        instance.mood_relaxed = 0.3
        instance.instrumental = 0.1
        instance.acoustic = 0.4
        instance.tonal = 0.9
        instance.genre_main = "Rock"
        instance.genre_secondary = ["Alternative", "Indie"]
        instance.camelot_key = "8B"
        instance.confidence_score = 0.85
        instance.normalized_at = datetime(2026, 2, 28, 12, 0, 0)
        # Ancien schéma
        instance.loudness = 0.7
        instance.tempo = 0.6
        instance.energy = 0.8
        instance.valence = 0.75
        instance.acousticness = 0.3
        instance.instrumentalness = 0.1
        instance.speechiness = 0.05
        instance.liveness = 0.4
        instance.dynamic_range = 0.6
        instance.spectral_complexity = 0.5
        instance.harmonic_complexity = 0.4
        instance.perceptual_roughness = 0.3
        instance.auditory_roughness = 0.2
        instance.normalization_source = "essentia"
        instance.normalization_version = "1.0"
        instance.normalization_date = datetime(2026, 2, 28, 10, 0, 0)
        # Métadonnées
        instance.date_added = datetime(2026, 2, 28, 8, 0, 0)
        instance.date_modified = datetime(2026, 2, 28, 12, 0, 0)
        
        # Appeler la vraie méthode to_dict
        result = TrackMIRNormalized.to_dict(instance)
        
        # Vérifier que toutes les colonnes sont présentes
        assert 'bpm' in result
        assert 'key' in result
        assert 'scale' in result
        assert 'danceability' in result
        assert 'mood_happy' in result
        assert 'mood_aggressive' in result
        assert 'mood_party' in result
        assert 'mood_relaxed' in result
        assert 'instrumental' in result
        assert 'acoustic' in result
        assert 'tonal' in result
        assert 'genre_main' in result
        assert 'genre_secondary' in result
        assert 'camelot_key' in result
        assert 'confidence_score' in result
        assert 'normalized_at' in result
        # Ancien schéma
        assert 'loudness' in result
        assert 'tempo' in result
        assert 'energy' in result
        assert 'valence' in result
        assert 'acousticness' in result
        assert 'instrumentalness' in result
        assert 'speechiness' in result
        assert 'liveness' in result
        assert 'dynamic_range' in result
        assert 'spectral_complexity' in result
        assert 'harmonic_complexity' in result
        assert 'perceptual_roughness' in result
        assert 'auditory_roughness' in result
        assert 'normalization_source' in result
        assert 'normalization_version' in result
        assert 'normalization_date' in result

    def test_model_repr(self):
        """Vérifie que __repr__ fonctionne correctement."""
        from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
        
        instance = MagicMock(spec=TrackMIRNormalized)
        instance.id = 1
        instance.track_id = 100
        instance.bpm = 120.0
        instance.key = "C"
        instance.camelot_key = "8B"
        
        result = TrackMIRNormalized.__repr__(instance)
        
        assert "TrackMIRNormalized" in result
        assert "id=1" in result
        assert "track_id=100" in result
        assert "bpm=120.0" in result
        assert "key=C" in result
        assert "camelot=8B" in result


class TestTrackMIRNormalizedMigration:
    """Tests pour la migration Alembic."""

    def test_migration_file_exists(self):
        """Vérifie que le fichier de migration existe."""
        import os
        migration_path = "alembic/versions/add_mir_norm_cols.py"
        assert os.path.exists(migration_path), f"Migration file not found: {migration_path}"

    def test_migration_has_correct_revision(self):
        """Vérifie que la migration a la bonne révision parente."""
        # Lire le fichier de migration
        with open("alembic/versions/add_mir_norm_cols.py", "r") as f:
            content = f.read()
        
        # Vérifier que down_revision pointe vers b2c3d4e5f6g7
        assert "down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'" in content
        # Vérifier que revision est add_mir_norm_cols (16 caractères, respecte la limite de 32)
        assert "revision: str = 'add_mir_norm_cols'" in content

    def test_migration_adds_all_required_columns(self):
        """Vérifie que la migration ajoute toutes les colonnes requises."""
        with open("alembic/versions/add_mir_norm_cols.py", "r") as f:
            content = f.read()
        
        # Colonnes du nouveau schéma à vérifier (sans danceability qui existe déjà)
        required_columns = [
            "bpm", "key", "scale",
            "mood_happy", "mood_aggressive", "mood_party", "mood_relaxed",
            "instrumental", "acoustic", "tonal",
            "genre_main", "genre_secondary", "camelot_key",
            "confidence_score", "normalized_at"
        ]
        
        for column in required_columns:
            assert f"op.add_column('track_mir_normalized', sa.Column('{column}'" in content, \
                f"Column {column} not found in migration"
        
        # Vérifier que danceability n'est PAS ajouté (existe déjà dans l'ancien schéma)
        assert "op.add_column('track_mir_normalized', sa.Column('danceability'" not in content, \
            "danceability should not be added as it already exists in old schema"

    def test_migration_creates_required_indexes(self):
        """Vérifie que la migration crée tous les indexes requis."""
        with open("alembic/versions/add_mir_norm_cols.py", "r") as f:
            content = f.read()
        
        # Indexes du nouveau schéma
        required_indexes = [
            "idx_track_mir_normalized_bpm",
            "idx_track_mir_normalized_key",
            "idx_track_mir_normalized_camelot_key",
            "idx_track_mir_normalized_genre_main"
        ]
        
        for index in required_indexes:
            assert f"op.create_index('{index}'" in content, \
                f"Index {index} not found in migration"
        
        # Vérifier que les indexes de l'ancien schéma ne sont PAS créés (existent déjà)
        old_schema_indexes = [
            "idx_track_mir_normalized_tempo",
            "idx_track_mir_normalized_energy",
            "idx_track_mir_normalized_valence",
            "idx_track_mir_normalized_danceability"
        ]
        
        for index in old_schema_indexes:
            assert f"op.create_index('{index}'" not in content, \
                f"Index {index} should not be created as it already exists"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
