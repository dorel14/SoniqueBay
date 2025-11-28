#!/usr/bin/env python3
"""
Script pour vérifier les métriques Celery depuis votre machine locale.
Version corrigée : meilleure gestion des timeouts et fallbacks.
Usage: python scripts/check_celery_metrics_local.py
"""

import subprocess
import json
from datetime import datetime

def run_in_container(container_name, command, timeout=60):
    """Exécute une commande dans un conteneur Docker avec timeout adaptatif."""
    try:
        print(f"🔍 Test {container_name}...")
        result = subprocess.run([
            'docker', 'exec', container_name, 'python3', '-c', command
        ], capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            print(f"✅ {container_name} - Commande réussie")
            return result.stdout.strip()
        else:
            print(f"❌ {container_name} - Code erreur {result.returncode}: {result.stderr[:200]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"⏰ {container_name} - Timeout après {timeout}s")
        return None
    except Exception as e:
        print(f"❌ {container_name} - Erreur: {e}")
        return None

def get_worker_metrics_via_file(container_name):
    """Tente de récupérer les métriques via les fichiers JSON."""
    command = '''
import json
import os
try:
    # Essayer plusieurs chemins possibles
    paths = [
        "/tmp/celery_metrics/celery_metrics_latest.json",
        "/app/backend_worker/tmp/celery_metrics/celery_metrics_latest.json",
        "/tmp/celery_metrics.json"
    ]
    
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            print(json.dumps(data))
            break
    else:
        # Fichier non trouvé, essayer Redis
        import redis
        try:
            r = redis.from_url("redis://redis:6379/0")
            data = r.get("celery_metrics")
            if data:
                print(data.decode())
            else:
                print("{}")
        except:
            print("{}")
except Exception as e:
    print("{}")
'''
    
    return run_in_container(container_name, command, timeout=30)

def get_worker_metrics_via_import(container_name):
    """Fallback : tente d'importer les métriques directement."""
    command = '''
import json
import sys
try:
    sys.path.append("/app")
    sys.path.append("/app/backend_worker")
    from backend_worker.utils.celery_monitor import CELERY_SIZE_METRICS
    result = {
        "args_max_size": CELERY_SIZE_METRICS.get("args_max_size", 0),
        "kwargs_max_size": CELERY_SIZE_METRICS.get("kwargs_max_size", 0),
        "args_avg_size": CELERY_SIZE_METRICS.get("args_avg_size", 0),
        "kwargs_avg_size": CELERY_SIZE_METRICS.get("kwargs_avg_size", 0),
        "total_measurements": CELERY_SIZE_METRICS.get("total_measurements", 0),
        "truncated_count": CELERY_SIZE_METRICS.get("truncated_count", 0),
        "max_task_name": CELERY_SIZE_METRICS.get("max_task_name", ""),
        "recommended_max": CELERY_SIZE_METRICS.get("recommended_max", 0),
        "last_updated": CELERY_SIZE_METRICS.get("last_updated", "Inconnu")
    }
    print(json.dumps(result, default=str))
except Exception as e:
    print("{}")
'''
    
    return run_in_container(container_name, command, timeout=30)

def get_worker_metrics(container_name):
    """Récupère les métriques depuis un worker avec fallbacks."""
    print(f"📊 Analyse de {container_name}...")
    
    # Essayer d'abord via les fichiers
    result = get_worker_metrics_via_file(container_name)
    
    # Si échec, essayer via import
    if not result:
        print(f"🔄 {container_name} - Tentative fallback...")
        result = get_worker_metrics_via_import(container_name)
    
    if result:
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            print(f"❌ {container_name} - Erreur parsing JSON: {e}")
            return None
    
    return None

def aggregate_metrics(metrics_list):
    """Agrège les métriques de tous les workers."""
    if not metrics_list:
        return None
    
    # Trouver les métriques avec le plus de mesures
    best_metrics = max(metrics_list, key=lambda x: x.get('total_measurements', 0))
    
    # Calculer les maxima agrégés
    args_max = max([m.get('args_max_size', 0) for m in metrics_list])
    kwargs_max = max([m.get('kwargs_max_size', 0) for m in metrics_list])
    total_measurements = sum([m.get('total_measurements', 0) for m in metrics_list])
    truncated_count = sum([m.get('truncated_count', 0) for m in metrics_list])
    
    # Trouver la tâche la plus volumineuse
    max_task_name = ""
    if args_max > kwargs_max:
        max_task_name = best_metrics.get('max_task_name', '')
    else:
        max_task_name = best_metrics.get('max_task_name', '')
    
    # Calculer la recommandation (max + 20% de marge)
    recommended_max = int(max(args_max, kwargs_max) * 1.2)
    
    return {
        'args_max_size': args_max,
        'kwargs_max_size': kwargs_max,
        'total_measurements': total_measurements,
        'truncated_count': truncated_count,
        'max_task_name': max_task_name,
        'recommended_max': recommended_max,
        'args_avg_size': best_metrics.get('args_avg_size', 0),
        'kwargs_avg_size': best_metrics.get('kwargs_avg_size', 0),
        'last_updated': best_metrics.get('last_updated', datetime.now().isoformat()),
        'workers_count': len(metrics_list)
    }

def display_metrics(metrics):
    """Affiche les métriques formatées."""
    if metrics is None:
        print("📊 Aucune métrique Celery disponible")
        print("💡 Les workers Celery doivent tourner et avoir traité des tâches")
        print("💡 Attendez quelques minutes puis relancer le script")
        return
    
    print("\n=== 📊 MÉTRIQUES CELERY MONITOR (LOCAL) ===")
    print(f"📦 Conteneurs analysés: {metrics.get('workers_count', 1)}")
    print(f"🕐 Dernière mise à jour: {metrics.get('last_updated', 'Inconnue')}")
    print(f"📈 Tâches analysées: {metrics['total_measurements']:,}")
    
    print("\n📏 TAILLE DES ARGUMENTS:")
    print(f"   Args max: {metrics['args_max_size']:,} caractères")
    print(f"   Kwargs max: {metrics['kwargs_max_size']:,} caractères")
    print(f"   Args moyen: {metrics['args_avg_size']:.0f} caractères")
    print(f"   Kwargs moyen: {metrics['kwargs_avg_size']:.0f} caractères")
    
    print("\n⚠️  PROBLÈMES:")
    print(f"   Tâches tronquées: {metrics['truncated_count']:,}")
    print(f"   Tâche la plus volumineuse: {metrics['max_task_name']}")
    
    print("\n🎯 RECOMMANDATIONS:")
    max_size = max(metrics['args_max_size'], metrics['kwargs_max_size'])
    recommended = metrics['recommended_max']
    
    print(f"   Taille max détectée: {max_size:,} caractères ({max_size/1024:.1f}KB)")
    print(f"   Limite recommandée: {recommended:,} caractères ({recommended/1024:.1f}KB)")
    
    # Recommandations de configuration
    if recommended <= 100 * 1024:
        config_value = 131072
        print(f"   🔧 Configuration suggérée: {config_value:,} (128KB)")
    elif recommended <= 500 * 1024:
        config_value = 524288
        print(f"   🔧 Configuration suggérée: {config_value:,} (512KB)")
    elif recommended <= 1024 * 1024:
        config_value = 1048576
        print(f"   🔧 Configuration suggérée: {config_value:,} (1MB)")
    else:
        config_value = 2097152
        print(f"   🔧 Configuration suggérée: {config_value:,} (2MB)")
    
    if config_value:
        print("\n💻 Pour appliquer dans celery_app.py:")
        print(f"   celery.amqp.argsrepr_maxsize = {config_value}")
        print(f"   celery.amqp.kwargsrepr_maxsize = {config_value}")

def list_running_workers():
    """Liste tous les conteneurs Celery en cours d'exécution avec plusieurs méthodes."""
    workers = []
    
    try:
        print("🔍 Recherche des conteneurs Celery...")
        
        # Méthode 1: Recherche exhaustive par mots-clés dans les noms
        result = subprocess.run([
            'docker', 'ps', '--format', '{{.Names}}'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            all_containers = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
            print(f"   📋 Tous les conteneurs actifs: {len(all_containers)}")
            
            # Filtre large pour tous les types de workers Celery
            
            # Détection plus large - tout conteneur avec soniquebay- est un worker potentiel
            potential_workers = []
            for container in all_containers:
                # Stratégie : si c'est un conteneur soniquebay ET qu'il contient un mot-clé de traitement
                is_soniquebay = container.startswith('soniquebay-')
                has_worker_keyword = any(keyword in container.lower() for keyword in
                                       ['extract', 'insert', 'batch', 'scan', 'vector', 'deferred', 'celery', 'beat'])
                
                # Ou si c'est juste un conteneur soniquebay (pour les noms non conventionnels)
                if is_soniquebay and (has_worker_keyword or 'worker' in container.lower()):
                    potential_workers.append(container)
                elif container.startswith('soniquebay-') and len(container) > 15:  # noms longs = workers
                    potential_workers.append(container)
            
            workers.extend(potential_workers)
            print(f"   ✓ Détectés par filtrage intelligent: {len(potential_workers)} conteneurs")
            for worker in potential_workers:
                print(f"      • {worker}")
        
        # Méthode 2: Filtres spécifiques pour les conteneurs manqués
        missed_keywords = ['celery-', 'soniquebay-celery']
        for filter_name in missed_keywords:
            result = subprocess.run([
                'docker', 'ps', '--filter', f'name={filter_name}',
                '--format', '{{.Names}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                found = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
                for worker_name in found:
                    if worker_name not in workers:
                        workers.append(worker_name)
                        print(f"   ✓ Ajouté via filtre '{filter_name}': {worker_name}")
        
        # Méthode 3: Recherche par image backend_worker (pour être sûr)
        result = subprocess.run([
            'docker', 'ps', '--filter', 'ancestor=backend_worker',
            '--format', '{{.Names}}'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            found = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
            for worker_name in found:
                if worker_name not in workers:
                    workers.append(worker_name)
                    print(f"   ✓ Ajouté via image backend_worker: {worker_name}")
        
        # Dédupliquer et trier
        workers = list(set(workers))
        workers.sort()  # Tri pour une meilleure lisibilité
        print(f"\n📊 Total de conteneurs Celery détectés: {len(workers)}")
        
        if workers:
            print("   🏷️  Conteneurs identifiés:")
            for i, worker in enumerate(workers, 1):
                print(f"      {i:2d}. {worker}")
        else:
            print("   ⚠️  Aucun worker Celery détecté")
        
        return workers
        
    except Exception as e:
        print(f"❌ Erreur récupération liste workers: {e}")
        return []

def test_container_connectivity(container_name):
    """Teste la connectivité d'un conteneur avec une commande simple."""
    try:
        result = subprocess.run([
            'docker', 'exec', container_name, 'python3', '-c', 'print("OK")'
        ], capture_output=True, text=True, timeout=5)
        
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
        print(f"❌ Erreur test connectivité {container_name}: {e}")
        return False

def main():
    print("🔍 Vérification des métriques Celery depuis la machine locale")
    print("=" * 60)
    
    # Liste des workers Celery
    workers = list_running_workers()
    
    if not workers:
        print("❌ Aucun conteneur Celery détecté")
        print("💡 Vérifiez que docker-compose est en cours d'exécution")
        print("💡 Commandes utiles:")
        print("   docker-compose ps")
        print("   docker-compose up -d")
        return
    
    # Tester la connectivité
    print("\n🧪 Test de connectivité des conteneurs...")
    accessible_workers = []
    for worker in workers:
        if test_container_connectivity(worker):
            accessible_workers.append(worker)
            print(f"   ✅ {worker}")
        else:
            print(f"   ❌ {worker} (inaccessible)")
    
    if not accessible_workers:
        print("❌ Aucun conteneur accessible")
        print("💡 Vérifiez que les conteneurs sont démarrés et fonctionnels")
        return
    
    print(f"\n📦 Conteneurs accessibles: {len(accessible_workers)}")
    print("📊 Récupération des métriques...")
    
    # Récupérer les métriques de tous les workers
    all_metrics = []
    for worker in accessible_workers:
        metrics = get_worker_metrics(worker)
        if metrics:
            all_metrics.append(metrics)
    
    if not all_metrics:
        print("\n❌ Aucune métrique récupérée")
        print("💡 Causes possibles:")
        print("   • Les workers ne traitent pas encore de tâches")
        print("   • Les métriques ne sont pas encore sauvegardées")
        print("   • Les workers sont occupés par des tâches longues")
        print("💡 Attendez quelques minutes puis relancez le script")
        
        # Afficher l'état des conteneurs
        print("\n📋 État des conteneurs Celery:")
        for worker in accessible_workers:
            try:
                result = subprocess.run([
                    'docker', 'exec', worker, 'ps', 'aux'
                ], capture_output=True, text=True, timeout=5)
                if 'celery' in result.stdout:
                    print(f"   ✅ {worker}: Celery actif")
                else:
                    print(f"   ⚠️  {worker}: Celery non détecté")
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
                print(f"   ❌ {worker}: Impossible de vérifier - {e}")
        
        return
    
    # Agréger les métriques
    print(f"\n✅ Métriques récupérées de {len(all_metrics)} conteneur(s)")
    aggregated = aggregate_metrics(all_metrics)
    
    # Affichage
    display_metrics(aggregated)
    
    print("\n" + "=" * 60)
    print("✅ Analyse terminée")

if __name__ == "__main__":
    main()