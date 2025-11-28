#!/usr/bin/env python3
"""
Script pour vérifier les métriques de taille des arguments Celery.
Usage: python scripts/check_celery_metrics.py
"""

import sys
import os

# Ajouter le backend_worker au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_worker'))

try:
    from backend_worker.utils.celery_monitor import get_size_summary, auto_configure_celery_limits
    
    print("=== MÉTRIQUES CELERY MONITOR ===")
    print(get_size_summary())
    
    print("\n=== RECOMMANDATIONS ===")
    recommended = auto_configure_celery_limits()
    if recommended:
        print(f"Limite recommandée: {recommended:,} caractères ({recommended/1024:.0f}KB)")
        print("\nPour appliquer cette limite dans celery_app.py:")
        print(f"celery.amqp.argsrepr_maxsize = {recommended}")
        print(f"celery.amqp.kwargsrepr_maxsize = {recommended}")
    else:
        print("Pas assez de données pour faire une recommandation")
        
    print("\nOptions disponibles:")
    print("- Le monitoring est actif automatiquement dans celery_app.py")
    print("- Utilisez 'reset_metrics()' pour remettre à zéro")
    
except ImportError as e:
    print(f"Erreur d'import: {e}")
    print("Assurez-vous que le backend_worker est accessible")
except Exception as e:
    print(f"Erreur: {e}")