
from celery import Celery
from celery.signals import worker_init, task_prerun, task_postrun, worker_shutdown

from backend_worker.utils.logging import logger
from backend_worker.utils.celery_monitor import measure_celery_task_size, update_size_metrics, log_task_size_report, get_size_summary, auto_configure_celery_limits
import os
import redis
import socket
import signal
from kombu import Queue

# === SIGNAL HANDLERS ===
def handle_sigterm(signum, frame):
    """Handle SIGTERM signal by cleaning up logging resources."""
    try:
        from backend_worker.utils.logging import cleanup_logging
        cleanup_logging()
    except Exception as e:
        logger.error(f"Error during logging cleanup on SIGTERM: {e}")

# Register the signal handler for SIGTERM
signal.signal(signal.SIGTERM, handle_sigterm)

# === DIAGNOSTIC REDIS ===
def diagnostic_redis():
    """Diagnostique les problèmes de connexion Redis avec validation complète de l'URL"""
    logger.info("[REDIS DIAGNOSTIC] Démarrage du diagnostic de connexion Redis...")

    try:
        # Obtenir et normaliser l'URL Redis
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        logger.info(f"[REDIS DIAGNOSTIC] URL Redis brute: {redis_url}")

        # Corriger les URL malformées
        if not redis_url.startswith('redis://'):
            redis_url = 'redis://' + redis_url
            logger.warning(f"[REDIS DIAGNOSTIC] URL Redis corrigée: {redis_url}")
        
        # Vérifier et corriger les doubles "redis://"
        if 'redis://redis://' in redis_url:
            redis_url = redis_url.replace('redis://redis://', 'redis://', 1)
            logger.warning(f"[REDIS DIAGNOSTIC] Double \"redis://\" corrigée: {redis_url}")

        # Extraire l'hôte pour test DNS
        try:
            # Utiliser urllib.parse pour un parsing plus robuste
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            redis_host = parsed.hostname
            redis_port = parsed.port or 6379
            logger.info(f"[REDIS DIAGNOSTIC] Hôte Redis: {redis_host}:{redis_port}")

            # Test de résolution DNS avec timeout
            try:
                ip_address = socket.gethostbyname(redis_host)
                logger.info(f"[REDIS DIAGNOSTIC] Résolution DNS réussie: {redis_host} -> {ip_address}")
            except socket.gaierror as e:
                logger.error(f"[REDIS DIAGNOSTIC] Échec résolution DNS pour {redis_host}: {e}")
                return False

            # Test de connexion Redis avec timeout
            try:
                client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                client.ping()
                logger.info("[REDIS DIAGNOSTIC] Connexion Redis réussie!")
                return True
            except redis.ConnectionError as e:
                logger.error(f"[REDIS DIAGNOSTIC] Erreur de connexion Redis: {e}")
                return False

        except Exception as url_parse_error:
            logger.error(f"[REDIS DIAGNOSTIC] Erreur de parsing URL Redis: {url_parse_error}")
            return False

    except Exception as e:
        logger.error(f"[REDIS DIAGNOSTIC] Erreur inattendue: {e}")
        return False

# Communique via Redis - Configuration haute performance
celery = Celery(
    'soniquebay',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    include=[
        # Tâches Celery centralisées
        'backend_worker.celery_tasks',

        # Workers avec tâches Celery définies
        'backend_worker.workers.vectorization.monitoring_worker',
        'backend_worker.workers.deferred.deferred_enrichment_worker',

        # Nouvelle pipeline de scan
        'backend_worker.workers.metadata.extract_metadata_worker',
        'backend_worker.workers.batch.process_entities_worker',
        'backend_worker.workers.insert.insert_batch_worker',

        # Artist GMM workers
        'backend_worker.workers.artist_gmm.artist_gmm_worker',

        # Last.fm workers
        'backend_worker.workers.lastfm.lastfm_worker',

        # Vectorization workers
        'backend_worker.workers.vectorization.track_vectorization_worker',

        # Tâches de covers (NOUVEAU - requis pour process_artist_images et process_album_covers)
        'backend_worker.tasks.covers_tasks',

        # Tâches d'analyse audio avec Librosa (NOUVEAU)
        'backend_worker.tasks.audio_analysis_tasks',

        # Legacy pour compatibilité (à supprimer progressivement)
        'backend_worker.tasks.main_tasks',

        # Tâches de maintenance
        'backend_worker.tasks.maintenance_tasks',
    ]
)

# Log pour diagnostiquer l'URL du broker au démarrage
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
logger.info(f"[CELERY INIT] Broker URL configurée: {broker_url}")
if broker_url.startswith('redis://redis://'):
    logger.warning(f"[CELERY INIT] URL Broker malformée détectée: {broker_url}. Cela pourrait causer des problèmes d'inspection.")
celery.amqp.argsrepr_maxsize = 1048576  # 1MB - Taille maximale des arguments pour le logging
celery.amqp.kwargsrepr_maxsize = 1048576  # 1MB - Taille maximale des arguments pour le logging

# Configuration pour le monitoring et les événements
celery.amqp.task_send_sent_event = True
celery.amqp.task_reject_on_worker_lost = True

# Configuration pour les événements Flower/Monitoring
celery.events.queue_capacity = 10000  # Capacité queue d'événements augmentée
# === CONFIGURATION UNIFIÉE POUR ÉVITER LES ERREURS KOMBU ===
# Appliquer la configuration unifiée pour éviter ValueError dans Kombu
from backend_worker.celery_config_source import get_unified_celery_config
celery.conf.update(get_unified_celery_config())

# === CONFIGURATION SPÉCIFIQUE AU WORKER (EN PLUS DE LA CONFIGURATION UNIFIÉE) ===
# Ces paramètres sont spécifiques au worker et ne doivent pas être dans la config unifiée
celery.conf.update(
    # === TIMEOUTS OPTIMISÉS POUR RASPBERRY PI ===
    task_time_limit=7200,  # 2h pour tâches longues (audio processing)
    task_soft_time_limit=6900,  # 1h55 avant interruption
    task_default_retry_delay=10,  # Démarrage rapide
    task_max_retries=3,  # Plus de tentatives avec backoff exponentiel

    # === CONTRÔLE DE FLUX ===
    worker_prefetch_multiplier=1,  # Contrôlé dynamiquement par queue
    worker_disable_rate_limits=False,
    worker_concurrency=2,           # Limité pour Raspberry Pi

    # === CONNEXIONS REDIS OPTIMISÉES ===
    redis_max_connections=50,              # ✅ CORRIGÉ: Réduit pour éviter surcharge
    broker_pool_limit=10,                  # ✅ CORRIGÉ: Pool plus petit pour stabilité
    worker_max_memory_per_child=524288000, # ✅ CRITIQUE: 500MB par worker (évite OOM)
    worker_max_tasks_per_child=500,        # ✅ CORRIGÉ: Restart plus fréquent (500 vs 1000)
    result_backend_transport_options={
        'socket_timeout': 30,              # ✅ CORRIGÉ: Timeout plus long pour RPi4
        'socket_connect_timeout': 20,      # ✅ CORRIGÉ: Connexion plus tolérante
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {},
        'health_check_interval': 30,       # ✅ CORRIGÉ: Health check plus espacé
        'socket_read_size': 32768,         # ✅ CORRIGÉ: Taille réduite pour RPi4
        'socket_write_size': 32768,        # ✅ CORRIGÉ: Taille réduite pour RPi4
    },
    
    # === COMPRESSION POUR GROS MESSAGES ===
    task_compression='gzip',               # Compression automatique
    result_compression='gzip',
    
    # === FORCER LE WORKER À ÉCOUTER TOUTES LES QUEUES ===
    # Définir explicitement les queues que le worker doit consommer
    worker_queues=[
        'scan', 'extract', 'batch', 'insert', 'covers',
        'deferred_vectors', 'deferred_covers', 'deferred_enrichment',
        'vectorization_monitoring', 'deferred', 'celery', 'maintenance',
        'audio_analysis'  # NOUVEAU: Analyse audio avec Librosa
    ],
)

# Validation des timeouts
logger.info(f"[Celery Config] Timeouts configurés - task_time_limit: {celery.conf.task_time_limit}, task_soft_time_limit: {celery.conf.task_soft_time_limit}")



@worker_init.connect
def configure_worker(sender=None, **kwargs):
    """Configure le worker unifié avec autoscale au démarrage."""
    worker_name = sender.hostname

    # Diagnostic Redis au démarrage
    logger.info(f"[WORKER INIT] Démarrage du worker unifié {worker_name} avec autoscale")
    redis_ok = diagnostic_redis()
    if not redis_ok:
        logger.error(f"[WORKER INIT] Problème de connexion Redis détecté pour {worker_name}")

    # === PUBLICATION DE LA CONFIGURATION CELERY DANS REDIS ===
    try:
        from backend_worker.utils.celery_config_publisher import publish_celery_config_to_redis
        logger.info(f"[WORKER INIT] Publication de la configuration Celery dans Redis")
        publish_celery_config_to_redis()
        logger.info(f"[WORKER INIT] Configuration Celery publiée avec succès")
    except Exception as e:
        logger.error(f"[WORKER INIT] Erreur lors de la publication de la configuration: {str(e)}")
        # Ne pas bloquer le démarrage du worker si la publication échoue

    # Configuration simplifiée des queues (utilisant la config unifiée)
    all_queues = ['scan', 'extract', 'batch', 'insert', 'covers', 'deferred_vectors', 
                  'deferred_covers', 'deferred_enrichment', 'vectorization_monitoring', 
                  'deferred', 'celery', 'maintenance', 'audio_analysis']
    logger.info(f"[WORKER] {worker_name} configuré pour écouter les queues: {all_queues}")

    # Configurer les workers pour consommer les queues par priorité
    sender.app.conf.worker_prefetch_multiplier = 1
    sender.app.conf.worker_concurrency = 2  # Limité pour Raspberry Pi
    sender.app.conf.task_acks_late = True

    logger.info(f"[WORKER] {worker_name} consommateur ajouté pour toutes les queues avec configuration unifiée")


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    """Log avant exécution de tâche pour diagnostiquer les blocages."""
    try:
        worker_name = getattr(sender, 'hostname', 'unknown')
        task_name = getattr(task, 'name', 'unknown')
        task_queue = getattr(task, 'queue', 'unknown')

        # === MONITORING TAILLE DES ARGUMENTS ===
        size_metrics = measure_celery_task_size(task, task_id)
        update_size_metrics(size_metrics)

        # Affichage du rapport de taille seulement si supérieur à 1KB pour éviter le spam
        if size_metrics['args_size'] > 1024 or size_metrics['kwargs_size'] > 1024:
            log_task_size_report(size_metrics)

        # Accès sécurisé à task.args avec fallback
        args_count = 0
        if hasattr(task, 'args') and task.args is not None:
            try:
                args_count = len(task.args)
            except (TypeError, AttributeError):
                args_count = 0

        # Accès sécurisé à task.request.args si args n'est pas disponible
        if args_count == 0 and hasattr(task, 'request') and hasattr(task.request, 'args'):
            try:
                args_count = len(task.request.args)
            except (TypeError, AttributeError):
                pass

        # === DIAGNOSTIC SPÉCIFIQUE POUR monitor_tag_changes ===
        if task_name == 'monitor_tag_changes':
            logger.info(f"[MONITOR_TAG_CHANGES DIAG] Tâche démarrée avec queue: {task_queue}")
            logger.info(f"[MONITOR_TAG_CHANGES DIAG] Worker: {worker_name}")
            logger.info(f"[MONITOR_TAG_CHANGES DIAG] Args count: {args_count}")

            # Log des arguments détaillés pour le diagnostic
            if hasattr(task, 'args') and task.args:
                logger.info(f"[MONITOR_TAG_CHANGES DIAG] Args: {task.args}")
            if hasattr(task, 'kwargs') and task.kwargs:
                logger.info(f"[MONITOR_TAG_CHANGES DIAG] Kwargs: {task.kwargs}")

            # Vérification de la configuration de routage
            from backend_worker.celery_app import task_routes
            expected_queue = task_routes.get('monitor_tag_changes', {}).get('queue', 'non-configurée')
            logger.info(f"[MONITOR_TAG_CHANGES DIAG] Queue attendue: {expected_queue}")
            logger.info(f"[MONITOR_TAG_CHANGES DIAG] Queue actuelle: {task_queue}")
            logger.info(f"[MONITOR_TAG_CHANGES DIAG] Correspondance: {'OK' if task_queue == expected_queue else 'ERREUR'}")

        # === DIAGNOSTIC PIDBOX ET KOMBU (VERSION OPTIMISÉE) ===
        # Log des informations de routage disponibles uniquement si elles existent
        if hasattr(task, 'request'):
            if hasattr(task.request, 'routing_key'):
                logger.info(f"[PIDBOX DIAG] Routing key: {task.request.routing_key}")
            if hasattr(task.request, 'exchange'):
                logger.info(f"[PIDBOX DIAG] Exchange: {task.request.exchange}")

        # Log des informations de base fiables (sans messages "non-disponible")
        logger.info(f"[PIDBOX DIAG] Task name: {task_name}")
        logger.info(f"[PIDBOX DIAG] Task ID: {task_id}")
        logger.info(f"[PIDBOX DIAG] Task queue: {task_queue}")

        # Informations système fiables (remplace les messages "unknown worker")
        import os
        import socket
        current_hostname = socket.gethostname()
        logger.info(f"[PIDBOX DIAG] System hostname: {current_hostname}")
        logger.info(f"[PIDBOX DIAG] Environment: {os.getenv('ENVIRONMENT', 'development')}")
        logger.info(f"[PIDBOX DIAG] Worker process: {os.getpid()}")

        logger.info(f"[TASK PRERUN] Task {task_name} (ID: {task_id}) démarrage sur worker {worker_name}")
        logger.info(f"[TASK PRERUN] Queue: {task_queue} | Args: {args_count} éléments")
    except Exception as e:
        logger.warning(f"[TASK PRERUN] Erreur lors du logging de la tâche {task_id}: {str(e)}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
    """Log après exécution de tâche pour diagnostiquer les blocages."""
    try:
        logger.info(f"[TASK POSTRUN] Task {task.name} (ID: {task_id}) terminée - État: {state}")
        if state == 'FAILURE':
            logger.error(f"[TASK POSTRUN] Échec de la tâche {task.name} - Exception: {retval}")
        elif state == 'SUCCESS':
            logger.info(f"[TASK POSTRUN] Succès de la tâche {task.name}")
    except Exception as e:
        logger.error(f"[TASK POSTRUN] Erreur dans le handler postrun: {e}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Log lors de l'arrêt du worker pour diagnostiquer les crashes."""
    worker_name = sender.hostname
    
    # === RAPPORT FINAL DE MONITORING ===
    summary = get_size_summary()
    logger.info(f"[WORKER SHUTDOWN] Rapport final monitoring worker {worker_name}:")
    for line in summary.strip().split('\n'):
        logger.info(f"[WORKER SHUTDOWN] {line}")
    
    # === RECOMMANDATIONS AUTOMATIQUES ===
    recommended_limit = auto_configure_celery_limits()
    if recommended_limit:
        logger.info(f"[WORKER SHUTDOWN] Limite recommandée: {recommended_limit:,} caractères")
        logger.info("[WORKER SHUTDOWN] Commande pour appliquer cette limite:")
        logger.info(f"[WORKER SHUTDOWN] celery.amqp.argsrepr_maxsize = {recommended_limit}")
        logger.info(f"[WORKER SHUTDOWN] celery.amqp.kwargsrepr_maxsize = {recommended_limit}")
    
    # === NETTOYAGE DES RESSOURCES DE LOGGING ===
    try:
        from backend_worker.utils.logging import cleanup_logging
        cleanup_logging()
        logger.info("[WORKER SHUTDOWN] Ressources de logging nettoyées avec succès")
    except Exception as e:
        logger.error(f"[WORKER SHUTDOWN] Erreur lors du nettoyage des ressources de logging: {e}")
    
    logger.warning(f"[WORKER SHUTDOWN] Worker {worker_name} s'arrête - Vérifier si c'est normal ou crash")
