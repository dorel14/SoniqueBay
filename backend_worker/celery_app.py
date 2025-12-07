
from celery import Celery
from celery.signals import worker_init, task_prerun, task_postrun, worker_shutdown

from backend_worker.utils.logging import logger
from backend_worker.utils.celery_monitor import measure_celery_task_size, update_size_metrics, log_task_size_report, get_size_summary, auto_configure_celery_limits
import os
import redis
import socket
from kombu import Queue

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

        # Artist GMM workers
        'backend_worker.workers.artist_gmm.artist_gmm_worker',

        # Last.fm workers
        'backend_worker.workers.lastfm.lastfm_worker',

        # Vectorization workers
        'backend_worker.workers.vectorization.track_vectorization_worker',

        # Tâches de covers (NOUVEAU - requis pour process_artist_images et process_album_covers)
        'backend_worker.covers_tasks',

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
    broker_transport_options = {
        'priority_steps': list(range(10)),
        'sep': ':',
        'queue_order_strategy': 'priority',
    },
    # === COMPRESSION POUR GROS MESSAGES ===
    task_compression='gzip',               # Compression automatique
    result_compression='gzip',

    # === ZONE TEMPORELLE ===
    timezone=os.getenv('TZ', default='UTC'),
    enable_utc=True,

    # === FORCER LE WORKER À ÉCOUTER TOUTES LES QUEUES ===
    # Définir explicitement les queues que le worker doit consommer
    worker_queues=[
        'scan', 'extract', 'batch', 'insert', 'covers',
        'deferred_vectors', 'deferred_covers', 'deferred_enrichment',
        'vectorization_monitoring', 'deferred', 'celery', 'maintenance'
    ],

    # === PRIORITÉS DES QUEUES (NOUVELLE CONFIGURATION) ===
    # Activation du support des priorités dans Celery
    task_queue_priority_enabled=True,
    task_queue_priority={
        'scan': 9,          # Priorité maximale - scans complets
        'extract': 8,       # Priorité élevée
        'batch': 8,         # Priorité élevée
        'insert': 7,        # Priorité élevée
        'covers': 5,         # Priorité normale
        'maintenance': 5,    # Priorité normale
        'vectorization_monitoring': 5,  # Priorité normale
        'celery': 5,         # Priorité normale
        'deferred_vectors': 4,      # Priorité basse - tâches différées
        'deferred_covers': 3,       # Priorité basse
        'deferred_enrichment': 2,   # Priorité basse
        'deferred': 1,       # Priorité la plus basse
    },

    # === CONFIGURATION SPÉCIFIQUE POUR LES PRIORITÉS ===
    # Configurer les workers pour respecter les priorités des queues
    worker_concurrency=2,           # Limité pour Raspberry Pi
    task_queue_priority_strategy='priority',  # Stratégie de priorité explicite
    task_queue_max_priority=10,      # Priorité maximale
    task_queue_default_priority=5,   # Priorité par défaut

    # === VALIDATION DES CONFIGURATIONS DE QUEUES ===
    # Ajouter une validation pour s'assurer que toutes les queues ont une configuration cohérente

)

# Validation des timeouts
logger.info(f"[Celery Config] Timeouts configurés - task_time_limit: {celery.conf.task_time_limit}, task_soft_time_limit: {celery.conf.task_soft_time_limit}")

# === DÉFINITION DES QUEUES SPÉCIALISÉES AVEC PRIORITÉS ===
task_queues = {
    # Queue DISCOVERY (I/O intensive) - PRIORITÉ MAXIMALE (0)
    'scan': {
        'exchange': 'scan',
        'routing_key': 'scan',
        'delivery_mode': 2,  # Persistant
        'priority': 0,  # Priorité la plus élevée
    },

    # Queue EXTRACTION (CPU intensive) - PRIORITÉ ÉLEVÉE (1)
    'extract': {
        'exchange': 'extract',
        'routing_key': 'extract',
        'delivery_mode': 1,  # Non-persistant
        'priority': 1,
    },

    # Queue BATCHING (Memory intensive) - PRIORITÉ ÉLEVÉE (2)
    'batch': {
        'exchange': 'batch',
        'routing_key': 'batch',
        'delivery_mode': 1,
        'priority': 2,
    },

    # Queue INSERTION (DB intensive) - PRIORITÉ ÉLEVÉE (3)
    'insert': {
        'exchange': 'insert',
        'routing_key': 'insert',
        'delivery_mode': 2,  # Persistant pour fiabilité
        'priority': 3,
    },

    # Queue COVERS (API/Réseau intensif) - PRIORITÉ NORMALE (4)
    'covers': {
        'exchange': 'covers',
        'routing_key': 'covers',
        'delivery_mode': 1,  # Non-persistant pour performance
        'priority': 4,
    },

    # ✅ Queue VECTORS DIFFÉRÉS (CPU intensif) - PRIORITÉ BASSE (6)
    'deferred_vectors': {
        'exchange': 'deferred_vectors',
        'routing_key': 'deferred_vectors',
        'delivery_mode': 1,  # Non-persistant (calculs CPU)
        'priority': 6,
    },

    # ✅ Queue COVERS DIFFÉRÉS (Réseau/API intensif) - PRIORITÉ BASSE (7)
    'deferred_covers': {
        'exchange': 'deferred_covers',
        'routing_key': 'deferred_covers',
        'delivery_mode': 1,  # Non-persistant (APIs externes)
        'priority': 7,
    },

    # ✅ Queue ENRICHMENT DIFFÉRÉS (I/O intensif) - PRIORITÉ BASSE (8)
    'deferred_enrichment': {
        'exchange': 'deferred_enrichment',
        'routing_key': 'deferred_enrichment',
        'delivery_mode': 1,  # Non-persistant (données temporaires)
        'priority': 8,
    },

    # Queue MONITORING VECTORISATION - PRIORITÉ NORMALE (5)
    'vectorization_monitoring': {
        'exchange': 'vectorization_monitoring',
        'routing_key': 'vectorization_monitoring',
        'delivery_mode': 1,  # Non-persistant pour monitoring léger
        'priority': 5,
    },

    # Queue LEGACY pour compatibilité - PRIORITÉ BASSE (9)
    'deferred': {
        'exchange': 'deferred',
        'routing_key': 'deferred',
        'delivery_mode': 1,
        'priority': 9,
    },

    # Queue par défaut (compatibilité) - PRIORITÉ NORMALE (5)
    'celery': {'exchange': 'celery', 'routing_key': 'celery', 'priority': 5},

    # Queue MAINTENANCE (tâches de nettoyage et monitoring) - PRIORITÉ NORMALE (4)
    'maintenance': {
        'exchange': 'maintenance',
        'routing_key': 'maintenance',
        'delivery_mode': 1,  # Non-persistant (tâches légères)
        'priority': 4,
    },
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

# === DÉCLARATION EXPLICITE DES QUEUES AVEC PRIORITÉS ===
# Déclarer toutes les queues pour s'assurer qu'elles existent dans Redis

celery.conf.task_queues = [
    Queue('scan', routing_key='scan', queue_arguments={'x-priority': 0}),
    Queue('extract', routing_key='extract', queue_arguments={'x-priority': 1}),
    Queue('batch', routing_key='batch', queue_arguments={'x-priority': 2}),
    Queue('insert', routing_key='insert', queue_arguments={'x-priority': 3}),
    Queue('covers', routing_key='covers', queue_arguments={'x-priority': 4}),
    Queue('deferred_vectors', routing_key='deferred_vectors', queue_arguments={'x-priority': 6}),
    Queue('deferred_covers', routing_key='deferred_covers', queue_arguments={'x-priority': 7}),
    Queue('deferred_enrichment', routing_key='deferred_enrichment', queue_arguments={'x-priority': 8}),
    Queue('vectorization_monitoring', routing_key='vectorization_monitoring', queue_arguments={'x-priority': 5}),
    Queue('deferred', routing_key='deferred', queue_arguments={'x-priority': 9}),
    Queue('celery', routing_key='celery', queue_arguments={'x-priority': 5}),
    Queue('maintenance', routing_key='maintenance', queue_arguments={'x-priority': 4}),
]

@worker_init.connect
def configure_worker(sender=None, **kwargs):
    """Configure le worker unifié avec autoscale au démarrage."""
    worker_name = sender.hostname

    # Diagnostic Redis au démarrage
    logger.info(f"[WORKER INIT] Démarrage du worker unifié {worker_name} avec autoscale")
    redis_ok = diagnostic_redis()
    if not redis_ok:
        logger.error(f"[WORKER INIT] Problème de connexion Redis détecté pour {worker_name}")

    # Forcer le worker à écouter TOUTES les queues définies avec priorités
    # Au lieu de laisser autoscale décider automatiquement
    all_queues = list(task_queues.keys())
    logger.info(f"[WORKER] {worker_name} configuré pour écouter les queues: {all_queues}")

    # Appliquer la configuration des queues avec priorités
    sender.app.control.add_consumer(
        queue=all_queues,
        destination=[worker_name]
    )

    # Configurer les workers pour consommer les queues par priorité
    # Les queues avec priorité plus basse (chiffre plus élevé) seront traitées après
    sender.app.conf.worker_prefetch_multiplier = 1
    sender.app.conf.worker_concurrency = 2  # Limité pour Raspberry Pi
    sender.app.conf.task_acks_late = True

    # Configuration spécifique pour le respect des priorités
    sender.app.conf.task_queue_priority = {
        'scan': 0,          # Priorité maximale
        'extract': 1,       # Priorité élevée
        'batch': 2,         # Priorité élevée
        'insert': 3,        # Priorité élevée
        'covers': 4,         # Priorité normale
        'maintenance': 4,    # Priorité normale
        'vectorization_monitoring': 5,  # Priorité normale
        'celery': 5,         # Priorité normale
        'deferred_vectors': 6,      # Priorité basse
        'deferred_covers': 7,       # Priorité basse
        'deferred_enrichment': 8,   # Priorité basse
        'deferred': 9,       # Priorité la plus basse
    }

    logger.info(f"[WORKER] {worker_name} consommateur ajouté pour toutes les queues avec priorités configurées")
    logger.info(f"[WORKER] Priorités des queues: {sender.app.conf.task_queue_priority}")


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

        # === DIAGNOSTIC PIDBOX ET KOMBU ===
        # Log des informations de routage et de configuration des queues
        if hasattr(task, 'request') and hasattr(task.request, 'routing_key'):
            logger.info(f"[PIDBOX DIAG] Routing key: {task.request.routing_key}")
        if hasattr(task, 'request') and hasattr(task.request, 'exchange'):
            logger.info(f"[PIDBOX DIAG] Exchange: {task.request.exchange}")

        # Log de la configuration des queues Celery
        logger.info(f"[PIDBOX DIAG] Worker queues: {getattr(sender, 'queues', 'non-disponible')}")
        logger.info(f"[PIDBOX DIAG] Task queues config: {getattr(task, 'queues', 'non-disponible')}")

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

