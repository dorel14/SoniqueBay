"""
Initialisation de sqlite-vec pour SoniqueBay.
Gère la création des tables virtuelles pour la vectorisation.
Utilise une connexion sqlite3 séparée pour sqlite-vec.
"""
import os
import sqlite3
from backend.api.utils.database import get_database_url
from backend.api.utils.logging import logger

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
        # Autoriser l'utilisation des extensions SQLite
        _vec_conn.execute("PRAGMA trusted_schema = ON;")
        _vec_conn.execute("PRAGMA module_list = ON;")
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
            
            # Vérifier les permissions du fichier
            try:
                import sqlite_vec
                vec_module_path = os.path.dirname(sqlite_vec.__file__)
                vec_so_path = os.path.join(vec_module_path, 'vec0.so')
                logger.info(f"Permissions du fichier vec0.so: {oct(os.stat(vec_so_path).st_mode)}")
            except Exception as e:
                logger.warning(f"Impossible de vérifier les permissions: {e}")

            # Essayer de charger depuis le package pip d'abord
            try:
                # Chercher d'abord dans le chemin système
                try:
                    conn.load_extension('/usr/local/lib/python3.11/site-packages/sqlite_vec/vec0.so')
                    logger.info("Extension sqlite-vec chargée depuis le chemin système")
                    return True
                except Exception as sys_e:
                    logger.warning(f"Échec du chargement depuis le chemin système: {sys_e}")

                # Essayer ensuite via le package pip
                import sqlite_vec
                vec_module_path = os.path.dirname(sqlite_vec.__file__)
                vec_path = os.path.join(vec_module_path, 'vec0.so')
                logger.info(f"Tentative de chargement depuis le package pip: {vec_path}")
                
                if os.path.exists(vec_path):
                    conn.load_extension(vec_path)
                    logger.info("Extension sqlite-vec chargée depuis le package pip")
                    return True
                else:
                    raise FileNotFoundError(f"Extension non trouvée dans {vec_path}")
                    
            except Exception as e:
                logger.error(f"Échec du chargement de l'extension: {e}")
                raise RuntimeError("Impossible de charger l'extension sqlite-vec") from e

            # Ne pas désactiver le chargement d'extension ici car on en a encore besoin
        except Exception as e:
            logger.error(f"Impossible de charger l'extension sqlite-vec: {str(e)}")
            logger.error("Vérifiez que le package sqlite-vec est installé: pip install sqlite-vec")
            raise RuntimeError("Échec de l'initialisation de sqlite-vec") from e

        # Créer la table virtuelle track_vectors pour vérifier la disponibilité de sqlite-vec
        try:
            # Supprimer la table si elle existe pour la recréer avec la bonne configuration
            cursor.execute("DROP TABLE IF EXISTS track_vectors")
            # Ne pas recharger l'extension ici car déjà chargée plus haut
            # Créer la table virtuelle avec la dimension spécifiée et l'index
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS track_vectors USING vec0(
                    id INTEGER PRIMARY KEY,
                    embedding FLOAT[384]
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