#!/usr/bin/env python3
"""
Script de diagnostic pour la base de données Flower corrompue
Analyse les sources possibles du problème et génère des logs de diagnostic
"""

import logging
import os
import shelve

# Import conditionnel pour _gdbm (uniquement sur Unix/Linux)
try:
    import _gdbm
    GDBM_AVAILABLE = True
except ImportError:
    GDBM_AVAILABLE = False
    logging.warning("Module _gdbm non disponible (Windows detected)")

# Configuration du logging selon les conventions SoniqueBay
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chemins de diagnostic
FLOWER_DB_PATH = "/var/flower/flower.db"
FLOWER_DATA_DIR = "/var/flower"
LOCAL_FLOWER_PATH = "./data/flower_data/flower.db"
LOCAL_FLOWER_DIR = "./data/flower_data"


def check_file_permissions(path: str) -> dict:
    """Vérifie les permissions d'un fichier/répertoire"""
    info = {
        "path": path,
        "exists": False,
        "is_file": False,
        "is_dir": False,
        "readable": False,
        "writable": False,
        "executable": False,
        "size": 0,
        "permissions": None,
        "error": None
    }
    
    try:
        if os.path.exists(path):
            info["exists"] = True
            info["is_file"] = os.path.isfile(path)
            info["is_dir"] = os.path.isdir(path)
            info["readable"] = os.access(path, os.R_OK)
            info["writable"] = os.access(path, os.W_OK)
            info["executable"] = os.access(path, os.X_OK)
            
            if info["is_file"]:
                info["size"] = os.path.getsize(path)
                file_stat = os.stat(path)
                info["permissions"] = oct(file_stat.st_mode)[-3:]
            
            logger.info(f"✓ Fichier/Répertoire '{path}' trouvé")
            if info["is_file"]:
                logger.info(f"  - Taille: {info['size']} bytes")
            logger.info(f"  - Permissions: {info['permissions']}")
            logger.info(f"  - Lecture: {info['readable']}, Écriture: {info['writable']}")
        else:
            logger.warning(f"✗ Fichier/Répertoire '{path}' n'existe pas")
            
    except Exception as e:
        info["error"] = str(e)
        logger.error(f"✗ Erreur lors de la vérification de '{path}': {e}")
    
    return info


def check_gdbm_database(path: str) -> dict:
    """Vérifie l'intégrité d'une base de données GDBM"""
    info = {
        "path": path,
        "valid": False,
        "corrupted": False,
        "error": None,
        "keys_count": 0,
        "can_open": False
    }
    
    if not GDBM_AVAILABLE:
        info["error"] = "Module _gdbm non disponible (Windows)"
        logger.warning(f"⚠ Module _gdbm non disponible - diagnostic GDBM limité pour '{path}'")
        
        # Test basique d'ouverture de fichier shelve
        try:
            with shelve.open(path, "r") as db_file:
                keys = list(db_file.keys())
                info["keys_count"] = len(keys)
                info["can_open"] = True
                info["valid"] = True
                logger.info(f"✓ Base de données '{path}' peut être ouverte (mode Windows)")
                logger.info(f"  - Nombre de clés: {info['keys_count']}")
        except Exception as e:
            info["error"] = str(e)
            logger.error(f"✗ Erreur lors de l'ouverture de '{path}': {e}")
        
        return info
    
    try:
        # Test d'ouverture en lecture
        with shelve.open(path, "r") as db_file:
            info["can_open"] = True
            # Tentative d'accès aux clés
            keys = list(db_file.keys())
            info["keys_count"] = len(keys)
            info["valid"] = True
            logger.info(f"✓ Base de données GDBM '{path}' est valide")
            logger.info(f"  - Nombre de clés: {info['keys_count']}")
            
    except _gdbm.error as e:
        if "Database needs recovery" in str(e):
            info["corrupted"] = True
            logger.error(f"✗ Base de données GDBM '{path}' est corrompue et nécessite une récupération")
        else:
            info["error"] = f"GDBM error: {e}"
            logger.error(f"✗ Erreur GDBM avec '{path}': {e}")
            
    except Exception as e:
        info["error"] = str(e)
        logger.error(f"✗ Erreur lors de la vérification de '{path}': {e}")
    
    return info


def check_disk_space(path: str) -> dict:
    """Vérifie l'espace disque disponible"""
    info = {
        "path": path,
        "total_space": 0,
        "free_space": 0,
        "used_space": 0,
        "usage_percent": 0,
        "error": None
    }
    
    try:
        statvfs = os.statvfs(path)
        total = statvfs.f_frsize * statvfs.f_blocks
        free = statvfs.f_frsize * statvfs.f_bavail
        used = total - free
        usage_percent = (used / total) * 100 if total > 0 else 0
        
        info.update({
            "total_space": total,
            "free_space": free,
            "used_space": used,
            "usage_percent": usage_percent
        })
        
        logger.info(f"✓ Espace disque pour '{path}':")
        logger.info(f"  - Total: {total // (1024**3)} GB")
        logger.info(f"  - Libre: {free // (1024**3)} GB")
        logger.info(f"  - Utilisé: {used // (1024**3)} GB ({usage_percent:.1f}%)")
        
    except Exception as e:
        info["error"] = str(e)
        logger.error(f"✗ Erreur lors de la vérification de l'espace disque: {e}")
    
    return info


def main():
    """Fonction principale de diagnostic"""
    logger.info("=== DIAGNOSTIC DE LA BASE DE DONNÉES FLOWER ===")
    
    # 1. Vérification des fichiers Flower (local et conteneur)
    logger.info("\n1. VÉRIFICATION DES FICHIERS FLOWER:")
    
    local_db_info = check_file_permissions(LOCAL_FLOWER_PATH)
    local_dir_info = check_file_permissions(LOCAL_FLOWER_DIR)
    
    # 2. Vérification de l'intégrité de la base de données
    logger.info("\n2. VÉRIFICATION DE L'INTÉGRITÉ DE LA BASE DE DONNÉES:")
    
    if local_db_info["exists"] and local_db_info["is_file"]:
        db_info = check_gdbm_database(LOCAL_FLOWER_PATH)
    else:
        db_info = {"corrupted": False, "error": "Base de données non trouvée"}
        logger.warning("⚠ Base de données Flower non trouvée")
    
    # 3. Vérification de l'espace disque
    logger.info("\n3. VÉRIFICATION DE L'ESPACE DISQUE:")
    
    if local_dir_info["exists"]:
        disk_info = check_disk_space(LOCAL_FLOWER_DIR)
    else:
        disk_info = {"error": "Répertoire de données non trouvé"}
        logger.warning("⚠ Répertoire de données Flower non trouvé")
    
    # 4. Analyse des sources possibles du problème
    logger.info("\n4. ANALYSE DES SOURCES POSSIBLES:")
    
    sources_analyse = []
    
    # Source 1: Corruption de base de données
    if db_info.get("corrupted", False):
        sources_analyse.append("🔴 CONFIRMÉE: Corruption de la base de données GDBM Flower")
        logger.error("CONFIRMÉ: La base de données Flower est corrompue")
    
    # Source 2: Problème de permissions
    if local_db_info["exists"]:
        if not local_db_info["readable"] or not local_db_info["writable"]:
            sources_analyse.append("🟡 POSSIBLE: Problème de permissions sur la base de données")
            logger.warning("PROBLÈME DE PERMISSIONS détecté")
    
    # Source 3: Espace disque insuffisant
    if disk_info.get("usage_percent", 0) > 90:
        sources_analyse.append("🟡 POSSIBLE: Espace disque insuffisant")
        logger.warning(f"ATTENTION: Utilisation disque élevée ({disk_info['usage_percent']:.1f}%)")
    
    # Source 4: Fichier manquant
    if not local_db_info["exists"]:
        sources_analyse.append("🟡 POSSIBLE: Fichier de base de données manquant")
        logger.warning("FICHIER DE BASE DE DONNÉES manquant")
    
    # 5. Recommandations
    logger.info("\n5. RECOMMANDATIONS:")
    
    if db_info.get("corrupted", False):
        logger.info("✅ SOLUTION RECOMMANDÉE: Utiliser le script de récupération de base de données")
        logger.info("   - Implémenter une vérification et récupération automatique au démarrage")
        logger.info("   - Utiliser gdbmtool pour réparer la base de données")
    
    if not local_db_info["exists"]:
        logger.info("✅ SOLUTION: Créer le répertoire et initialiser la base de données")
    
    if local_dir_info["exists"] and (not local_dir_info["readable"] or not local_dir_info["writable"]):
        logger.info("✅ SOLUTION: Corriger les permissions du répertoire flower_data")
    
    # Résumé final
    logger.info("\n=== RÉSUMÉ DU DIAGNOSTIC ===")
    if sources_analyse:
        for source in sources_analyse:
            logger.info(source)
    else:
        logger.info("✅ Aucune source de problème identifiée")
    
    return {
        "local_db_info": local_db_info,
        "local_dir_info": local_dir_info,
        "db_info": db_info,
        "disk_info": disk_info,
        "sources_analyse": sources_analyse
    }


if __name__ == "__main__":
    main()