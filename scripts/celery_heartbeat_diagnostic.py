#!/usr/bin/env python3
"""
Script de diagnostic spécialisé pour les "missed heartbeat" Celery.
Identifie les causes potentielles et propose des solutions.
Usage: python scripts/celery_heartbeat_diagnostic.py
"""

import os
import sys
import redis
import socket
import subprocess
from datetime import datetime
from typing import Dict

# Ajouter le backend_worker au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_worker'))

try:
    from backend_worker.utils.celery_monitor import get_size_summary
    from backend_worker.celery_app import celery
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Assurez-vous que le backend_worker est accessible")
    sys.exit(1)

class CeleryHeartbeatDiagnostic:
    """Diagnostic spécialisé pour les problèmes de heartbeat Celery."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []
        
    def log_issue(self, message: str, severity: str = "ERROR"):
        """Log d'un problème trouvé."""
        if severity == "ERROR":
            self.issues.append(f"❌ {message}")
        else:
            self.warnings.append(f"⚠️  {message}")
    
    def log_recommendation(self, message: str):
        """Log d'une recommandation."""
        self.recommendations.append(f"💡 {message}")
    
    def check_system_memory(self) -> Dict[str, any]:
        """Vérifie la mémoire système disponible."""
        try:
            # Vérifier la mémoire disponible (Linux/macOS)
            if os.name == 'posix':
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    lines = meminfo.split('\n')
                    mem_total = int([line for line in lines if line.startswith('MemTotal:')][0].split()[1])
                    mem_available = int([line for line in lines if line.startswith('MemAvailable:')][0].split()[1])
                    
                    # Convertir en MB
                    mem_total_mb = mem_total // 1024
                    mem_available_mb = mem_available // 1024
                    usage_percent = ((mem_total - mem_available) / mem_total) * 100
                    
                    return {
                        'total_mb': mem_total_mb,
                        'available_mb': mem_available_mb,
                        'usage_percent': usage_percent,
                        'is_rpi4_limited': mem_total_mb <= 8192  # 8GB max pour RPi4
                    }
            else:
                return {'error': 'Système non POSIX'}
        except Exception as e:
            self.log_issue(f"Impossible de vérifier la mémoire système: {e}")
            return {'error': str(e)}
    
    def check_docker_status(self) -> Dict[str, any]:
        """Vérifie l'état des conteneurs Docker."""
        try:
            result = subprocess.run(['docker-compose', 'ps', '--format', 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                containers = []
                for line in lines:
                    if line:
                        parts = line.split('\t')
                        containers.append({
                            'name': parts[0] if len(parts) > 0 else 'unknown',
                            'status': parts[1] if len(parts) > 1 else 'unknown',
                            'ports': parts[2] if len(parts) > 2 else ''
                        })
                return {'containers': containers}
            else:
                self.log_issue(f"Erreur docker-compose: {result.stderr}")
                return {'error': result.stderr}
        except subprocess.TimeoutExpired:
            self.log_issue("Timeout lors de la vérification Docker")
            return {'error': 'Timeout'}
        except Exception as e:
            self.log_issue(f"Impossible de vérifier Docker: {e}")
            return {'error': str(e)}
    
    def check_redis_connectivity(self) -> Dict[str, any]:
        """Vérifie la connectivité Redis."""
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        
        # Nettoyer l'URL si nécessaire
        if redis_url.startswith('redis://redis://'):
            redis_url = redis_url.replace('redis://redis://', 'redis://', 1)
        
        try:
            # Test DNS
            redis_host = redis_url.replace('redis://', '').split(':')[0]
            ip = socket.gethostbyname(redis_host)
            
            # Test connexion Redis
            client = redis.from_url(redis_url)
            client.ping()
            
            return {
                'host': redis_host,
                'ip': ip,
                'url': redis_url,
                'status': 'OK'
            }
        except redis.ConnectionError as e:
            self.log_issue(f"Erreur de connexion Redis: {e}")
            return {'status': 'CONNECTION_ERROR', 'error': str(e)}
        except socket.gaierror as e:
            self.log_issue(f"Erreur DNS Redis: {e}")
            return {'status': 'DNS_ERROR', 'error': str(e)}
        except Exception as e:
            self.log_issue(f"Erreur Redis inattendue: {e}")
            return {'status': 'UNKNOWN_ERROR', 'error': str(e)}
    
    def analyze_celery_config(self) -> Dict[str, any]:
        """Analyse la configuration Celery."""
        issues = []
        warnings = []
        
        try:
            # Vérifier les timeouts heartbeat
            heartbeat = getattr(celery.conf, 'worker_heartbeat', None)
            if not heartbeat or heartbeat < 120:
                issues.append(f"Heartbeat trop court: {heartbeat}s (recommande: >=120s)")
            
            # Vérifier worker_max_memory_per_child
            memory_limit = getattr(celery.conf, 'worker_max_memory_per_child', None)
            if not memory_limit:
                warnings.append("Aucune limite mémoire configurée (risque OOM)")
            elif memory_limit > 1073741824:  # 1GB
                warnings.append(f"Limite mémoire élevée: {memory_limit//1024//1024}MB")
            
            # Vérifier worker_max_tasks_per_child
            task_limit = getattr(celery.conf, 'worker_max_tasks_per_child', None)
            if not task_limit or task_limit > 1000:
                warnings.append(f"Limite tâches par worker élevée: {task_limit}")
            
            # Vérifier les prefetch multipliers
            from backend_worker.celery_app import PREFETCH_MULTIPLIERS
            for queue, prefetch in PREFETCH_MULTIPLIERS.items():
                if prefetch > 1:
                    warnings.append(f"Prefetch élevé pour {queue}: {prefetch}")
            
            return {
                'heartbeat': heartbeat,
                'memory_limit_mb': memory_limit // 1024 // 1024 if memory_limit else None,
                'task_limit': task_limit,
                'prefetch_multipliers': PREFETCH_MULTIPLIERS,
                'issues': issues,
                'warnings': warnings
            }
        except Exception as e:
            self.log_issue(f"Erreur analyse configuration Celery: {e}")
            return {'error': str(e)}
    
    def check_processes(self) -> Dict[str, any]:
        """Vérifie les processus Celery actifs."""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            celery_processes = [line for line in result.stdout.split('\n') 
                              if 'celery' in line.lower() and 'grep' not in line]
            
            # Compter les ForkPoolWorker
            fork_workers = [line for line in celery_processes 
                          if 'ForkPoolWorker' in line]
            
            return {
                'total_processes': len(celery_processes),
                'fork_workers': len(fork_workers),
                'processes': celery_processes
            }
        except Exception as e:
            self.log_issue(f"Erreur vérification processus: {e}")
            return {'error': str(e)}
    
    def generate_recommendations(self, mem_info: Dict, redis_info: Dict, config_info: Dict):
        """Génère des recommandations basées sur l'analyse."""
        
        # Recommandations mémoire
        if mem_info.get('usage_percent', 0) > 80:
            self.log_recommendation("Mémoire système > 80% - Réduire la concurrency Celery")
        
        if mem_info.get('is_rpi4_limited', False):
            self.log_recommendation("RPi4 détecté - Utiliser worker_max_memory_per_child=500MB")
        
        # Recommandations Redis
        if redis_info.get('status') != 'OK':
            self.log_recommendation("Vérifier que Redis est démarré: docker-compose up redis")
        
        # Recommandations configuration
        if config_info.get('issues'):
            for issue in config_info['issues']:
                if 'Heartbeat' in issue:
                    self.log_recommendation("Augmenter worker_heartbeat à 300s pour RPi4")
        
        # Recommandations générales
        self.log_recommendation("Surveiller avec: docker-compose logs -f celery-scan-worker")
        self.log_recommendation("Restart workers si OOM: docker-compose restart celery-scan-worker")
    
    def run_diagnostic(self) -> str:
        """Lance le diagnostic complet."""
        print("🔍 DIAGNOSTIC CELERY HEARTBEAT - SONIQUEBAY")
        print("=" * 60)
        print(f"⏰ Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Tests système
        print("📊 ANALYSE MÉMOIRE SYSTÈME")
        mem_info = self.check_system_memory()
        if 'error' not in mem_info:
            print(f"   Mémoire totale: {mem_info['total_mb']:,} MB")
            print(f"   Mémoire disponible: {mem_info['available_mb']:,} MB")
            print(f"   Utilisation: {mem_info['usage_percent']:.1f}%")
            if mem_info['is_rpi4_limited']:
                print("   🔴 Raspberry Pi 4 détecté (limite 8GB)")
        else:
            print(f"   ❌ {mem_info['error']}")
        print()
        
        # Test Docker
        print("🐳 ÉTAT DOCKER")
        docker_info = self.check_docker_status()
        if 'containers' in docker_info:
            if not docker_info['containers']:
                print("   ⚠️  Aucun conteneur actif")
            else:
                for container in docker_info['containers']:
                    status_icon = "✅" if 'Up' in container['status'] else "❌"
                    print(f"   {status_icon} {container['name']}: {container['status']}")
        else:
            print(f"   ❌ {docker_info.get('error', 'Erreur inconnue')}")
        print()
        
        # Test Redis
        print("🔗 CONNECTIVITÉ REDIS")
        redis_info = self.check_redis_connectivity()
        if redis_info.get('status') == 'OK':
            print(f"   ✅ Connexion OK: {redis_info['host']} ({redis_info['ip']})")
        else:
            print(f"   ❌ {redis_info.get('error', 'Erreur inconnue')}")
        print()
        
        # Analyse configuration
        print("⚙️  CONFIGURATION CELERY")
        config_info = self.analyze_celery_config()
        if 'error' not in config_info:
            print(f"   Heartbeat: {config_info.get('heartbeat', 'Non défini')}s")
            memory_mb = config_info.get('memory_limit_mb')
            print(f"   Limite mémoire: {memory_mb if memory_mb else 'Non définie'} MB")
            print(f"   Limite tâches: {config_info.get('task_limit', 'Non définie')}")
            
            for issue in config_info.get('issues', []):
                print(f"   ❌ {issue}")
            for warning in config_info.get('warnings', []):
                print(f"   ⚠️  {warning}")
        else:
            print(f"   ❌ {config_info['error']}")
        print()
        
        # Métriques Celery
        print("📈 MÉTRIQUES CELERY")
        try:
            summary = get_size_summary()
            # Affichage simplifié
            lines = summary.split('\n')
            for line in lines:
                if 'Tâches analysées:' in line:
                    print(f"   📊 {line.strip()}")
                elif 'Taille max' in line:
                    print(f"   📊 {line.strip()}")
                elif 'Tâches tronquées:' in line:
                    print(f"   📊 {line.strip()}")
        except Exception as e:
            print(f"   ⚠️  Impossible de récupérer les métriques: {e}")
        print()
        
        # Processus
        print("🔄 PROCESSUS CELERY")
        proc_info = self.check_processes()
        if 'error' not in proc_info:
            print(f"   Total processus: {proc_info['total_processes']}")
            print(f"   ForkPoolWorkers: {proc_info['fork_workers']}")
        else:
            print(f"   ⚠️  {proc_info['error']}")
        print()
        
        # Synthèse
        print("🎯 SYNTHÈSE ET RECOMMANDATIONS")
        self.generate_recommendations(mem_info, redis_info, config_info)
        
        if self.issues:
            print("\n❌ PROBLÈMES CRITIQUES:")
            for issue in self.issues:
                print(f"   {issue}")
        
        if self.warnings:
            print("\n⚠️  AVERTISSEMENTS:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if self.recommendations:
            print("\n💡 RECOMMANDATIONS:")
            for rec in self.recommendations:
                print(f"   {rec}")
        
        # Score de santé
        critical_issues = len([i for i in self.issues if any(word in i.lower() 
                             for word in ['heartbeat', 'memory', 'redis', 'oom'])])
        
        if critical_issues == 0:
            print("\n✅ SYSTÈME SAIN - Pas de problèmes critiques détectés")
            health_status = "EXCELLENT"
        elif critical_issues <= 2:
            print(f"\n⚠️  SYSTÈME MOYEN - {critical_issues} problème(s) critique(s)")
            health_status = "MOYEN"
        else:
            print(f"\n🔴 SYSTÈME DÉGRADÉ - {critical_issues} problèmes critiques")
            health_status = "CRITIQUE"
        
        return health_status

if __name__ == "__main__":
    diagnostic = CeleryHeartbeatDiagnostic()
    health = diagnostic.run_diagnostic()
    
    print("\n" + "=" * 60)
    print(f"🏥 ÉTAT DE SANTÉ SYSTÈME: {health}")
    print("=" * 60)
    
    # Code de sortie basé sur l'état de santé
    if health == "EXCELLENT":
        sys.exit(0)
    elif health == "MOYEN":
        sys.exit(1)
    else:
        sys.exit(2)