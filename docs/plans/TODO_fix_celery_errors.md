# TODO - Correction des erreurs Celery

## Problèmes identifiés

### 1. Conflit de merge non résolu dans `celery_tasks.py`
- **Fichier**: `backend_worker/celery_tasks.py`
- **Ligne**: 378 et autres
- **Erreur**: `IndentationError: expected an indented block after 'try' statement`
- **Cause**: Marqueurs de conflit Git `<<<<<<< HEAD`, `=======`, `>>>>>>> origin/master` présents dans le fichier

### 2. EOFError dans le logging multiprocessing
- **Fichier**: `backend_worker/utils/logging.py`
- **Erreur**: `EOFError` dans `QueueListener._monitor`
- **Cause**: Utilisation de `multiprocessing.Queue` au niveau du module qui n'est pas compatible avec les processus enfants Celery

## Plan de correction

### Étape 1: Corriger le conflit de merge dans celery_tasks.py
- [x] Choisir la version sentence-transformers (plus légère pour Raspberry Pi)
- [x] Supprimer tous les marqueurs de conflit
- [x] Vérifier la cohérence du code

### Étape 2: Corriger le logging dans backend_worker/utils/logging.py
- [x] Remplacer `multiprocessing.Queue` par `queue.Queue` (thread-safe)
- [x] Ajouter une gestion robuste des erreurs pour le QueueListener
- [x] Créer une classe SafeQueueListener qui gère les EOFError
- [x] S'assurer que la configuration fonctionne dans les workers Celery

### Étape 3: Tester
- [ ] Vérifier que le worker Celery démarre sans erreur
- [ ] Vérifier que les logs sont écrits correctement

## Fichiers concernés
- `backend_worker/celery_tasks.py`
- `backend_worker/utils/logging.py`
