# Correctif Last.fm - Artistes Similaires

## 🔍 Analyse du Problème

### Cause Racine Identifiée
Le service Last.fm ne parvenait pas à stocker les artistes similaires dans la base de données à cause de **4 problèmes critiques** :

1. **Format de données incompatible** : Le service envoyait des `similar_artist_id` (IDs numériques) mais l'API attendait des `name` (noms d'artistes)
2. **Endpoint API mal utilisé** : Mauvaise correspondance entre le format d'envoi et les attentes de l'endpoint
3. **Pas de vérification d'existence** : Les artistes similaires n'étaient pas recherchés/créés en BDD
4. **Données Last.fm non persistées** : `lastfm_url`, `lastfm_listeners` n'étaient pas stockés correctement

### Logs du Problème
```
[LASTFM] Making API call to http://api:8001/api/artists/4814/similar with body: {'limit': 10}
[LASTFM] API response status: 200, body: {"task_id":"a08ce048-c67a-458c-9280-2afee37668f3","message":"Similar artists fetch triggered"}
[LASTFM] Similar artists fetch completed: Similar artists fetch triggered
```

Le processus semblait réussir (200 OK) mais aucune donnée n'était persistée.

## ✅ Correctifs Appliqués

### 1. Service Last.fm (`backend_worker/services/lastfm_service.py`)

**Fonction `_store_similar_artists` refactorisée :**

- ✅ **Format de données corrigé** : Envoi de `{"name": "Artist Name", "weight": 0.8}` au lieu d'IDs
- ✅ **Recherche d'artistes améliorée** : Utilisation de `musicbrainz_artistid` en priorité puis `name`
- ✅ **Logging détaillé** : Ajout de logs pour debugging et monitoring
- ✅ **Gestion d'erreurs renforcée** : Timeout augmenté, try/catch étendu
- ✅ **Validation des données** : Vérification de la validité des données avant envoi

### 2. Endpoint API (`backend/api/routers/artists_api.py`)

**Endpoint `/api/artists/{artist_id}/lastfm-info` amélioré :**

- ✅ **Plus de champs persistés** : `lastfm_bio`, `lastfm_images`, `lastfm_musicbrainz_id`
- ✅ **Logging ajouté** : Suivi des opérations de mise à jour
- ✅ **Refresh de l'objet** : `db.refresh()` pour s'assurer de la persistance

### 3. Import Logger
- ✅ **Ajout de l'import logger** dans `artists_api.py`

## 🧪 Test du Correctif

### Script de Test
Le script `test_lastfm_fix.py` permet de valider le correctif :

```bash
python test_lastfm_fix.py
```

### Tests Effectués
1. **Recherche d'artiste existant** (Radiohead)
2. **Test endpoint Last.fm info** (stockage des métadonnées)
3. **Test endpoint similar artists** (avec format corrigé)
4. **Vérification des similar artists stockés**
5. **Vérification des données Last.fm persistées**

### Validation Manuelle
Pour tester manuellement :

```bash
# 1. Vérifier les similar artists stockés
curl "http://api:8001/api/artists/4814/similar"

# 2. Vérifier les données Last.fm
curl "http://api:8001/api/artists/4814"

# 3. Tester l'endpoint similar artists directement
curl -X POST "http://api:8001/api/artists/4814/similar" \
  -H "Content-Type: application/json" \
  -d '[{"name": "Muse", "weight": 0.9}, {"name": "Thom Yorke", "weight": 0.8}]'
```

## 📊 Flow Corrigé

### Avant (Problématique)
```
Worker Celery → /api/artists/{id}/fetch-similar (trigger seulement)
    ↓
Service Last.fm → /api/artists/{id}/similar (format incorrect)
    ↓
API Reject/Ignore → Aucune donnée stockée
```

### Après (Corrigé)
```
Worker Celery → /api/artists/{id}/fetch-similar (trigger seulement)
    ↓
Service Last.fm → /api/artists/{id}/similar (format correct)
    ↓
API Valide et Stocke → Données persistées en BDD
    ↓
Vérification → Similar artists visibles dans /api/artists/{id}/similar
```

## 🔧 Fichiers Modifiés

1. **`backend_worker/services/lastfm_service.py`**
   - Fonction `_store_similar_artists` refactorisée
   - Format d'envoi corrigé
   - Logging amélioré

2. **`backend/api/routers/artists_api.py`**
   - Endpoint `/api/artists/{artist_id}/lastfm-info` amélioré
   - Import logger ajouté
   - Plus de champs Last.fm persistés

3. **`test_lastfm_fix.py`** (nouveau)
   - Script de validation du correctif

## ⚡ Impact sur les Performances

- **Timeouts augmentés** : 15s → 30s pour plus de robustesse
- **Logging sélectif** : DEBUG seulement pour le debugging
- **Validation des données** : Évite les appels API inutiles
- **Gestion d'erreurs** : Rollback automatique en cas de problème

## 🎯 Prochaines Étapes

1. **Déployer les modifications**
2. **Exécuter le script de test**
3. **Vérifier les logs** pour s'assurer du bon fonctionnement
4. **Tester avec un vrai artista** via l'interface utilisateur
5. **Monitorer les performances** sur le RPi4

## 📝 Notes Techniques

- Le correctif respecte l'architecture existante "Separation of Concerns"
- Aucune modification de schéma de base de données requise
- Compatible avec l'environnement Docker existant
- Respecte les contraintes du RPi4 (RAM, CPU)