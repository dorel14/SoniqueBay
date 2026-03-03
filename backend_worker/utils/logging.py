# -*- coding: utf-8 -*-
"""Module de configuration du logging pour le backend worker SoniqueBay.

Utilise un QueueHandler/QueueListener basé sur queue.Queue (thread-safe)
au lieu de multiprocessing.Queue pour éviter les EOFError lors du démarrage
des workers Celery dans un contexte multiprocessing.

Architecture:
- queue.Queue (thread-safe) remplace multiprocessing.Queue
- SafeQueueListener gère les EOFError et BrokenPipeError proprement
- configure_worker_logging() à appeler dans chaque processus worker Celery

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import logging
import os
import pathlib
import queue
import stat
import sys
from datetime import datetime
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

# === CONFIGURATION DES CHEMINS ===
date_format = "%Y%m%d"
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
logdir = os.path.join(parentdir, 'logs')
logfiles = os.path.join(logdir, 'soniquebay - ' + datetime.today().strftime(date_format) + '.log')

# === CRÉATION DU RÉPERTOIRE DE LOGS ===
pathlib.Path(logdir).mkdir(parents=True, exist_ok=True)
try:
    os.chmod(logdir, 0o755)
except Exception:
    pass  # Ignorer les erreurs de permissions (ex: Docker)

# Créer le fichier de log s'il n'existe pas
if not os.path.exists(logfiles):
    try:
        with open(logfiles, 'a', encoding='utf-8') as f:
            pass
        os.chmod(
            logfiles,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
        )
    except Exception:
        pass  # Ignorer les erreurs de création


# === FORMATEUR SÉCURISÉ ===
class SafeFormatter(logging.Formatter):
    """Formateur qui gère les caractères non-UTF8 dans les messages de log."""

    def format(self, record: logging.LogRecord) -> str:
        """Formate le record en nettoyant les caractères invalides."""
        if isinstance(record.msg, str):
            record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        return super().format(record)


# === HANDLER CONSOLE UTF-8 ===
class Utf8StreamHandler(logging.StreamHandler):
    """Handler console qui force l'encodage UTF-8."""

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        # Force le stream en utf-8 si possible
        if hasattr(stream, "encoding") and stream.encoding and stream.encoding.lower() != "utf-8":
            try:
                stream = open(stream.fileno(), mode='w', encoding='utf-8', buffering=1)
            except Exception:
                pass  # Garder le stream original si impossible
        super().__init__(stream)


# === QUEUE LISTENER ROBUSTE ===
class SafeQueueListener(QueueListener):
    """QueueListener qui gère proprement les EOFError et BrokenPipeError.

    Ces erreurs surviennent quand les processus enfants Celery se terminent
    et que la queue de logging est fermée avant que le listener ait fini.
    """

    def dequeue(self, block: bool) -> logging.LogRecord:
        """Récupère un record depuis la queue avec gestion des erreurs."""
        try:
            return self.queue.get(block)
        except (EOFError, OSError, BrokenPipeError):
            # La queue a été fermée - retourner None pour arrêter proprement
            raise queue.Empty

    def _monitor(self):
        """Thread de monitoring avec gestion robuste des erreurs."""
        try:
            super()._monitor()
        except (EOFError, OSError, BrokenPipeError):
            # Erreur normale lors de l'arrêt du processus - ignorer silencieusement
            pass
        except Exception as e:
            # Erreur inattendue - logger sur stderr pour ne pas perdre l'info
            try:
                sys.stderr.write(f"[SafeQueueListener] Erreur inattendue dans _monitor: {e}\n")
            except Exception:
                pass


# === INITIALISATION DU LOGGING ===
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
_log_level_int = getattr(logging, log_level, logging.INFO)

safe_formatter = SafeFormatter(
    '%(asctime)s :: %(levelname)s :: %(filename)s:%(lineno)d - %(funcName)s() :: %(message)s'
)

# Handler fichier rotatif
file_handler = RotatingFileHandler(
    filename=logfiles,
    mode='a',
    maxBytes=1_000_000,
    backupCount=5,
    encoding='utf-8',
)
file_handler.setLevel(_log_level_int)
file_handler.setFormatter(safe_formatter)

# Handler console UTF-8
stream_handler = Utf8StreamHandler()
stream_handler.setLevel(_log_level_int)
stream_handler.setFormatter(safe_formatter)

# === QUEUE THREAD-SAFE (remplace multiprocessing.Queue) ===
# IMPORTANT: On utilise queue.Queue (thread-safe) et NON multiprocessing.Queue
# multiprocessing.Queue cause des EOFError dans les workers Celery car la queue
# n'est pas correctement héritée par les processus enfants.
log_queue: queue.Queue = queue.Queue(-1)

# Démarrage du QueueListener avec le listener robuste
listener = SafeQueueListener(log_queue, file_handler, stream_handler, respect_handler_level=True)
listener.start()

# Configuration du logger racine avec QueueHandler
logger = logging.getLogger()
logger.setLevel(_log_level_int)

# Supprimer les handlers existants pour éviter les doublons
for _handler in logger.handlers[:]:
    logger.removeHandler(_handler)

queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)


# === FONCTIONS UTILITAIRES ===

def configure_worker_logging() -> logging.Logger:
    """Configure le logging pour les processus workers Celery.

    Cette fonction doit être appelée au démarrage de chaque processus worker.
    Elle reconfigure le logger pour utiliser la queue partagée thread-safe.

    Returns:
        Logger configuré pour le worker
    """
    worker_logger = logging.getLogger()

    # Supprimer tous les handlers existants
    for handler in worker_logger.handlers[:]:
        worker_logger.removeHandler(handler)

    # Ajouter un QueueHandler qui envoie les logs à la queue partagée
    handler = QueueHandler(log_queue)
    worker_logger.addHandler(handler)
    worker_logger.setLevel(_log_level_int)

    return worker_logger


def cleanup_logging() -> None:
    """Nettoie les ressources de logging à la fin du programme.

    Doit être appelée lors de l'arrêt du worker pour éviter les fuites
    de ressources et les erreurs de fermeture de queue.
    """
    global listener

    # Arrêter le listener proprement
    try:
        if listener is not None and hasattr(listener, 'stop'):
            listener.stop()
    except (OSError, EOFError, BrokenPipeError):
        pass  # Ignorer les erreurs si déjà arrêté

    # Supprimer les handlers du logger
    try:
        for handler in logger.handlers[:]:
            try:
                logger.removeHandler(handler)
                handler.close()
            except Exception:
                pass
    except Exception:
        pass

    # Vider et fermer la queue
    try:
        # Vider la queue pour éviter les blocages
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except queue.Empty:
                break
    except Exception:
        pass


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger pour le nom donné.

    Args:
        name: Nom du logger (généralement __name__)

    Returns:
        Logger configuré
    """
    return logging.getLogger(name)
