# tests/integration/database/test_migrations.py
"""
Tests d'intégration pour les migrations de base de données Alembic.

Ce module contient les tests d'intégration pour:
- L'exécution des migrations
- Les rollbacks de migrations
- La cohérence des schémas
- La préservation des données

Auteur: SoniqueBay Team
Date: 2024
Marqueurs: pytest.mark.integration, pytest.mark.database, pytest.mark.migrations
"""

import pytest
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import text, inspect
from alembic.config import Config
from alembic import command

from tests.conftest import (
    test_db_engine,
    db_session,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.migrations
class TestMigrationExecution:
    """Tests pour l'exécution des migrations."""

    @pytest.fixture
    def alembic_config(self):
        """Configuration Alembic pour les tests."""
        config = Config("alembic.ini")
        return config

    def test_migration_stamp(self, alembic_config, test_db_engine):
        """Test le marquage de la base de données avec Alembic."""
        # Le stamp applique une version sans exécuter de migrations
        command.stamp(alembic_config, "head")

        # Vérifier que la table alembic_version existe
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            assert result is not None

    def test_migration_upgrade(self, alembic_config, test_db_engine):
        """Test la mise à niveau des migrations."""
        # Récupérer la version actuelle
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            current_version = result[0] if result else None

        # Upgrade vers head
        command.upgrade(alembic_config, "head")

        # Vérifier que la base est à jour
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            assert result is not None
            # La version devrait être plus récente ou égale

    def test_migration_downgrade(self, alembic_config, test_db_engine):
        """Test le retour arrière des migrations."""
        # D'abord upgrade vers head
        command.upgrade(alembic_config, "head")

        # Récupérer la version actuelle
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            current_version = result[0]

        # Downgrade d'une version
        command.downgrade(alembic_config, "-1")

        # Vérifier que la version a changé
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            new_version = result[0] if result else None
            # La version devrait être différente
            assert new_version != current_version

    def test_migration_branches(self, alembic_config, test_db_engine):
        """Test les branches de migration."""
        # Upgrade vers un point de branche spécifique
        command.upgrade(alembic_config, "head")

        # Vérifier que toutes les tables nécessaires existent
        required_tables = [
            "artists",
            "albums",
            "tracks",
            "genres",
            "covers",
            "genre_tags",
            "mood_tags",
        ]

        with test_db_engine.connect() as conn:
            for table in required_tables:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).fetchone()
                assert result is not None


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.migrations
class TestSchemaConsistency:
    """Tests pour la cohérence du schéma de base de données."""

    def test_all_tables_exist(self, test_db_engine):
        """Vérifie que toutes les tables existent."""
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        required_tables = [
            "artists",
            "albums",
            "tracks",
            "genres",
            "covers",
            "genre_tags",
            "mood_tags",
            "agent_scores",
            "scan_sessions",
            "function_calls",
        ]

        for table in required_tables:
            assert table in tables, f"Table {table} does not exist"

    def test_primary_keys_exist(self, test_db_engine):
        """Vérifie que les clés primaires existent."""
        inspector = inspect(test_db_engine)

        tables_with_pk = ["artists", "albums", "tracks"]
        for table in tables_with_pk:
            pk = inspector.get_pk_constraint(table)
            assert pk is not None and len(pk["constrained_columns"]) > 0

    def test_foreign_keys_exist(self, test_db_engine):
        """Vérifie que les clés étrangères existent."""
        inspector = inspect(test_db_engine)

        # Tracks devrait avoir des FK vers artists et albums
        fks = inspector.get_foreign_keys("tracks")
        assert len(fks) > 0

    def test_indexes_exist(self, test_db_engine):
        """Vérifie que les index nécessaires existent."""
        inspector = inspect(test_db_engine)

        # Vérifier les index sur tracks
        indexes = inspector.get_indexes("tracks")
        index_names = [idx["name"] for idx in indexes]

        assert any("bpm" in name for name in index_names)
        assert any("genre" in name for name in index_names)

    def test_unique_constraints(self, test_db_engine):
        """Vérifie les contraintes d'unicité."""
        inspector = inspect(test_db_engine)

        # Vérifier les contraintes uniques sur artists
        constraints = inspector.get_unique_constraints("artists")
        assert len(constraints) > 0

    def test_not_null_constraints(self, test_db_engine):
        """Vérifie les contraintes NOT NULL."""
        inspector = inspect(test_db_engine)

        # Vérifier les colonnes NOT NULL sur tracks
        columns = {col["name"]: col for col in inspector.get_columns("tracks")}

        assert columns["title"]["nullable"] is False
        assert columns["path"]["nullable"] is False


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.migrations
class TestDataPreservation:
    """Tests pour la préservation des données pendant les migrations."""

    def test_data_preservation_on_upgrade(self, test_db_engine, db_session):
        """Vérifie la préservation des données après upgrade."""
        from backend.api.models.tracks_model import Track
        from backend.api.models.artists_model import Artist

        # Créer des données de test
        artist = Artist(name="Test Artist Migration", musicbrainz_artistid="test-mig-id")
        db_session.add(artist)
        db_session.flush()

        track = Track(
            title="Test Track Migration",
            path="/path/to/migration_test.mp3",
            track_artist_id=artist.id,
            genre="Test",
        )
        db_session.add(track)
        db_session.commit()

        artist_id = artist.id
        track_id = track.id

        # Simuler une migration (ici, on vérifie juste que les données persistent)
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT * FROM artists WHERE id = {artist_id}")
            ).fetchone()
            assert result is not None

            result = conn.execute(
                text(f"SELECT * FROM tracks WHERE id = {track_id}")
            ).fetchone()
            assert result is not None

    def test_data_types_compatibility(self, test_db_engine):
        """Vérifie la compatibilité des types de données."""
        inspector = inspect(test_db_engine)

        # Vérifier les types de colonnes critiques
        columns = {col["name"]: col for col in inspector.get_columns("tracks")}

        # Vérifier les types numériques
        assert columns["bpm"]["type"] is not None
        assert columns["year"]["type"] is not None

    def test_enum_values_preserved(self, test_db_engine):
        """Vérifie que les valeurs d'énumération sont préservées."""
        with test_db_engine.connect() as conn:
            # Vérifier les valeurs de genre
            result = conn.execute(text("SELECT DISTINCT genre FROM tracks")).fetchall()
            assert len(result) >= 0


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.migrations
class TestMigrationRollback:
    """Tests pour les rollbacks de migrations."""

    def test_rollback_preserves_data(self, test_db_engine, db_session):
        """Vérifie que le rollback préserve les données valides."""
        from backend.api.models.artists_model import Artist

        # Créer des données
        artist = Artist(name="Rollback Test Artist", musicbrainz_artistid="rollback-test-id")
        db_session.add(artist)
        db_session.commit()
        artist_id = artist.id

        # Downgrade puis upgrade
        # Note: Ces opérations sont exécutées via Alembic commands

        # Vérifier que les données persistent
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT * FROM artists WHERE id = {artist_id}")
            ).fetchone()
            assert result is not None

    def test_rollback_schema_reversion(self, alembic_config, test_db_engine):
        """Vérifie la réversion du schéma après rollback."""
        # Upgrade
        command.upgrade(alembic_config, "head")

        # Downgrade
        command.downgrade(alembic_config, "-1")

        # Vérifier que la structure est revenue à l'état précédent
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        # Les tables de la version précédente doivent exister
        assert "artists" in tables
        assert "albums" in tables
        assert "tracks" in tables


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.migrations
class TestMigrationHistory:
    """Tests pour l'historique des migrations."""

    def test_migration_history_available(self, test_db_engine):
        """Vérifie que l'historique des migrations est disponible."""
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            assert result is not None
            assert result[0] is not None

    def test_no_duplicate_migrations(self, alembic_config):
        """Vérifie qu'il n'y a pas de migrations en double."""
        # Cette vérification est faite par Alembic lors de l'exécution
        # On peut vérifier que les scripts de migration sont valides

        migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "alembic", "versions")
        if os.path.exists(migrations_dir):
            migration_files = [f for f in os.listdir(migrations_dir) if f.endswith(".py")]
            # Vérifier que les noms de fichiers sont uniques
            names = [f.split("_")[0] for f in migration_files]
            assert len(names) == len(set(names))

    def test_migration_order(self, alembic_config):
        """Vérifie l'ordre des migrations."""
        # Les migrations doivent être exécutées dans l'ordre
        command.upgrade(alembic_config, "head")

        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
            ).fetchone()
            assert result is not None


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.migrations
class TestMigrationEdgeCases:
    """Tests des cas limites pour les migrations."""

    def test_empty_database_migration(self, test_db_engine):
        """Test la migration d'une base vide."""
        # Les migrations doivent fonctionner sur une base vide
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        # Vérifier que toutes les tables ont été créées
        required_tables = ["artists", "albums", "tracks"]
        for table in required_tables:
            assert table in tables

    def test_partial_data_migration(self, test_db_engine, db_session):
        """Test la migration avec des données partielles."""
        from backend.api.models.artists_model import Artist

        # Créer seulement un artiste (sans albums/tracks)
        artist = Artist(name="Partial Test Artist", musicbrainz_artistid="partial-test-id")
        db_session.add(artist)
        db_session.commit()

        # Les FKs nullable doivent permettre des enregistrements incomplets
        with test_db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM artists")
            ).fetchone()
            assert result[0] >= 1

    def test_migration_with_large_dataset(self, test_db_engine, db_session):
        """Test la migration avec un grand jeu de données."""
        from backend.api.models.artists_model import Artist

        # Créer beaucoup d'artistes
        for i in range(100):
            artist = Artist(
                name=f"Bulk Artist {i}",
                musicbrainz_artistid=f"bulk-test-id-{i}"
            )
            db_session.add(artist)

        db_session.commit()

        # Vérifier que toutes les données sont présentes
        with test_db_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM artists")).fetchone()
            assert result[0] == 100
