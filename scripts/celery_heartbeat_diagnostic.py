#!/usr/bin/env python3
"""
Script de diagnostic spécialisé pour les "missed heartbeat" TaskIQ.
Identifie les causes potentielles et propose des solutions.
Usage: python scripts/celery_heartbeat_diagnostic.py
"""

import os
import sys
import redis
import socket
import subprocess
from datetime import datetime
from typing import Dict, Any

# Ajouter le backend_worker au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_worker'))

try:
    from backend_worker.taskiq_app import broker
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Assurez-vous que le backend_worker est accessible")
    sys.exit(1)

class TaskIQHeartbeatDiagnostic:
    """Diagnostic spécialisé pour les problèmes de heartbeat TaskIQ."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []
        
    def log_issue(self, message: str, severity: str = "ERROR"):
        """Log d'un problème trouvé."""
        if severity == "ERROR":
            self.issues.append(f"[ERROR] {message}")
        else:
            self.warnings.append(f"[WARN] {message}")
        
    def log_recommendation(self, message: str):
        """Log d'une recommandation."""
        self.recommendations.append(f"[RECOMMEND] {message}")
        
    def check_system_memory(self) -> Dict[str, Any]:
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
        
    def check_docker_status(self) -> Dict[str, Any]:
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
        
    def check_redis_connectivity(self) -> Dict[str, Any]:
        """Vérifie la connectivité Redis."""
        redis_url = os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')
         
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
        
    def check_processes(self) -> Dict[str, Any]:
        """Vérifie les processus TaskIQ actifs."""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            taskiq_processes = [line for line in result.stdout.split('\n') 
                              if 'taskiq' in line.lower() and 'grep' not in line]
             
            return {
                'total_processes': len(taskiq_processes),
                'processes': taskiq_processes
            }
        except Exception as e:
            self.log_issue(f"Erreur vérification processus: {e}")
            return {'error': str(e)}
        
    def generate_recommendations(self, mem_info: Dict[str, Any], redis_info: Dict[str, Any]):
        """Génère des recommandations basées sur l'analyse."""
        
        # Recommandations mémoire
        if mem_info.get('usage_percent', 0) > 80:
            self.log_recommendation("Mémoire système > 80% - Réduire la concurrency TaskIQ")
        
        if mem_info.get('is_rpi4_limited', False):
            self.log_recommendation("RPi4 détecté - Utiliser des limites mémoire appropriées pour TaskIQ workers")
        
        # Recommandations Redis
        if redis_info.get('status') != 'OK':
            self.log_recommendation("Vérifier que Redis est démarré: docker-compose up redis")
        
        # Recommandations générales
        self.log_recommendation("Surveiller avec: docker-compose logs -f taskiq-worker")
        self.log_recommendation("Restart workers si nécessaire: docker-compose restart taskiq-worker")
        
    def run_diagnostic(self) -> str:
        """Lance le diagnostic complet."""
        print("[INFO] DIAGNOSTIC TASKIQ HEARTBEAT - SONIQUEBAY")
        print("=" * 60)
        print(f"[TIME] Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Tests système
        print("[MEM] ANALYSE MÉMOIRE SYSTÈME")
        mem_info = self.check_system_memory()
        if 'error' not in mem_info:
            print(f"   Total memory: {mem_info['total_mb']:,} MB")
            print(f"   Available memory: {mem_info['available_mb']:,} MB")
            print(f"   Usage: {mem_info['usage_percent']:.1f}%")
            if mem_info['is_rpi4_limited']:
                print("   [RPI] Raspberry Pi 4 detected (8GB limit)")
        else:
            print(f"   [ERROR] {mem_info['error']}")
        print()
        
        # Test Docker
        print("[DOCK] DOCKER STATUS")
        docker_info = self.check_docker_status()
        if 'containers' in docker_info:
            if not docker_info['containers']:
                print("   [WARN] No active containers")
            else:
                for container in docker_info['containers']:
                    status_icon = "[OK]" if 'Up' in container['status'] else "[ERROR]"
                    print(f"   {status_icon} {container['name']}: {container['status']}")
        else:
            print(f"   [ERROR] {docker_info.get('error', 'Unknown error')}")
        print()
        
        # Test Redis
        print("[REDIS] REDIS CONNECTIVITY")
        redis_info = self.check_redis_connectivity()
        if redis_info.get('status') == 'OK':
            print(f"   [OK] Connection OK: {redis_info['host']} ({redis_info['ip']})")
        else:
            print(f"   [ERROR] {redis_info.get('error', 'Unknown error')}")
        print()
        
        # Processes
        print("[PROC] TASKIQ PROCESSES")
        proc_info = self.check_processes()
        if 'error' not in proc_info:
            print(f"   Total processes: {proc_info['total_processes']}")
        else:
            print(f"   [WARN] {proc_info['error']}")
        print()
        
        # Summary
        print("[SUMMARY] SUMMARY AND RECOMMENDATIONS")
        self.generate_recommendations(mem_info, redis_info)
        
        if self.issues:
            print("\n[ERROR] CRITICAL ISSUES:")
            for issue in self.issues:
                print(f"   {issue}")
        
        if self.warnings:
            print("\n[WARN] WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if self.recommendations:
            print("\n[INFO] RECOMMENDATIONS:")
            for rec in self.recommendations:
                print(f"   {rec}")
        
        # Health score
        critical_issues = len([i for i in self.issues if any(word in i.lower() 
                           for word in ['memory', 'redis', 'oom'])])
        
        if critical_issues == 0:
            print("\n[OK] SYSTEM HEALTHY - No critical issues detected")
            health_status = "EXCELLENT"
        elif critical_issues <= 2:
            print(f"\n[WARN] SYSTEM FAIR - {critical_issues} critical issue(s)")
            health_status = "MOYEN"
        else:
            print(f"\n[ERROR] SYSTEM DEGRADED - {critical_issues} critical issues")
            health_status = "CRITIQUE"
        
        return health_status

if __name__ == "__main__":
    diagnostic = TaskIQHeartbeatDiagnostic()
    health = diagnostic.run_diagnostic()
    
    print("\n" + "=" * 60)
    print(f"[HEALTH] SYSTEM HEALTH STATUS: {health}")
    print("=" * 60)
    
    # Exit code based on health status
    if health == "EXCELLENT":
        sys.exit(0)
    elif health == "MOYEN":
        sys.exit(1)
    else:
        sys.exit(2)