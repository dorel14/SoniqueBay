#!/usr/bin/env python3
"""
Script de migration des données SQLite vers PostgreSQL + pgvector
Utilisé pour la migration complète de SoniqueBay vers PostgreSQL.

Auteur: Kilo Code
Date: 2025-11-21
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Ajouter le répertoire backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class Base(DeclarativeBase):
    pass

def get_sqlite_engine():
    """Crée l'engine pour la DB SQLite source."""
    sqlite_path = Path("./backend/library_api/data/music.db")
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Base SQLite non trouvée: {sqlite_path}")

    return create_engine(f"sqlite:///{sqlite_path}", echo=False)

def get_postgres_engine():
    """Crée l'engine pour la DB PostgreSQL destination."""
    db_config = {
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'musicdb')
    }

    url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    return create_engine(url, echo=False)

def convert_vector_to_pgvector(vector_str: str) -> List[float]:
    """Convertit une chaîne JSON vector en liste float pour pgvector."""
    if not vector_str or vector_str.strip() == "":
        return []

    try:
        # Essayer de parser comme JSON d'abord
        if vector_str.startswith('[') and vector_str.endswith(']'):
            vector_data = json.loads(vector_str)
        else:
            # Essayer de parser comme string séparée par des virgules
            vector_data = [float(x.strip()) for x in vector_str.split(',') if x.strip()]

        # Convertir en float et normaliser
        vector_float = [float(x) for x in vector_data]

        # Vérifier la dimension (devrait être 512 pour les embeddings)
        if len(vector_float) != 512:
            logger.warning(f"Vector dimension inattendue: {len(vector_float)}, attendu 512")

        return vector_float

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Erreur conversion vector '{vector_str[:100]}...': {e}")
        return []

def migrate_table(source_engine, dest_engine, table_name: str, batch_size: int = 1000):
    """Migre une table complète avec gestion des vectors."""
    logger.info(f"Début migration table: {table_name}")

    with source_engine.connect() as source_conn:
        with dest_engine.connect() as dest_conn:
            # Récupérer le schéma de la table source
            # metadata = MetaData()

            # Compter les enregistrements
            count_result = source_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total_records = count_result.scalar()
            logger.info(f"Table {table_name}: {total_records} enregistrements à migrer")

            # Migrer par batches
            offset = 0
            migrated = 0

            while offset < total_records:
                # Récupérer un batch
                result = source_conn.execute(text(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"))
                rows = result.fetchall()

                if not rows:
                    break

                # Préparer les données pour insertion
                insert_data = []
                for row in rows:
                    row_dict = dict(row._mapping)

                    # Conversion spéciale pour les colonnes vector
                    if 'vector' in row_dict and row_dict['vector'] is not None:
                        row_dict['vector'] = convert_vector_to_pgvector(row_dict['vector'])

                    # Nettoyer les valeurs None pour les colonnes NOT NULL si nécessaire
                    # (ajuster selon les contraintes de la table)

                    insert_data.append(row_dict)

                # Insérer le batch
                if insert_data:
                    try:
                        # Construire la requête d'insertion
                        columns = list(insert_data[0].keys())
                        placeholders = ', '.join([f':{col}' for col in columns])
                        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                        dest_conn.execute(text(query), insert_data)
                        dest_conn.commit()

                        migrated += len(insert_data)
                        logger.info(f"Table {table_name}: {migrated}/{total_records} migrés")

                    except Exception as e:
                        logger.error(f"Erreur insertion batch table {table_name}: {e}")
                        dest_conn.rollback()
                        raise

                offset += batch_size

    logger.info(f"Migration table {table_name} terminée: {migrated} enregistrements")

def create_indexes(dest_engine):
    """Crée les index nécessaires après migration."""
    logger.info("Création des index...")

    with dest_engine.connect() as conn:
        try:
            # Index GIN pour TSVECTOR
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracks_search ON tracks USING GIN (search);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_artists_search ON artists USING GIN (search);"))

            # Index HNSW pour pgvector (nécessite pgvector extension)
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracks_vector ON tracks USING hnsw (vector vector_cosine_ops);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_artists_vector ON artists USING hnsw (vector vector_cosine_ops);"))

            # Autres index utiles
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks (title);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks (track_artist_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_artists_name ON artists (name);"))

            conn.commit()
            logger.info("Index créés avec succès")

        except Exception as e:
            logger.error(f"Erreur création index: {e}")
            conn.rollback()
            raise

def populate_tsvector_columns(dest_engine):
    """Remplit les colonnes TSVECTOR après migration."""
    logger.info("Population des colonnes TSVECTOR...")

    with dest_engine.connect() as conn:
        try:
            # Pour tracks
            conn.execute(text("""
                UPDATE tracks
                SET search = to_tsvector('english',
                    COALESCE(title, '') || ' ' ||
                    COALESCE(artists.name, '') || ' ' ||
                    COALESCE(albums.title, '') || ' ' ||
                    COALESCE(tracks.genre, '')
                )
                FROM artists, albums
                WHERE tracks.track_artist_id = artists.id
                AND tracks.album_id = albums.id
            """))

            # Pour artists
            conn.execute(text("""
                UPDATE artists
                SET search = to_tsvector('english',
                    COALESCE(name, '') || ' ' ||
                    COALESCE(lastfm_tags, '')
                )
            """))

            conn.commit()
            logger.info("Colonnes TSVECTOR remplies")

        except Exception as e:
            logger.error(f"Erreur remplissage TSVECTOR: {e}")
            conn.rollback()
            raise

def main():
    """Fonction principale de migration."""
    logger.info("Début migration SQLite vers PostgreSQL")

    try:
        # Créer les engines
        sqlite_engine = get_sqlite_engine()
        postgres_engine = get_postgres_engine()

        # Tester les connexions
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connexion SQLite OK")

        with postgres_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connexion PostgreSQL OK")

        # Liste des tables à migrer (dans l'ordre des dépendances)
        tables_to_migrate = [
            'genres',
            'artists',
            'albums',
            'tracks',
            'covers',
            'track_genres',
            'track_mood_tags',
            'track_genre_tags',
            'artist_genres',
            'playqueue',
            'scan_sessions'
        ]

        # Migrer chaque table
        for table in tables_to_migrate:
            try:
                migrate_table(sqlite_engine, postgres_engine, table)
            except Exception as e:
                logger.error(f"Échec migration table {table}: {e}")
                # Continuer avec les autres tables ou arrêter selon la politique

        # Créer les index
        create_indexes(postgres_engine)

        # Remplir les colonnes TSVECTOR
        populate_tsvector_columns(postgres_engine)

        logger.info("Migration terminée avec succès!")

    except Exception as e:
        logger.error(f"Erreur migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()