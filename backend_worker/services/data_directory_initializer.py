"""
Service d'initialisation des répertoires de données pour le backend_worker.

Ce service garantit que tous les répertoires nécessaires existent
avec les bonnes permissions avant l'exécution des tâches Celery.

Auteur : Kilo Code
"""

import os
import pwd
import grp
from pathlib import Path
from typing import Dict, Any
from backend_worker.utils.logging import logger


class DataDirectoryInitializer:
    """Service pour initialiser et vérifier les répertoires de données."""
    
    def __init__(self):
        """Initialise le service d'initialisation."""
        self.required_directories = [
            "/app/data",
            "/app/data/models", 
            "/app/data/celery_beat_data",
            "/app/data/search_indexes",
            "/app/data/whoosh_index",
            "/app/backend_worker/data",
            "/app/backend_worker/logs"
        ]
        
        self.current_user = self._get_current_user()
        logger.info(f"DataDirectoryInitializer initialisé pour l'utilisateur: {self.current_user}")
    
    def _get_current_user(self) -> Dict[str, Any]:
        """Récupère les informations sur l'utilisateur courant."""
        try:
            uid = os.getuid()
            gid = os.getgid()
            user = pwd.getpwuid(uid)
            group = grp.getgrgid(gid)
            
            return {
                "uid": uid,
                "gid": gid,
                "username": user.pw_name,
                "groupname": group.gr_name,
                "home": user.pw_dir
            }
        except Exception as e:
            logger.warning(f"Impossible de récupérer les informations utilisateur: {e}")
            return {"username": "unknown", "uid": -1, "gid": -1}
    
    def check_directory_permissions(self, directory_path: str) -> Dict[str, Any]:
        """Vérifie les permissions d'un répertoire."""
        path = Path(directory_path)
        result = {
            "path": directory_path,
            "exists": False,
            "readable": False,
            "writable": False,
            "executable": False,
            "owner": None,
            "group": None,
            "permissions": None,
            "parent_exists": False,
            "parent_writable": False,
            "error": None
        }
        
        try:
            result["exists"] = path.exists()
            
            if result["exists"]:
                result["readable"] = os.access(path, os.R_OK)
                result["writable"] = os.access(path, os.W_OK)
                result["executable"] = os.access(path, os.X_OK)
                
                stat_info = path.stat()
                result["owner"] = pwd.getpwuid(stat_info.st_uid).pw_name
                result["group"] = grp.getgrgid(stat_info.st_gid).gr_name
                result["permissions"] = oct(stat_info.st_mode)[-3:]
            
            # Vérifier le répertoire parent
            parent = path.parent
            result["parent_exists"] = parent.exists()
            if result["parent_exists"]:
                result["parent_writable"] = os.access(parent, os.W_OK)
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def initialize_directory(self, directory_path: str, force: bool = False) -> Dict[str, Any]:
        """
        Initialise un répertoire avec les bonnes permissions.
        
        Args:
            directory_path: Chemin du répertoire à créer
            force: Forcer la recréation même si existant
            
        Returns:
            Résultat de l'initialisation
        """
        path = Path(directory_path)
        result = {
            "path": directory_path,
            "created": False,
            "permissions_set": False,
            "ownership_set": False,
            "error": None,
            "warnings": []
        }
        
        try:
            # Créer le répertoire s'il n'existe pas ou si force=True
            if not path.exists() or force:
                path.mkdir(parents=True, exist_ok=True)
                result["created"] = True
                logger.info(f"Répertoire créé: {directory_path}")
            
            # Définir les permissions (755 pour les répertoires)
            try:
                os.chmod(path, 0o755)
                result["permissions_set"] = True
            except Exception as e:
                result["warnings"].append(f"Impossible de définir les permissions: {e}")
                logger.warning(f"Impossible de définir les permissions pour {directory_path}: {e}")
            
            # Définir la ownership si possible (utilisateur courant)
            try:
                if self.current_user["uid"] != -1:
                    os.chown(path, self.current_user["uid"], self.current_user["gid"])
                    result["ownership_set"] = True
            except Exception as e:
                result["warnings"].append(f"Impossible de définir la ownership: {e}")
                logger.warning(f"Impossible de définir la ownership pour {directory_path}: {e}")
            
            # Vérifier que le répertoire est maintenant accessible
            if os.access(path, os.R_OK | os.W_OK | os.X_OK):
                logger.info(f"Répertoire initialisé avec succès: {directory_path}")
            else:
                result["error"] = "Répertoire créé mais pas accessible en lecture/écriture"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erreur lors de l'initialisation de {directory_path}: {e}")
        
        return result
    
    def initialize_all_directories(self, force: bool = False) -> Dict[str, Any]:
        """
        Initialise tous les répertoires requis.
        
        Args:
            force: Forcer la recréation de tous les répertoires
            
        Returns:
            Résultat global de l'initialisation
        """
        logger.info("=== INITIALISATION DES RÉPERTOIRES DE DONNÉES ===")
        
        results = {
            "total_directories": len(self.required_directories),
            "successful": 0,
            "failed": 0,
            "warnings": 0,
            "details": []
        }
        
        for directory in self.required_directories:
            logger.info(f"Initialisation de {directory}...")
            
            # Vérifier l'état avant
            before_check = self.check_directory_permissions(directory)
            
            # Initialiser
            init_result = self.initialize_directory(directory, force)
            
            # Vérifier l'état après
            after_check = self.check_directory_permissions(directory)
            
            # Compiler le résultat
            detail = {
                "directory": directory,
                "before": before_check,
                "initialization": init_result,
                "after": after_check,
                "success": init_result["error"] is None and after_check["writable"]
            }
            
            results["details"].append(detail)
            
            if detail["success"]:
                results["successful"] += 1
                logger.info(f"✓ {directory} initialisé avec succès")
            else:
                results["failed"] += 1
                logger.error(f"✗ Échec d'initialisation de {directory}")
                if init_result["error"]:
                    logger.error(f"  Erreur: {init_result['error']}")
                if after_check["error"]:
                    logger.error(f"  Erreur de vérification: {after_check['error']}")
            
            if init_result["warnings"]:
                results["warnings"] += len(init_result["warnings"])
                for warning in init_result["warnings"]:
                    logger.warning(f"  Avertissement: {warning}")
        
        logger.info(f"=== INITIALISATION TERMINÉE: {results['successful']}/{results['total_directories']} réussis ===")
        
        return results
    
    def validate_data_access(self) -> Dict[str, Any]:
        """
        Valide l'accès aux répertoires de données critiques.
        
        Returns:
            Résultat de la validation
        """
        logger.info("=== VALIDATION DE L'ACCÈS AUX DONNÉES ===")
        
        critical_tests = [
            ("/app/data", "lecture et écriture"),
            ("/app/data/models", "création de fichiers modèles"),
            ("/app/data/celery_beat_data", "création de fichiers Celery Beat")
        ]
        
        results = {
            "all_accessible": True,
            "tests": []
        }
        
        for directory, description in critical_tests:
            test_result = {
                "directory": directory,
                "description": description,
                "accessible": False,
                "error": None
            }
            
            try:
                # Test de lecture
                if not os.access(directory, os.R_OK):
                    raise PermissionError(f"Pas de permission de lecture sur {directory}")
                
                # Test d'écriture
                if not os.access(directory, os.W_OK):
                    raise PermissionError(f"Pas de permission d'écriture sur {directory}")
                
                # Test de création de fichier temporaire
                test_file = Path(directory) / ".permission_test.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    test_result["accessible"] = True
                    logger.info(f"✓ Test d'accès réussi pour {directory}")
                except Exception as e:
                    raise PermissionError(f"Impossible de créer un fichier test dans {directory}: {e}")
                
            except Exception as e:
                test_result["error"] = str(e)
                test_result["accessible"] = False
                results["all_accessible"] = False
                logger.error(f"✗ Échec du test d'accès pour {directory}: {e}")
            
            results["tests"].append(test_result)
        
        return results


# Instance globale du service
data_directory_initializer = DataDirectoryInitializer()


def initialize_data_directories(force: bool = False) -> bool:
    """
    Fonction utilitaire pour initialiser tous les répertoires de données.
    
    Args:
        force: Forcer la recréation des répertoires
        
    Returns:
        True si succès, False sinon
    """
    try:
        result = data_directory_initializer.initialize_all_directories(force)
        return result["failed"] == 0
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des répertoires: {e}")
        return False


def validate_data_access() -> bool:
    """
    Fonction utilitaire pour valider l'accès aux données.
    
    Returns:
        True si accès valide, False sinon
    """
    try:
        result = data_directory_initializer.validate_data_access()
        return result["all_accessible"]
    except Exception as e:
        logger.error(f"Erreur lors de la validation d'accès: {e}")
        return False


if __name__ == "__main__":
    """Test du service d'initialisation."""
    print("=== TEST SERVICE D'INITIALISATION ===")
    
    # Test d'initialisation
    print("\n1. Test d'initialisation...")
    init_result = initialize_data_directories(force=True)
    print(f"Résultat: {'Succès' if init_result else 'Échec'}")
    
    # Test de validation
    print("\n2. Test de validation...")
    validate_result = validate_data_access()
    print(f"Résultat: {'Succès' if validate_result else 'Échec'}")
    
    print("\n=== TESTS TERMINÉS ===")