# -*- coding: utf-8 -*-
import os
import logging
import pathlib
import stat
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import multiprocessing

# Créer une queue pour la communication inter-processus
log_queue = multiprocessing.Queue(-1)

date_format = "%Y%m%d"
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
logdir = os.path.join(parentdir, '/logs')
logfiles = os.path.join(logdir, 'soniquebay - '+ datetime.today().strftime(date_format) +'.log')


class SafeFormatter(logging.Formatter):
    def format(self, record):
        # Nettoie le message pour remplacer les caractères invalides
        if isinstance(record.msg, str):
            record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        return super().format(record)


pathlib.Path(logdir).mkdir(parents=True, exist_ok=True)
# Définir les permissions du répertoire de logs (777 = rwxrwxrwx)
try:
    os.chmod(logdir, 0o755)  # équivalent à 0o777
    print(f"Permissions du répertoire {logdir} modifiées avec succès")
except Exception as e:
    print(f"Impossible de modifier les permissions du répertoire {logdir}: {e}")

# Créer le fichier de log s'il n'existe pas et définir ses permissions
if not os.path.exists(logfiles):
    try:
        # Créer un fichier vide
        with open(logfiles, 'a', encoding='utf-8') as f:
            pass
        # Définir les permissions du fichier (666 = rw-rw-rw-)
        os.chmod(logfiles, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)  # équivalent à 0o666
        print(f"Fichier {logfiles} créé avec les permissions appropriées")
    except Exception as e:
        print(f"Impossible de créer ou de modifier les permissions du fichier {logfiles}: {e}")

# création de l'objet logger qui va nous servir à écrire dans les logs
logger = logging.getLogger()
# on met le niveau du logger à DEBUG, comme ça il écrit tout
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(getattr(logging, log_level))


# création d'un formateur qui va ajouter le temps, le niveau
# de chaque message quand on écrira un message dans le log
safe_formatter = SafeFormatter('%(asctime)s :: %(levelname)s :: %(filename)s:%(lineno)d - %(funcName)s() :: %(message)s')

# Création des handlers pour le QueueListener
file_handler = RotatingFileHandler(filename=logfiles,
                                    mode='a',
                                    maxBytes=1000000,
                                    backupCount=5,
                                    encoding='utf-8',)
file_handler.setLevel(getattr(logging, log_level))
file_handler.setFormatter(safe_formatter)

# Handler console avec encodage utf-8
class Utf8StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        # Force le stream en utf-8 si possible
        if hasattr(stream, "encoding") and stream.encoding and stream.encoding.lower() != "utf-8":
            stream = open(stream.fileno(), mode='w', encoding='utf-8', buffering=1)
        super().__init__(stream)

stream_handler = Utf8StreamHandler()
stream_handler.setLevel(getattr(logging, log_level))
stream_handler.setFormatter(safe_formatter)

# Configurer le QueueListener avec les handlers
listener = QueueListener(log_queue, file_handler, stream_handler)
listener.start()

# Configurer le logger principal pour utiliser un QueueHandler
queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)

# Fonction pour configurer le logging dans les processus enfants
def configure_worker_logging():
    """
    Configure logging for worker processes.
    This should be called at the start of each worker process.
    """
    # Supprimer tous les handlers existants
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Ajouter un QueueHandler qui envoie les logs à la queue partagée
    handler = QueueHandler(log_queue)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, log_level))
    return logger