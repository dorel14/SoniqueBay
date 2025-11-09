
from celery import Celery  # noqa: E402
from celery.signals import worker_init, task_prerun, task_postrun, worker_shutdown # noqa: E402

from backend_worker.utils.logging import logger # noqa: E402
from backend_worker.utils.celery_monitor import measure_celery_task_size, update_size_metrics, log_task_size_report, get_size_summary, auto_configure_celery_limits # noqa: E402
import os # noqa: E402
import redis # noqa: E402
import socket # noqa: E402


# === DIAGNOSTIC REDIS ===
def diagnostic_redis():
    """Diagnostique les problèmes de connexion Redis"""
    logger.info("[REDIS DIAGNOSTIC] Démarrage du diagnostic de connexion Redis...")

    try:
        # Test de résolution DNS
        redis_host = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0').replace('redis://', '').split(':')[0]
        logger.info(f"[REDIS DIAGNOSTIC] Hôte Redis: {redis_host}")

        try:
            ip_address = socket.gethostbyname(redis_host)
            logger.info(f"[REDIS DIAGNOSTIC] Résolution DNS réussie: {redis_host} -> {ip_address}")
        except socket.gaierror as e:
            logger.error(f"[REDIS DIAGNOSTIC] Échec résolution DNS: {e}")
            return False

        # Test de connexion Redis
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        logger.info(f"[REDIS DIAGNOSTIC] Test de connexion à: {redis_url}")

        # Vérifier si l'URL a une double "redis://"
        if redis_url.startswith('redis://redis://'):
            logger.error(f"[REDIS DIAGNOSTIC] URL Redis malformée détectée: {redis_url}. Correction en cours.")
            redis_url = redis_url.replace('redis://redis://', 'redis://', 1)
            logger.info(f"[REDIS DIAGNOSTIC] URL corrigée: {redis_url}")

        client = redis.from_url(redis_url)
        client.ping()
        logger.info("[REDIS DIAGNOSTIC] Connexion Redis réussie!")
        return True

    except redis.ConnectionError as e:
        logger.error(f"[REDIS DIAGNOSTIC] Erreur de connexion Redis: {e}")
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
        
        # Legacy pour compatibilité (à supprimer progressivement)
        'backend_worker.tasks.main_tasks',
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
# === CONFIGURATION OPTIMISÉE HAUTE PERFORMANCE ===
celery.conf.update(
    # === OPTIMISATIONS GÉNÉRALES ===
    task_acks_late=True,                    # Fiabilité maximale
    task_reject_on_worker_lost=True,        # Gestion des workers perdus
    task_ignore_result=False,               # Nécessaire pour monitoring

    # === ÉVÉNEMENTS CELERY (REQUIS POUR FLOWER INSPECTION) ===
    worker_send_task_events=True,           # Activer envoi événements workers
    task_send_sent_event=True,              # Activer envoi événements tâches
    task_track_started=True,                # Tracking des tâches démarrées

    # === SÉRIALISATION OPTIMISÉE ===
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_accept_content=['json'],

    # === TIMEOUTS OPTIMISÉS POUR RASPBERRY PI ===
    task_time_limit=7200,  # 2h pour tâches longues (audio processing)
    task_soft_time_limit=6900,  # 1h55 avant interruption
    worker_heartbeat=300,  # ✅ CRITIQUE: Heartbeat étendu pour RPi4 (5 min au lieu de 60s)
    worker_clock_sync_interval=300,  # ✅ CRITIQUE: Sync étendu pour éviter timeouts
    task_default_retry_delay=10,  # Démarrage rapide
    task_max_retries=3,  # Plus de tentatives avec backoff exponentiel

    # === CONTRÔLE DE FLUX ===
    worker_prefetch_multiplier=1,  # Contrôlé dynamiquement par queue
    worker_disable_rate_limits=False,

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

    # === ZONE TEMPORELLE ===
    timezone=os.getenv('TZ', default='UTC'),
    enable_utc=True,
    
    
)

# Validation des timeouts
logger.info(f"[Celery Config] Timeouts configurés - task_time_limit: {celery.conf.task_time_limit}, task_soft_time_limit: {celery.conf.task_soft_time_limit}")

# === DÉFINITION DES QUEUES SPÉCIALISÉES ===
task_queues = {
    # Queue DISCOVERY (I/O intensive)
    'scan': {
        'exchange': 'scan',
        'routing_key': 'scan',
        'delivery_mode': 2,  # Persistant
    },

    # Queue EXTRACTION (CPU intensive)
    'extract': {
        'exchange': 'extract',
        'routing_key': 'extract',
        'delivery_mode': 1,  # Non-persistant
    },

    # Queue BATCHING (Memory intensive)
    'batch': {
        'exchange': 'batch',
        'routing_key': 'batch',
        'delivery_mode': 1,
    },

    # Queue INSERTION (DB intensive)
    'insert': {
        'exchange': 'insert',
        'routing_key': 'insert',
        'delivery_mode': 2,  # Persistant pour fiabilité
    },

    # Queue COVERS (API/Réseau intensif - NOUVELLE!)
    'covers': {
        'exchange': 'covers',
        'routing_key': 'covers',
        'delivery_mode': 1,  # Non-persistant pour performance
    },

    # ✅ Queue VECTORS DIFFÉRÉS (CPU intensif - limitées pour éviter OOM)
    'deferred_vectors': {
        'exchange': 'deferred_vectors',
        'routing_key': 'deferred_vectors',
        'delivery_mode': 1,  # Non-persistant (calculs CPU)
    },

    # ✅ Queue COVERS DIFFÉRÉS (Réseau/API intensif - avec délais)
    'deferred_covers': {
        'exchange': 'deferred_covers',
        'routing_key': 'deferred_covers',
        'delivery_mode': 1,  # Non-persistant (APIs externes)
    },

    # ✅ Queue ENRICHMENT DIFFÉRÉS (I/O intensif)
    'deferred_enrichment': {
        'exchange': 'deferred_enrichment',
        'routing_key': 'deferred_enrichment',
        'delivery_mode': 1,  # Non-persistant (données temporaires)
    },

    # Queue MONITORING VECTORISATION (NOUVELLE!)
    'vectorization_monitoring': {
        'exchange': 'vectorization_monitoring',
        'routing_key': 'vectorization_monitoring',
        'delivery_mode': 1,  # Non-persistant pour monitoring léger
    },

    # Queue LEGACY pour compatibilité
    'deferred': {
        'exchange': 'deferred',
        'routing_key': 'deferred',
        'delivery_mode': 1,
    },

    # Queue par défaut (compatibilité)
    'celery': {'exchange': 'celery', 'routing_key': 'celery'},
}

# === ROUTAGE OPTIMISÉ - NOUVELLE ARCHITECTURE ===
task_routes = {
    # === TÂCHES CELERY_CENTRALES ===
    'scan.discovery': {'queue': 'scan'},
    'metadata.extract_batch': {'queue': 'extract'},
    'batch.process_entities': {'queue': 'batch'},
    'insert.direct_batch': {'queue': 'insert'},
    'vectorization.calculate': {'queue': 'vectorization'},
    'covers.extract_embedded': {'queue': 'deferred'},
    'metadata.enrich_batch': {'queue': 'deferred'},
    
    # === WORKERS DEFERRED (TÂCHES RÉELLEMENT DÉFINIES) ===
    'worker_deferred_enrichment.*': {'queue': 'deferred'},
    
    # === MONITORING VECTORISATION ===
    'monitor_tag_changes': {'queue': 'vectorization_monitoring'},
    'trigger_vectorizer_retrain': {'queue': 'vectorization_monitoring'},
    'check_model_health': {'queue': 'vectorization_monitoring'},
}

# === CONFIGURATION PAR QUEUE ===
PREFETCH_MULTIPLIERS = {
    # Tâches haute priorité (scan)
    'scan': 1,         # ✅ CRITIQUE: 1 seul - évite surcharge mémoire I/O

    # Tâches CPU intensives
    'extract': 1,      # ✅ CRITIQUE: 1 seul - évite surcharge CPU
    'vectorization': 1,  # ✅ CRITIQUE: 1 seul - éviter surcharge CPU

    # Tâches I/O et mémoire
    'batch': 1,        # ✅ CRITIQUE: 1 seul - Memory bound critique
    'insert': 1,       # ✅ CRITIQUE: 1 seul - évite surcharge DB

    # Tâches deferred (legacy + enrichissement)
    'deferred': 1,     # ✅ CRITIQUE: 1 seul (legacy + enrichissement)

    # Tâches léger monitoring
    'vectorization_monitoring': 1,  # ✅ OPTIMISÉ: 1 (monitoring léger)
}

CONCURRENCY_SETTINGS = {
    # Tâches haute priorité (scan)
    'scan': 1,         # ✅ CRITIQUE: 1 worker max - priorité absolue

    # Tâches CPU intensives
    'extract': 1,      # ✅ CRITIQUE: 1 worker max (CPU bound)
    'vectorization': 1,  # ✅ CRITIQUE: 1 worker max (évite OOM RPi4)

    # Tâches I/O et mémoire
    'batch': 1,        # ✅ CRITIQUE: 1 worker max (Memory bound)
    'insert': 1,       # ✅ CRITIQUE: 1 worker max (DB connection limit)

    # Tâches deferred
    'deferred': 1,     # ✅ CRITIQUE: 1 worker max (legacy + enrichissement)

    # Tâches monitoring léger
    'vectorization_monitoring': 1,  # ✅ OPTIMISÉ: 1 worker max (léger)
}

@worker_init.connect
def configure_worker(sender=None, **kwargs):
    """Configure le worker au démarrage."""
    worker_name = sender.hostname
    app = sender.app

    # Diagnostic Redis au démarrage
    logger.info(f"[WORKER INIT] Démarrage du worker {worker_name}")
    redis_ok = diagnostic_redis()
    if not redis_ok:
        logger.error(f"[WORKER INIT] Problème de connexion Redis détecté pour {worker_name}")

    # Configuration par queue
    queue_for_worker = None
    for queue_name in PREFETCH_MULTIPLIERS:
        if queue_name in worker_name:
            queue_for_worker = queue_name
            break

    if queue_for_worker:
        app.conf.worker_prefetch_multiplier = PREFETCH_MULTIPLIERS[queue_for_worker]
        app.conf.worker_concurrency = CONCURRENCY_SETTINGS[queue_for_worker]

        logger.info(f"[WORKER] {worker_name} → Queue={queue_for_worker} | "
                   f"Prefetch={PREFETCH_MULTIPLIERS[queue_for_worker]} | "
                   f"Concurrency={CONCURRENCY_SETTINGS[queue_for_worker]}")


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
    
    logger.warning(f"[WORKER SHUTDOWN] Worker {worker_name} s'arrête - Vérifier si c'est normal ou crash")

