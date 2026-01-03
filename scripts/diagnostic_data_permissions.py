#!/usr/bin/env python3
"""
Script de diagnostic pour le problème d'autorisation /app/data
dans le backend_worker.

Ce script diagnostique les problèmes de permissions et de montage
des répertoires de données pour les workers Celery.

Usage:
    python scripts/diagnostic_data_permissions.py

Auteur : Kilo Code
"""

import os
import pwd
import grp
from pathlib import Path
from typing import Dict, Any


def get_current_user_info() -> Dict[str, Any]:
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
            "home": user.pw_dir,
            "shell": user.pw_shell
        }
    except Exception as e:
        return {"error": str(e)}


def check_directory_permissions(directory_path: str) -> Dict[str, Any]:
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
        # Vérifier l'existence
        result["exists"] = path.exists()
        
        if result["exists"]:
            # Vérifier les permissions
            result["readable"] = os.access(path, os.R_OK)
            result["writable"] = os.access(path, os.W_OK)
            result["executable"] = os.access(path, os.X_OK)
            
            # Informations détaillées sur les permissions
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


def test_directory_creation(directory_path: str) -> Dict[str, Any]:
    """Teste la création d'un répertoire."""
    path = Path(directory_path)
    result = {
        "path": directory_path,
        "can_create": False,
        "can_create_parent": False,
        "created": False,
        "cleanup_needed": False,
        "error": None
    }
    
    try:
        # Vérifier si on peut créer le répertoire parent
        try:
            test_parent = path.parent / "test_permissions_temp"
            test_parent.mkdir(exist_ok=True)
            result["can_create_parent"] = True
            test_parent.rmdir()
        except Exception as e:
            result["can_create_parent"] = False
            result["error"] = f"Impossible de créer dans le parent: {e}"
        
        # Vérifier si on peut créer le répertoire
        try:
            path.mkdir(parents=True, exist_ok=True)
            result["can_create"] = True
            result["created"] = True
            
            # Vérifier si on peut écrire dedans
            test_file = path / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            result["cleanup_needed"] = True
            
        except Exception as e:
            result["can_create"] = False
            result["error"] = f"Impossible de créer le répertoire: {e}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def check_docker_environment() -> Dict[str, Any]:
    """Vérifie l'environnement Docker."""
    result = {
        "in_docker": False,
        "docker_check_file": None,
        "mount_points": [],
        "environment_vars": {}
    }
    
    # Vérifier si on est dans Docker
    docker_files = [
        "/.dockerenv",
        "/run/.containerenv"
    ]
    
    for docker_file in docker_files:
        if os.path.exists(docker_file):
            result["in_docker"] = True
            result["docker_check_file"] = docker_file
            break
    
    # Vérifier les variables d'environnement importantes
    important_vars = [
        "USER", "HOME", "PATH", "PYTHONPATH", 
        "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
    ]
    
    for var in important_vars:
        result["environment_vars"][var] = os.getenv(var)
    
    return result


def check_celery_worker_info() -> Dict[str, Any]:
    """Vérifie les informations spécifiques à Celery."""
    result = {
        "celery_importable": False,
        "celery_version": None,
        "current_queue": None,
        "worker_info": {}
    }
    
    try:
        import celery
        result["celery_importable"] = True
        result["celery_version"] = celery.__version__
        
        # Tenter d'obtenir des infos sur le worker courant
        try:
            from celery.task.control import inspect
            i = inspect()
            active_tasks = i.active()
            if active_tasks:
                result["worker_info"]["active_tasks"] = list(active_tasks.keys())
        except Exception:
            pass
            
    except ImportError:
        pass
    
    return result


def main():
    """Fonction principale de diagnostic."""
    print("=== DIAGNOSTIC PERMISSIONS /app/data ===\n")
    
    # 1. Informations utilisateur
    print("1. INFORMATIONS UTILISATEUR")
    user_info = get_current_user_info()
    for key, value in user_info.items():
        print(f"   {key}: {value}")
    print()
    
    # 2. Environnement Docker
    print("2. ENVIRONNEMENT DOCKER")
    docker_info = check_docker_environment()
    for key, value in docker_info.items():
        print(f"   {key}: {value}")
    print()
    
    # 3. Informations Celery
    print("3. INFORMATIONS CELERY")
    celery_info = check_celery_worker_info()
    for key, value in celery_info.items():
        print(f"   {key}: {value}")
    print()
    
    # 4. Test des répertoires critiques
    print("4. TEST DES RÉPERTOIRES CRITIQUES")
    critical_dirs = [
        "/app",
        "/app/data",
        "/app/data/models",
        "/app/data/celery_beat_data",
        "/app/backend_worker",
        "/app/backend_worker/data"
    ]
    
    for directory in critical_dirs:
        print(f"\n   --- Répertoire: {directory} ---")
        perms = check_directory_permissions(directory)
        for key, value in perms.items():
            if key != "path":  # Déjà affiché
                print(f"      {key}: {value}")
    
    # 5. Test de création
    print("\n5. TEST DE CRÉATION DES RÉPERTOIRES")
    test_dirs = [
        "/app/data/models",
        "/app/data/celery_beat_data", 
        "/app/backend_worker/data"
    ]
    
    for directory in test_dirs:
        print(f"\n   --- Test création: {directory} ---")
        creation_test = test_directory_creation(directory)
        for key, value in creation_test.items():
            print(f"      {key}: {value}")
    
    # 6. Recommandations
    print("\n6. RECOMMANDATIONS")
    print("   Basé sur les résultats ci-dessus:")
    print("   - Vérifiez que le volume /app/data est correctement monté")
    print("   - Assurez-vous que l'utilisateur Celery a les permissions")
    print("   - Vérifiez la configuration Docker du backend_worker")
    print("   - Consultez les logs Docker pour plus de détails")
    
    # 7. Test spécifique du service qui échoue
    print("\n7. TEST DU SERVICE QUI ÉCHOUE")
    try:
        print("   Tentative d'import du ModelPersistenceService...")
        from backend_worker.services.model_persistence_service import ModelPersistenceService
        print("   ✓ Import réussi")
        
        print("   Tentative d'initialisation...")
        ModelPersistenceService()
        print("   ✓ Initialisation réussie")
        
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        print("   C'est probablement la cause de l'erreur Permission denied")


if __name__ == "__main__":
    main()