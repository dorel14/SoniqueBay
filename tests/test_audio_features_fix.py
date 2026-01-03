#!/usr/bin/env python3
"""
Script de test et validation des corrections du pipeline audio features

Ce script :
1. Lance le test du pipeline complet
2. Valide que les corrections fonctionnent
3. Vérifie la nouvelle architecture scan → extraction → stockage

Usage:
    python scripts/test_audio_features_fix.py
"""

import sys
import subprocess
import os
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend_worker.utils.logging import get_logger

logger = get_logger(__name__)


def run_pytest_test():
    """Lance le test pytest spécifique pour le pipeline audio"""
    logger.info("🚀 Lancement du test du pipeline audio features...")
    
    test_file = "tests/worker/test_audio_features_pipeline.py"
    
    # Commande pytest avec output détaillé
    cmd = [
        "python", "-m", "pytest", 
        test_file,
        "-v",  # Verbose
        "--tb=short",  # Traceback court
        "--no-header"  # Pas d'en-tête
    ]
    
    try:
        logger.info(f"Exécution: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=300  # Timeout de 5 minutes
        )
        
        if result.returncode == 0:
            logger.info("✅ Test du pipeline audio PASSÉ!")
            logger.info("📋 Sortie du test:")
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            
            return True
        else:
            logger.error("❌ Test du pipeline audio ÉCHOUÉ!")
            logger.error(f"Code de sortie: {result.returncode}")
            
            if result.stderr:
                logger.error("🔴 Erreurs:")
                for line in result.stderr.split('\n'):
                    if line.strip():
                        logger.error(f"  {line}")
            
            if result.stdout:
                logger.info("📋 Sortie standard:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("⏰ Timeout lors de l'exécution du test!")
        return False
    except Exception as e:
        logger.error(f"💥 Erreur lors du lancement du test: {e}")
        return False


def validate_dependencies():
    """Vérifie que les dépendances nécessaires sont installées"""
    logger.info("🔍 Validation des dépendances...")
    
    required_modules = [
        'librosa',
        'soundfile',
        'numpy',
        'scipy'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module} - OK")
        except ImportError:
            logger.warning(f"❌ {module} - MANQUANT")
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"📦 Modules manquants: {', '.join(missing_modules)}")
        logger.info("💡 Installation recommandée:")
        for module in missing_modules:
            logger.info(f"   pip install {module}")
        return False
    
    return True


def run_diagnostic_check():
    """Effectue un diagnostic complet du système"""
    logger.info("🔬 Diagnostic complet du système audio...")
    
    # Vérifier les dépendances
    deps_ok = validate_dependencies()
    
    # Vérifier les fichiers de service
    service_files = [
        "backend_worker/services/audio_features_service.py",
        "backend_worker/services/scan_optimizer.py"
    ]
    
    for file_path in service_files:
        if os.path.exists(file_path):
            logger.info(f"✅ Service trouvé: {file_path}")
        else:
            logger.error(f"❌ Service manquant: {file_path}")
            deps_ok = False
    
    # Vérifier le test
    test_file = "tests/worker/test_audio_features_pipeline.py"
    if os.path.exists(test_file):
        logger.info(f"✅ Test trouvé: {test_file}")
    else:
        logger.error(f"❌ Test manquant: {test_file}")
        deps_ok = False
    
    return deps_ok


def main():
    """Point d'entrée principal"""
    logger.info("🎵 Démarrage de la validation des corrections audio features")
    logger.info("=" * 60)
    
    # Diagnostic initial
    if not run_diagnostic_check():
        logger.error("💥 Diagnostic initial échoué!")
        logger.error("Corrigez les dépendances et fichiers manquants avant de continuer.")
        return False
    
    # Lancer le test du pipeline
    test_passed = run_pytest_test()
    
    # Résumé final
    logger.info("=" * 60)
    if test_passed:
        logger.info("🎉 VALIDATION COMPLÈTE RÉUSSIE!")
        logger.info("📋 Résumé des corrections validées:")
        logger.info("  ✅ 1. Collision de noms résolue (extract_audio_features)")
        logger.info("  ✅ 2. Fallback Librosa fonctionnel quand tags AcoustID vides")
        logger.info("  ✅ 3. Appels avec paramètres vides corrigés")
        logger.info("  ✅ 4. Logs améliorés pour diagnostiquer l'extraction")
        logger.info("  ✅ 5. Pipeline complet scan → extraction → stockage validé")
        logger.info("")
        logger.info("🚀 Le système audio features est maintenant opérationnel!")
        logger.info("   Les tags (BPM, tonalité, energy, etc.) seront correctement")
        logger.info("   extraits et stockés en base lors des scans musicaux.")
        
        return True
    else:
        logger.error("💥 VALIDATION ÉCHOUÉE!")
        logger.error("📋 Prochaines étapes recommandées:")
        logger.error("  1. Vérifiez les logs d'erreur ci-dessus")
        logger.error("  2. Installez les dépendances manquantes")
        logger.error("  3. Relancez le script de validation")
        logger.error("  4. En cas de problème persistant, vérifiez l'architecture")
        
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)