"""
Initialisation de sqlite-vec pour SoniqueBay.
Gère la création des tables virtuelles pour la vectorisation.
Utilise une connexion sqlite3 séparée pour sqlite-vec.
"""
import os
import sqlite3
from backend.utils.database import get_database_url
from backend.utils.logging import logger

# Connexion globale pour sqlite-vec (séparée de SQLAlchemy)
_vec_conn = None


def get_vec_connection():
    """
    Retourne la connexion sqlite3 pour les opérations vectorielles.
    Crée la connexion si elle n'existe pas.
    """
    global _vec_conn
    if _vec_conn is None:
        # Extraire le chemin de la base de données depuis l'URL SQLAlchemy
        db_url = get_database_url()
        if db_url.startswith('sqlite:///'):
            db_path = db_url[10:]  # Enlever 'sqlite:///'
        else:
            raise ValueError("Seules les bases SQLite sont supportées pour sqlite-vec")

        _vec_conn = sqlite3.connect(db_path)
        logger.info(f"Connexion sqlite-vec établie: {db_path}")

    return _vec_conn


def create_vector_tables():
    """
    Crée les tables virtuelles sqlite-vec nécessaires pour la vectorisation.
    """
    try:
        conn = get_vec_connection()

        # Vérifier si sqlite-vec est disponible
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        sqlite_version = cursor.fetchone()[0]
        logger.info(f"SQLite version: {sqlite_version}")

        # Charger l'extension sqlite-vec
        try:
            conn.enable_load_extension(True)
            logger.info("load_extension activée sur la connexion sqlite3")

            # Essayer de charger depuis le répertoire du projet d'abord
            vec_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sqlite-vec', 'vec0')
            logger.info(f"Chemin projet essayé: {vec_path}.so / {vec_path}.dll")
            if os.path.exists(vec_path + '.so'):
                logger.info(f"Fichier {vec_path}.so trouvé, chargement...")
                conn.load_extension(vec_path)
                logger.info("Extension sqlite-vec chargée depuis le répertoire du projet (.so)")
            elif os.path.exists(vec_path + '.dll'):
                logger.info(f"Fichier {vec_path}.dll trouvé, chargement...")
                conn.load_extension(vec_path)
                logger.info("Extension sqlite-vec chargée depuis le répertoire du projet (.dll)")
            else:
                logger.warning("Aucun fichier trouvé dans le répertoire projet, essai système")
                # Charger depuis le système
                try:
                    conn.load_extension('vec0')
                    logger.info("Extension sqlite-vec chargée depuis le système")
                except Exception as sys_e:
                    logger.error(f"Échec chargement système: {sys_e}")
                    # Essayer les chemins courants pour sqlite-vec installé via pip
                    import sqlite_vec
                    vec_module_path = os.path.dirname(sqlite_vec.__file__)
                    possible_paths = [
                        os.path.join(vec_module_path, 'vec0'),
                        '/usr/local/lib/sqlite-vec/vec0',
                        '/opt/venv/lib/python3.13/site-packages/sqlite_vec/vec0'
                    ]
                    for path in possible_paths:
                        logger.info(f"Essai chemin alternatif: {path}")
                        if os.path.exists(path + '.so'):
                            logger.info(f"Fichier trouvé: {path}.so, chargement...")
                            conn.load_extension(path)
                            logger.info("Extension sqlite-vec chargée depuis chemin alternatif")
                            break
                        elif os.path.exists(path):
                            logger.info(f"Fichier trouvé sans extension: {path}, chargement...")
                            conn.load_extension(path)
                            logger.info("Extension sqlite-vec chargée depuis chemin alternatif (sans ext)")
                            break
                    else:
                        logger.error("Aucun chemin alternatif n'a fonctionné")
                        raise sys_e

            conn.enable_load_extension(False)
        except Exception as e:
            logger.error(f"Impossible de charger l'extension sqlite-vec: {e}")
            return False

        # Créer la table virtuelle track_vectors pour vérifier la disponibilité de sqlite-vec
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS track_vectors
                USING vec0(
                    track_id INTEGER PRIMARY KEY,
                    embedding TEXT
                );
            """)
            conn.commit()
            logger.info("Table virtuelle track_vectors créée avec succès - sqlite-vec est disponible")
            return True
        except Exception as e:
            logger.error(f"Échec de création de la table virtuelle - sqlite-vec n'est pas disponible: {e}")
            return False

    except Exception as e:
        logger.error(f"Erreur lors de la création des tables virtuelles: {e}")
        return False


def initialize_sqlite_vec():
    """
    Initialise sqlite-vec et crée les tables nécessaires.
    À appeler au démarrage de l'application.
    """
    logger.info("Initialisation de sqlite-vec...")
    success = create_vector_tables()

    if success:
        logger.info("sqlite-vec initialisé avec succès")
    else:
        logger.warning("Échec de l'initialisation de sqlite-vec")

    return success


def close_vec_connection():
    """
    Ferme la connexion sqlite-vec si elle existe.
    """
    global _vec_conn
    if _vec_conn:
        _vec_conn.close()
        _vec_conn = None
        logger.info("Connexion sqlite-vec fermée")


if __name__ == "__main__":
    # Permet de tester l'initialisation
    try:
        initialize_sqlite_vec()
    finally:
        close_vec_connection()