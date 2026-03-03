# -*- coding: utf-8 -*-
"""
Tests unitaires pour la migration add_calculated_at_to_mir_scores.

Rôle:
    Valide que la migration ajoute correctement la colonne 'calculated_at'
    à la table track_mir_scores.

Couverture:
    - Présence de la migration
    - Structure correcte de la migration (upgrade/downgrade)
    - Colonne calculated_at ajoutée

Auteur: SoniqueBay Team
"""

import pytest
import os
import sys
from pathlib import Path


class TestAddCalculatedAtMigration:
    """Tests pour la migration d'ajout de colonne calculated_at."""
    
    def test_migration_file_exists(self):
        """Test que le fichier de migration existe."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'add_calculated_at_to_mir_scores.py'
        assert migration_path.exists(), f"Le fichier de migration n'existe pas: {migration_path}"
    
    def test_migration_has_correct_revision(self):
        """Test que la migration a la bonne révision parente."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'add_calculated_at_to_mir_scores.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la révision dans le contenu du fichier
        assert "revision: str = 'add_calc_at_mir_scores'" in content
        # La migration dépend de fix_mir_acousticness
        assert "'fix_mir_acousticness'" in content
    
    def test_migration_has_upgrade_function(self):
        """Test que la migration a une fonction upgrade."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'add_calculated_at_to_mir_scores.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la présence de la fonction upgrade
        assert 'def upgrade()' in content or 'def upgrade() -> None:' in content
    
    def test_migration_has_downgrade_function(self):
        """Test que la migration a une fonction downgrade."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'add_calculated_at_to_mir_scores.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la présence de la fonction downgrade
        assert 'def downgrade()' in content or 'def downgrade() -> None:' in content
    
    def test_migration_adds_calculated_at_column(self):
        """Test que la migration ajoute la colonne calculated_at."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'add_calculated_at_to_mir_scores.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier l'ajout de la colonne calculated_at
        assert 'calculated_at' in content, "La migration doit référencer 'calculated_at'"
        assert 'TIMESTAMP WITH TIME ZONE' in content, "La colonne doit être de type TIMESTAMP WITH TIME ZONE"
        assert 'ADD COLUMN' in content, "La migration doit utiliser ADD COLUMN"
    
    def test_migration_checks_column_exists(self):
        """Test que la migration vérifie si la colonne existe déjà."""
        migration_path = Path(__file__).parent.parent.parent / 'alembic' / 'versions' / 'add_calculated_at_to_mir_scores.py'
        content = migration_path.read_text(encoding='utf-8')
        
        # Vérifier la vérification d'existence
        assert 'information_schema.columns' in content, "La migration doit vérifier l'existence de la colonne"
        assert 'DROP COLUMN IF EXISTS' in content, "Le downgrade doit utiliser IF EXISTS"


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
        pytest.skip("Test d'intégration DB - exécuter manuellement avec une DB de test")
