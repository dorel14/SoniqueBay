# -*- coding: utf-8 -*-
"""
Tests unitaires pour la migration fix_all_mir_schema_mismatches.

Rôle:
    Valide que la migration corrige tous les mismatches des tables MIR.

Couverture:
    - Présence de la migration
    - Structure correcte (upgrade/downgrade)
    - Corrections pour track_mir_synthetic_tags
    - Corrections pour track_mir_scores
    - Ajouts pour track_mir_normalized

Auteur: SoniqueBay Team
"""

import pytest
import os
import sys
from pathlib import Path


class TestFixAllMIRSchemasMigration:
    """Tests pour la migration complète des schémas MIR."""
    
    def test_migration_file_exists(self):
        """Test que le fichier de migration existe."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        assert migration_path.exists(), f"Le fichier de migration n'existe pas: {migration_path}"
    
    def test_migration_has_correct_revision(self):
        """Test que la migration a la bonne révision parente."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        assert "revision: str = 'fix_all_mir_schemas'" in content
        assert "'add_calc_at_mir_scores'" in content
    
    def test_migration_has_upgrade_function(self):
        """Test que la migration a une fonction upgrade."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        assert 'def upgrade()' in content or 'def upgrade() -> None:' in content
    
    def test_migration_has_downgrade_function(self):
        """Test que la migration a une fonction downgrade."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        assert 'def downgrade()' in content or 'def downgrade() -> None:' in content
    
    def test_migration_fixes_synthetic_tags(self):
        """Test que la migration corrige track_mir_synthetic_tags."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier les renommages
        assert 'confidence' in content, "Doit référencer 'confidence'"
        assert 'tag_score' in content, "Doit référencer 'tag_score'"
        assert 'source' in content, "Doit référencer 'source'"
        assert 'tag_source' in content, "Doit référencer 'tag_source'"
        assert 'track_mir_synthetic_tags' in content, "Doit référencer la table"
    
    def test_migration_fixes_scores(self):
        """Test que la migration corrige track_mir_scores."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier les renommages
        assert 'acousticness_score' in content, "Doit référencer 'acousticness_score'"
        assert 'acousticness' in content, "Doit référencer 'acousticness'"
        assert 'scoring_date' in content, "Doit référencer 'scoring_date'"
        assert 'calculated_at' in content, "Doit référencer 'calculated_at'"
        assert 'track_mir_scores' in content, "Doit référencer la table"
    
    def test_migration_adds_normalized_columns(self):
        """Test que la migration ajoute les colonnes à track_mir_normalized."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier les colonnes du nouveau schéma
        new_columns = ['bpm', 'key', 'scale', 'mood_happy', 'mood_aggressive',
                      'mood_party', 'mood_relaxed', 'instrumental', 'acoustic',
                      'tonal', 'genre_main', 'genre_secondary', 'camelot_key']
        
        for col in new_columns:
            assert col in content, f"La migration doit référencer '{col}'"
        
        assert 'track_mir_normalized' in content, "Doit référencer la table"
    
    def test_migration_uses_if_exists_checks(self):
        """Test que la migration vérifie l'existence des colonnes."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_all_mir_schema_mismatches.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier les vérifications d'existence
        assert 'information_schema.columns' in content, "Doit vérifier l'existence des colonnes"
        assert 'IF EXISTS' in content or 'IF NOT EXISTS' in content, "Doit utiliser IF EXISTS"


class TestModelAlignment:
    """Tests pour vérifier l'alignement des modèles avec la migration."""
    
    def test_synthetic_tags_model_expects_correct_columns(self):
        """Test que le modèle TrackMIRSyntheticTags attend les bonnes colonnes."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from backend.api.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags
            
            # Vérifier les colonnes attendues
            assert hasattr(TrackMIRSyntheticTags, 'tag_score'), "Doit avoir 'tag_score'"
            assert hasattr(TrackMIRSyntheticTags, 'tag_source'), "Doit avoir 'tag_source'"
            assert hasattr(TrackMIRSyntheticTags, 'tag_name'), "Doit avoir 'tag_name'"
            assert hasattr(TrackMIRSyntheticTags, 'tag_category'), "Doit avoir 'tag_category'"
            assert hasattr(TrackMIRSyntheticTags, 'created_at'), "Doit avoir 'created_at'"
        finally:
            sys.path.pop(0)
    
    def test_scores_model_expects_correct_columns(self):
        """Test que le modèle TrackMIRScores attend les bonnes colonnes."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from backend.api.models.track_mir_scores_model import TrackMIRScores
            
            # Vérifier les colonnes attendues
            assert hasattr(TrackMIRScores, 'acousticness'), "Doit avoir 'acousticness'"
            assert hasattr(TrackMIRScores, 'calculated_at'), "Doit avoir 'calculated_at'"
            assert hasattr(TrackMIRScores, 'energy_score'), "Doit avoir 'energy_score'"
            assert hasattr(TrackMIRScores, 'mood_valence'), "Doit avoir 'mood_valence'"
            assert hasattr(TrackMIRScores, 'dance_score'), "Doit avoir 'dance_score'"
        finally:
            sys.path.pop(0)
    
    def test_normalized_model_expects_new_schema_columns(self):
        """Test que le modèle TrackMIRNormalized attend les colonnes du nouveau schéma."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
            
            # Vérifier les colonnes du nouveau schéma
            new_columns = ['bpm', 'key', 'scale', 'mood_happy', 'mood_aggressive',
                          'mood_party', 'mood_relaxed', 'instrumental', 'acoustic',
                          'tonal', 'genre_main', 'genre_secondary', 'camelot_key',
                          'confidence_score', 'normalized_at']
            
            for col in new_columns:
                assert hasattr(TrackMIRNormalized, col), f"Doit avoir '{col}'"
        finally:
            sys.path.pop(0)


class TestMigrationIntegration:
    """Tests d'intégration pour la migration (nécessite une DB de test)."""
    
    @pytest.mark.skipif(
        os.getenv('SKIP_DB_TESTS') == '1',
        reason="Tests DB désactivés (SKIP_DB_TESTS=1)"
    )
    def test_migration_can_be_applied(self):
        """
        Test que la migration peut être appliquée sur une base de données.
        Nécessite une connexion DB de test.
        """
        pytest.skip("Test d'intégration DB - exécuter manuellement avec une DB de test")
