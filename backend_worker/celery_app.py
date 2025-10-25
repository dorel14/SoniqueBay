
from celery import Celery  # noqa: E402
from celery.signals import worker_init, task_prerun # noqa: E402

from backend_worker.utils.logging import logger # noqa: E402
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
        # Tâches principales optimisées
        'backend_worker.background_tasks.tasks',
        'backend_worker.background_tasks.optimized_scan',  # Nouvelles tâches optimisées
        'backend_worker.background_tasks.optimized_extract',  # Extraction massive
        'backend_worker.background_tasks.optimized_batch',  # Batching intelligent
        'backend_worker.background_tasks.optimized_insert',  # Insertion directe

        # Workers existants (maintenus pour compatibilité)
        'backend_worker.background_tasks.worker_scan',
        'backend_worker.background_tasks.worker_extract',
        'backend_worker.background_tasks.worker_insert_bulk',
        'backend_worker.background_tasks.worker_cover',
        'backend_worker.background_tasks.worker_metadata',
        'backend_worker.background_tasks.worker_vector',

        # Workers différés
        'backend_worker.background_tasks.worker_deferred_enrichment',
        'backend_worker.background_tasks.worker_deferred_covers',
        'backend_worker.background_tasks.worker_deferred_vectors',
    ]
)

# Log pour diagnostiquer l'URL du broker au démarrage
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
logger.info(f"[CELERY INIT] Broker URL configurée: {broker_url}")
if broker_url.startswith('redis://redis://'):
    logger.warning(f"[CELERY INIT] URL Broker malformée détectée: {broker_url}. Cela pourrait causer des problèmes d'inspection.")

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

    # === TIMEOUTS ADAPTÉS (simplifiés pour éviter les erreurs de type) ===
    task_time_limit=7200,  # Timeout global par défaut : 2h
    task_soft_time_limit=6600,  # Soft timeout global : 110min

    # === CONTRÔLE DE FLUX ===
    worker_prefetch_multiplier=1,  # Contrôlé dynamiquement par queue
    worker_max_tasks_per_child=1000,       # Éviter fuites mémoire
    worker_disable_rate_limits=False,

    # === CONNEXIONS REDIS OPTIMISÉES ===
    redis_max_connections=200,             # Haute concurrence
    broker_pool_limit=50,                  # Pool plus grand
    result_backend_transport_options={
        'socket_timeout': 30,
        'socket_connect_timeout': 30,
        'retry_on_timeout': True,
    },

    # === COMPRESSION POUR GROS MESSAGES ===
    task_compression='gzip',               # Compression automatique
    result_compression='gzip',

    # === ZONE TEMPORELLE ===
    timezone='Europe/Paris',
    enable_utc=True,
)

# CORRECTION: Validation finale des timeouts pour éviter les dictionnaires problématiques
logger.debug(f"[Celery Config] task_time_limit configuré: {celery.conf.task_time_limit}")
logger.debug(f"[Celery Config] task_soft_time_limit configuré: {celery.conf.task_soft_time_limit}")

# Validation de sécurité pour éviter les dictionnaires dans les timeouts
# Vérifier si c'est un dictionnaire ou un nombre
if isinstance(celery.conf.task_time_limit, dict):
    for task_name, timeout_value in celery.conf.task_time_limit.items():
        if isinstance(timeout_value, dict):
            logger.error(f"[Celery Config] ERREUR: Timeout pour {task_name} est un dictionnaire: {timeout_value}")
            celery.conf.task_time_limit[task_name] = 3600  # Valeur par défaut
        elif not isinstance(timeout_value, (int, float)):
            logger.error(f"[Celery Config] ERREUR: Timeout pour {task_name} n'est pas un nombre: {timeout_value} (type: {type(timeout_value)})")
            celery.conf.task_time_limit[task_name] = 3600
else:
    # Si c'est un nombre global, c'est correct
    logger.info(f"[Celery Config] task_time_limit est un nombre global: {celery.conf.task_time_limit}")

if isinstance(celery.conf.task_soft_time_limit, dict):
    for task_name, timeout_value in celery.conf.task_soft_time_limit.items():
        if isinstance(timeout_value, dict):
            logger.error(f"[Celery Config] ERREUR: Soft timeout pour {task_name} est un dictionnaire: {timeout_value}")
            celery.conf.task_soft_time_limit[task_name] = 3300  # Valeur par défaut
        elif not isinstance(timeout_value, (int, float)):
            logger.error(f"[Celery Config] ERREUR: Soft timeout pour {task_name} n'est pas un nombre: {timeout_value} (type: {type(timeout_value)})")
            celery.conf.task_soft_time_limit[task_name] = 3300
else:
    # Si c'est un nombre global, c'est correct
    logger.info(f"[Celery Config] task_soft_time_limit est un nombre global: {celery.conf.task_soft_time_limit}")

# Log final pour confirmer
logger.info(f"[Celery Config] Timeouts finaux - task_time_limit: {celery.conf.task_time_limit}")
logger.info(f"[Celery Config] Timeouts finaux - task_soft_time_limit: {celery.conf.task_soft_time_limit}")

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

    # Queue DIFFÉRÉE (Background tasks)
    'deferred': {
        'exchange': 'deferred',
        'routing_key': 'deferred',
        'delivery_mode': 1,
    },

    # Queue par défaut (compatibilité)
    'celery': {'exchange': 'celery', 'routing_key': 'celery'},
}

# === ROUTAGE OPTIMISÉ ===
task_routes = {
    # Nouvelles tâches optimisées
    'scan_directory_parallel': {'queue': 'scan'},
    'scan_directory_chunk': {'queue': 'scan'},
    'extract_metadata_batch': {'queue': 'extract'},
    'batch_entities': {'queue': 'batch'},
    'insert_batch_direct': {'queue': 'insert'},

    # Anciennes tâches (compatibilité)
    'scan_music_task': {'queue': 'scan'},
    'worker_scan.*': {'queue': 'scan'},
    'worker_extract.*': {'queue': 'extract'},
    'worker_insert_bulk.*': {'queue': 'insert'},
    'worker_metadata.*': {'queue': 'deferred'},
    'worker_vector.*': {'queue': 'deferred'},
    'worker_cover.*': {'queue': 'deferred'},

    # Tâches différées
    'enrich_*': {'queue': 'deferred'},
    'vectorize_*': {'queue': 'deferred'},
}

# === CONFIGURATION DYNAMIQUE PAR QUEUE ===
PREFETCH_MULTIPLIERS = {
    'scan': 16,        # I/O bound - prefetch élevé
    'extract': 4,      # CPU bound - prefetch modéré
    'batch': 2,        # Memory bound - prefetch faible
    'insert': 8,       # DB bound - prefetch moyen
    'deferred': 6,     # Mixed - prefetch moyen
}

CONCURRENCY_SETTINGS = {
    'scan': 16,        # 16 workers pour I/O parallèle
    'extract': 8,      # 8 workers pour CPU parallèle
    'batch': 4,        # 4 workers pour mémoire
    'insert': 16,      # 16 workers pour DB parallèle
    'deferred': 6,     # 6 workers pour tâches background
}

@worker_init.connect
def configure_worker(sender=None, **kwargs):
    """
    Appliqué une fois au démarrage du worker.
    Ajuste dynamiquement le prefetch_multiplier et la concurrency.
    """
    worker_name = sender.hostname
    app = sender.app

    # Diagnostic Redis au démarrage
    logger.info(f"[WORKER INIT] Démarrage du worker {worker_name}")
    redis_ok = diagnostic_redis()
    if not redis_ok:
        logger.error(f"[WORKER INIT] Problème de connexion Redis détecté pour {worker_name}")
        # Le worker va probablement échouer, mais au moins on aura les logs

    # Cherche la queue liée au worker (par nom ou argument)
    queue_for_worker = None
    for queue_name in PREFETCH_MULTIPLIERS:
        if queue_name in worker_name:
            queue_for_worker = queue_name
            break

    if queue_for_worker:
        # Applique le prefetch
        app.conf.worker_prefetch_multiplier = PREFETCH_MULTIPLIERS[queue_for_worker]
        # Applique la concurrency
        app.conf.worker_concurrency = CONCURRENCY_SETTINGS[queue_for_worker]

        logger.info(f"[OPTIMIZED] {worker_name} → Queue={queue_for_worker} | "
                   f"Prefetch={PREFETCH_MULTIPLIERS[queue_for_worker]} | "
                   f"Concurrency={CONCURRENCY_SETTINGS[queue_for_worker]}")

@task_prerun.connect
def adjust_prefetch_per_task(task=None, **kwargs):
    """
    Ajuste dynamiquement selon la queue courante de la tâche.
    (utile si un worker écoute plusieurs queues)
    """
    request = getattr(task, 'request', None)
    if not request:
        return
    queue_name = request.delivery_info.get('routing_key')
    if queue_name and queue_name in PREFETCH_MULTIPLIERS:
        task.app.conf.worker_prefetch_multiplier = PREFETCH_MULTIPLIERS[queue_name]

