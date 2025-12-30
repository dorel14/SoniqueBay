# Diagnostic et Solution - Erreur d'Autorisation `/app/data`

## Problème Identifié

**Erreur :** `[Errno 13] Permission denied: '/app/data'`

**Contexte :** La tâche Celery `check_model_health` échoue avec une erreur de permission lors de l'accès au répertoire `/app/data` dans le backend_worker.

## Analyse des Causes

Après analyse du code, j'ai identifié **5 sources possibles** du problème :

### 1. **Cause la plus probable** : Répertoire non initialisé
- Le répertoire `/app/data` n'est pas créé au démarrage du conteneur
- Le `ModelPersistenceService` essaie d'accéder à `/app/data/models` mais échoue
- L'appel `mkdir(parents=True, exist_ok=True)` peut échouer si l'utilisateur n'a pas les permissions sur le parent

### 2. **Problème de permissions Docker**
- L'utilisateur sous lequel s'exécute le worker Celery n'a pas les droits d'écriture
- Ownership incorrect des répertoires (root vs soniquebay)
- Montage de volume avec permissions restrictives

### 3. **Timing d'initialisation**
- Les répertoires sont créés après le démarrage des workers Celery
- Race condition entre l'entrypoint et le démarrage des services

### 4. **Configuration Celery Beat**
- Le fichier `/app/data/celery_beat_data/celerybeat-schedule.db` n'existe pas
- Permissions insuffisantes pour Celery Beat

### 5. **Environnement d'exécution**
- Conteneur s'exécute avec un utilisateur différent de celui attendu
- Variables d'environnement manquantes

## Solutions Implémentées

J'ai créé une **solution en 3 parties** pour résoudre définitivement ce problème :

### 1. **Service d'Initialisation des Répertoires** (`backend_worker/services/data_directory_initializer.py`)
- Service dédié pour créer et vérifier tous les répertoires requis
- Gestion robuste des permissions et ownership
- Validation de l'accès en lecture/écriture
- Logs détaillés pour le debugging

### 2. **Amélioration du ModelPersistenceService** 
- Initialisation automatique des répertoires avant utilisation
- Tests de permissions intégrés
- Gestion d'erreurs améliorée avec messages explicites
- Fallback vers création directe si l'initialisation globale échoue

### 3. **Modification de l'Entrypoint Docker**
- Initialisation des répertoires au démarrage du conteneur
- Exécution sous l'utilisateur correct (soniquebay)
- Logs de confirmation de l'initialisation

## Fichiers Modifiés

1. **`backend_worker/services/data_directory_initializer.py`** (NOUVEAU)
   - Service complet d'initialisation des répertoires

2. **`backend_worker/services/model_persistence_service.py`** (MODIFIÉ)
   - Import du service d'initialisation
   - Initialisation robuste dans `__init__`
   - Tests de permissions avant utilisation

3. **`backend_worker/entrypoint.sh`** (MODIFIÉ)
   - Ajout de l'initialisation des répertoires avant démarrage
   - Exécution sous l'utilisateur soniquebay

4. **`scripts/diagnostic_data_permissions.py`** (NOUVEAU)
   - Script de diagnostic pour identifier les problèmes de permissions

## Comment Appliquer la Solution

### Option 1 : Reconstruction Docker (Recommandée)
```bash
# Reconstruire le backend_worker
docker-compose build backend_worker

# Redémarrer le service
docker-compose restart backend_worker
```

### Option 2 : Application Manuelle
```bash
# Exécuter le diagnostic pour vérifier l'état actuel
python scripts/diagnostic_data_permissions.py

# Appliquer la correction manuellement
cd backend_worker
python -c "from services.data_directory_initializer import initialize_data_directories; initialize_data_directories()"
```

## Vérification de la Solution

Pour vérifier que le problème est résolu :

1. **Vérifier les logs** :
   ```bash
   docker-compose logs backend_worker | grep "MODEL_PERSISTENCE"
   ```

2. **Vérifier la tâche Celery** :
   - La tâche `check_model_health` devrait maintenant réussir
   - Plus d'erreur "Permission denied"

3. **Tester manuellement** :
   ```bash
   docker-compose exec backend_worker python -c "from backend_worker.services.model_persistence_service import ModelPersistenceService; ModelPersistenceService()"
   ```

## Diagnostic Avancé

Si le problème persiste, utilisez le script de diagnostic :

```bash
python scripts/diagnostic_data_permissions.py
```

Ce script vérifiera :
- L'utilisateur courant et ses permissions
- L'environnement Docker
- L'état de tous les répertoires critiques
- La possibilité de créer et écrire dans les répertoires
- L'import et l'initialisation du ModelPersistenceService

## Impact et Bénéfices

- ✅ **Résolution définitive** de l'erreur de permission
- ✅ **Robustesse** : gestion d'erreurs améliorée
- ✅ **Diagnostic** : outils de debugging intégrés
- ✅ **Maintenabilité** : service d'initialisation réutilisable
- ✅ **Logs détaillés** : meilleure visibilité sur les problèmes

## Compatibilité

- ✅ Compatible Raspberry Pi 4
- ✅ Compatible l'architecture Docker existante
- ✅ Préserve les conventions de développement
- ✅ Aucun impact sur les autres services

---

**Auteur :** Kilo Code  
**Date :** 2025-12-29  
**Statut :** Solution prête à déployer