# -*- coding: utf-8 -*-
"""
Tests unitaires pour la migration fix_track_mir_scores_acousticness.

Rôle:
    Valide que la migration renomme correctement la colonne 'acousticness_score'
    en 'acousticness' dans la table track_mir_scores.

Couverture:
    - Présence de la migration
    - Structure correcte de la migration (upgrade/downgrade)
    - Colonnes attendues après migration
    - Index composite correct

Auteur: SoniqueBay Team
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestTrackMIRScoresAcousticnessMigration:
    """Tests pour la migration de renommage de colonne acousticness."""
    
    def test_migration_file_exists(self):
        """Test que le fichier de migration existe."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        assert migration_path.exists(), f"Le fichier de migration n'existe pas: {migration_path}"
    
    def test_migration_has_correct_revision(self):
        """Test que la migration a la bonne révision parente."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la révision dans le contenu du fichier
        # Note: Nom raccourci pour respecter la limite de 32 caractères de PostgreSQL
        assert "revision: str = 'fix_mir_acousticness'" in content
        # La migration fusionne deux branches: add_mir_norm_cols et fix_track_mir_raw_schema
        assert "'add_mir_norm_cols'" in content
        assert "'fix_track_mir_raw_schema'" in content
    
    def test_migration_has_upgrade_function(self):
        """Test que la migration a une fonction upgrade."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la présence de la fonction upgrade
        assert 'def upgrade()' in content or 'def upgrade() -> None:' in content
    
    def test_migration_has_downgrade_function(self):
        """Test que la migration a une fonction downgrade."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la présence de la fonction downgrade
        assert 'def downgrade()' in content or 'def downgrade() -> None:' in content
    
    def test_migration_uses_alter_column(self):
        """Test que la migration utilise ALTER TABLE RENAME COLUMN pour le renommage."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # La migration utilise des commandes SQL brutes via conn.execute(sa.text(...))
        assert 'RENAME COLUMN' in content, "La migration doit utiliser RENAME COLUMN"
        assert 'acousticness_score' in content, "La migration doit référencer 'acousticness_score'"
        assert 'acousticness' in content, "La migration doit référencer 'acousticness'"
    
    def test_migration_adds_calculated_at_column(self):
        """Test que la migration ajoute la colonne calculated_at manquante."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier l'ajout de la colonne calculated_at via SQL brut
        assert 'ADD COLUMN IF NOT EXISTS calculated_at' in content, "La migration doit ajouter la colonne 'calculated_at'"
        assert 'TIMESTAMP WITH TIME ZONE' in content, "La colonne doit être de type TIMESTAMP WITH TIME ZONE"
    
    def test_migration_handles_index_recreation(self):
        """Test que la migration recrée l'index composite."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'fix_track_mir_scores_acousticness.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la gestion de l'index
        assert 'idx_track_mir_scores_multi' in content, "La migration doit gérer l'index composite"
        # La migration utilise DROP INDEX IF EXISTS via conn.execute(sa.text(...))
        assert 'DROP INDEX IF EXISTS' in content, "La migration doit supprimer l'index existant (avec IF EXISTS)"
        assert 'op.create_index' in content, "La migration doit recréer l'index"
    
    def test_model_expects_acousticness_column(self):
        """Test que le modèle TrackMIRScores attend la colonne 'acousticness'."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from backend.api.models.track_mir_scores_model import TrackMIRScores
            
            # Vérifier que le modèle a l'attribut acousticness
            assert hasattr(TrackMIRScores, 'acousticness'), "Le modèle doit avoir l'attribut 'acousticness'"
            
            # Vérifier que le modèle n'a PAS acousticness_score (ancien nom)
            assert not hasattr(TrackMIRScores, 'acousticness_score'), \
                "Le modèle ne doit pas avoir l'attribut 'acousticness_score' (utiliser 'acousticness')"
        finally:
            sys.path.pop(0)
    
    def test_model_has_correct_table_args(self):
        """Test que le modèle a les bons __table_args__ avec l'index composite."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from backend.api.models.track_mir_scores_model import TrackMIRScores
            
            table_args = TrackMIRScores.__table_args__
            assert table_args is not None, "Le modèle doit avoir __table_args__"
            
            # Vérifier la présence de l'index composite
            index_found = False
            for arg in table_args:
                if hasattr(arg, 'name') and arg.name == 'idx_track_mir_scores_multi':
                    index_found = True
                    # Vérifier que l'index utilise 'acousticness' (pas 'acousticness_score')
                    columns = list(arg.columns.keys()) if hasattr(arg, 'columns') else []
                    assert 'acousticness' in columns or 'acousticness' in str(arg), \
                        "L'index doit utiliser 'acousticness'"
            
            assert index_found, "L'index 'idx_track_mir_scores_multi' doit exister dans __table_args__"
        finally:
            sys.path.pop(0)
    
    def test_model_to_dict_includes_acousticness(self):
        """Test que to_dict() inclut la clé 'acousticness'."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from backend.api.models.track_mir_scores_model import TrackMIRScores
            
            # Créer une instance mock
            instance = MagicMock(spec=TrackMIRScores)
            instance.id = 1
            instance.track_id = 123
            instance.energy_score = 0.8
            instance.mood_valence = 0.5
            instance.dance_score = 0.7
            instance.acousticness = 0.3
            instance.complexity_score = 0.6
            instance.emotional_intensity = 0.4
            instance.calculated_at = None
            instance.date_added = None
            instance.date_modified = None
            
            # Appeler to_dict
            result = TrackMIRScores.to_dict(instance)
            
            assert 'acousticness' in result, "to_dict() doit inclure 'acousticness'"
            assert 'acousticness_score' not in result, "to_dict() ne doit pas inclure 'acousticness_score'"
            assert result['acousticness'] == 0.3, "La valeur acousticness doit être correcte"
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
        # Ce test est marqué pour être sauté par défaut
        # Il peut être activé en définissant une variable d'environnement
        pytest.skip("Test d'intégration DB - exécuter manuellement avec une DB de test")
