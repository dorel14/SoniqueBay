# Briefing Développeur — Phase 6 : Fusion Backend / Backend Worker

## 🎯 Objectif
Fusionner les répertoires `backend/` et `backend_worker/` pour réunir toute la logique métier en un seul lieu, éliminant la duplication de code.

---

## 📋 Tâches à Réaliser

### T6.1 : Auditer les duplications entre `backend/services/` et `backend_worker/services/`
**Fichier** : `docs/plans/taskiq_migrations/audit/duplications_services.md` (nouveau)

**Actions** :
1. Lister tous les fichiers dans `backend/services/`
2. Lister tous les fichiers dans `backend_worker/services/` (si encore présent)
3. Identifier les services dupliqués (même nom ou fonctionnalité similaire)
4. Documenter les différences de signature entre les versions
5. Prioriser les services à fusionner

**Format** :
```markdown
# Audit des Duplications Backend / Backend Worker

## Services Dupliqués
| Service | backend/services/ | backend_worker/services/ | Différences |
|---------|-------------------|--------------------------|-------------|
| album_service.py | ✅ | ✅ | Signatures différentes |
| artist_service.py | ✅ | ✅ | Logique dupliquée |

## Services Uniques
| Service | Emplacement | Action |
|---------|-------------|--------|
| scan_service.py | backend/services/ | Garder |
| vectorization_service.py | backend_worker/services/ | Déplacer |
```

**Validation** :
- [ ] Tous les services sont listés
- [ ] Les duplications sont identifiées
- [ ] Les priorités de fusion sont définies

---

### T6.2 : Créer la structure cible dans `backend/`

**Actions** :
1. Créer `backend/tasks/__init__.py`
2. Copier le contenu de `backend_worker/tasks/` vers `backend/tasks/`
3. Créer `backend/workers/__init__.py`
4. Copier le contenu de `backend_worker/workers/` vers `backend/workers/`
5. Créer `backend/models/__init__.py` (si pas déjà présent)
6. Copier le contenu de `backend_worker/models/` vers `backend/models/`

**Validation** :
- [ ] La structure cible est créée
- [ ] Tous les fichiers sont copiés
- [ ] Les `__init__.py` sont présents

---

### T6.3 : Fusionner les services dupliqués

**Actions** :
1. Pour chaque service dupliqué :
   - Comparer les deux versions
   - Identifier la version la plus complète
   - Fusionner les fonctionnalités manquantes
   - Mettre à jour les signatures si nécessaire
2. Supprimer les anciens fichiers dans `backend_worker/services/`

**Validation** :
- [ ] Tous les services dupliqués sont fusionnés
- [ ] Les fonctionnalités sont conservées
- [ ] Les tests passent après fusion

---

### T6.4 : Mettre à jour les imports dans toutes les tâches TaskIQ

**Actions** :
1. Rechercher tous les imports `backend_worker.tasks.*`
2. Remplacer par `backend.tasks.*`
3. Rechercher tous les imports `backend_worker.workers.*`
4. Remplacer par `backend.workers.*`
5. Rechercher tous les imports `backend_worker.models.*`
6. Remplacer par `backend.models.*`
7. Rechercher tous les imports `backend_worker.services.*`
8. Remplacer par `backend.services.*`

**Commandes utiles** :
```bash
# Rechercher les imports à modifier
grep -r "from backend_worker" backend/ tests/
grep -r "import backend_worker" backend/ tests/

# Remplacer (à faire manuellement ou avec sed)
sed -i 's/from backend_worker\.tasks\./from backend.tasks./g' fichier.py
sed -i 's/from backend_worker\.workers\./from backend.workers./g' fichier.py
```

**Validation** :
- [ ] Tous les imports sont mis à jour
- [ ] Aucun import `backend_worker` ne reste
- [ ] Les tests passent après mise à jour

---

### T6.5 : Mettre à jour `backend/taskiq_app.py`

**Actions** :
1. Déplacer `backend_worker/taskiq_app.py` vers `backend/taskiq_app.py`
2. Mettre à jour les imports dans le fichier
3. Inclure les nouvelles tâches depuis `backend.tasks.*`

**Validation** :
- [ ] Le fichier est déplacé
- [ ] Les imports sont mis à jour
- [ ] Le broker s'initialise correctement

---

### T6.6 : Mettre à jour `docker-compose.yml`

**Actions** :
1. Mettre à jour le service `taskiq-worker` pour pointer vers `backend/`
2. Mettre à jour les volumes montés
3. Mettre à jour la commande de démarrage

**Exemple** :
```yaml
taskiq-worker:
    build:
        context: .
        dockerfile: backend/Dockerfile
    container_name: soniquebay-taskiq-worker
    restart: unless-stopped
    command: ["python", "-m", "backend.taskiq_worker"]
    volumes:
        - ./backend:/app/backend
        - music-share:/music:ro
        - ./logs:/app/logs
```

**Validation** :
- [ ] Le service est mis à jour
- [ ] Les volumes sont corrects
- [ ] La commande de démarrage est correcte

---

### T6.7 : Mettre à jour les Dockerfiles

**Actions** :
1. Mettre à jour `backend/Dockerfile` pour inclure les tâches et workers
2. Supprimer `backend_worker/Dockerfile` (si encore présent)

**Validation** :
- [ ] Le Dockerfile est mis à jour
- [ ] L'image se construit correctement
- [ ] Le conteneur démarre correctement

---

### T6.8 : Supprimer `backend_worker/` après validation

**Actions** :
1. Vérifier qu'aucun import ne pointe vers `backend_worker/`
2. Supprimer le répertoire `backend_worker/`
3. Mettre à jour `.gitignore` si nécessaire

**Commandes** :
```bash
# Vérifier qu'aucun import ne reste
grep -r "from backend_worker" backend/ tests/
grep -r "import backend_worker" backend/ tests/

# Supprimer le répertoire
rm -rf backend_worker/
```

**Validation** :
- [ ] Aucun import `backend_worker` ne reste
- [ ] Le répertoire est supprimé
- [ ] Les tests passent après suppression

---

## 🧪 Tests à Exécuter

### Vérifications de Qualité de Code
```bash
# Exécuter ruff check sur les fichiers modifiés
ruff check backend/ tests/

# Vérifier l'absence d'erreurs Pylance dans VS Code
# (Ouvrir les fichiers et vérifier la barre d'état)
```

### Tests Unitaires
```bash
# Exécuter tous les tests unitaires
python -m pytest tests/unit/ -q --tb=no
```

### Tests d'Intégration
```bash
# Exécuter tous les tests d'intégration
python -m pytest tests/integration/ -q --tb=no
```

### Tests E2E
```bash
# Exécuter tous les tests E2E
python -m pytest tests/e2e/ -q --tb=no
```

### Tests Docker
```bash
# Démarrer les services
docker-compose build
docker-compose up -d

# Vérifier que tous les services démarrent
docker-compose ps

# Vérifier les logs
docker logs soniquebay-taskiq-worker
docker logs soniquebay-api
```

---

## ✅ Critères d'Acceptation

- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Tous les tests unitaires passent
- [ ] Tous les tests d'intégration passent
- [ ] Tous les tests E2E passent
- [ ] `docker-compose up` démarre avec la nouvelle structure
- [ ] Toutes les tâches TaskIQ fonctionnent
- [ ] Aucun import `backend_worker` ne reste
- [ ] Documentation à jour

---

## 🚨 Points d'Attention

1. **Ne pas supprimer** `backend_worker/` avant d'avoir validé que tous les imports sont mis à jour
2. **Tester chaque service** après fusion pour vérifier qu'aucune fonctionnalité n'est perdue
3. **Utiliser des imports absolus** (backend.xxx) conformément à AGENTS.md
4. **Logger avec le préfixe `[TASKIQ]`** pour différencier des logs Celery
5. **Tester localement** avant de committer

---

## 📞 Support

En cas de problème :
1. Consulter les logs Docker : `docker logs soniquebay-taskiq-worker`
2. Vérifier la configuration Redis : `docker exec soniquebay-redis redis-cli ping`
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 6 (Fusion Backend / Backend Worker)*
*Statut : En cours*
