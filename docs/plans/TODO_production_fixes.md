# TODO - Correctifs Production

> Branche : `blackboxai/production-fixes`
> Créée le : 2025-03-05
> Base : `master` (commit 4ba4834)

## Objectif
Cette branche est dédiée aux correctifs suite aux tests en production.

## Liste des correctifs

| # | Problème | Statut | Commit |
|---|----------|--------|--------|
| 1 | **DNS Error "Name or service not known"** - Variable d'environnement API_URL incorrecte | ✅ Corrigé | ef280de |

### Fix #1 : DNS Error "Name or service not known"

**Problème :**
Les workers Celery ne pouvaient pas se connecter à l'API car la variable d'environnement `API_URL` dans `docker-compose.yml` pointait vers un hostname inexistant (`api` au lieu de `library`).

**Root Cause :**
```yaml
# AVANT (incorrect)
environment:
  - API_URL=http://api:8001  # ❌ 'api' n'est pas un alias réseau valide

# APRÈS (corrigé)
environment:
  - API_URL=http://library:8001  # ✅ 'library' est l'alias défini dans api-service
```

**Solution :**
Correction unique dans `docker-compose.yml` :
- `celery-worker` : `API_URL=http://library:8001`
- `frontend` : `API_URL=http://library:8001`

**Pourquoi c'est la bonne approche :**
- ✅ Le code Python utilise déjà `os.getenv("API_URL", "http://library:8001")`
- ✅ Les valeurs par défaut dans le code sont correctes
- ✅ Seule la configuration Docker était incorrecte
- ✅ **Aucune modification du code source nécessaire** - configuration via variables d'environnement uniquement

**Action requise :**
⚠️ **Redémarrer les conteneurs** pour prendre en compte les changements :
```bash
docker-compose down && docker-compose up -d
# ou juste
docker-compose restart celery-worker frontend
```

**Vérification :**
```bash
# Vérifier que la variable est correcte dans le conteneur
docker exec soniquebay-celery-worker env | grep API_URL
# Doit afficher : API_URL=http://library:8001
```

## Procédure de travail

1. **Réception du problème** : L'utilisateur décrit le bug rencontré en production
2. **Analyse** : Investigation des logs et du code concerné
3. **Correction** : Implémentation du fix avec tests
4. **Commit** : Format `type(scope): description` (Conventional Commits)
5. **Test** : Vérification en production
6. **Itération** : Si nouveau problème, retour à l'étape 1

## Notes

- Chaque correction fait l'objet d'un commit séparé
- Les tests unitaires sont obligatoires pour chaque fix
- La branche reste ouverte tant que des correctifs sont nécessaires
- **Principe important** : Toujours privilégier la configuration via variables d'environnement plutôt que de modifier le code source

---

**Statut global** : 🟢 Fix #1 terminé - **Redémarrage des conteneurs requis**
