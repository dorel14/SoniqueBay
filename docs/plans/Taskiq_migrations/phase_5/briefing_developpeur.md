# Briefing Développeur — Phase 5 : Décommission Celery

## 🎯 Objectif
Supprimer Celery après validation complète, en ne gardant que TaskIQ.

---

## 📋 Tâches à Réaliser

### Prérequis
- Phase 4 validée
- 2 semaines sans incident majeur
- Tous les tests passent

---

### T5.1 : Supprimer les imports Celery dans `backend/api/utils/`
**Fichier** : `backend/api/utils/` (plusieurs fichiers)

**Actions** :
1. Rechercher tous les imports Celery dans `backend/api/utils/`
2. Vérifier que plus aucun import Celery n'est utilisé
3. Remplacer par les appels TaskIQ si nécessaire

**Commandes** :
```bash
# Rechercher les imports Celery
grep -r "from celery" backend/api/utils/
grep -r "import celery" backend/api/utils/
```

**Validation** :
- [ ] Aucun import Celery trouvé
- [ ] Les appels TaskIQ fonctionnent

---

### T5.2 : Supprimer `backend_worker/celery_app.py`
**Fichier** : `backend_worker/celery_app.py` (supprimer)

**Actions** :
1. Vérifier que plus aucune tâche n'utilise `celery_app.py`
2. Supprimer le fichier

**Commandes** :
```bash
# Vérifier les imports
grep -r "from backend_worker.celery_app" backend/ tests/
grep -r "import backend_worker.celery_app" backend/ tests/

# Supprimer le fichier
rm backend_worker/celery_app.py
```

**Validation** :
- [ ] Aucun import trouvé
- [ ] Le fichier est supprimé

---

### T5.3 : Supprimer `backend_worker/celery_tasks.py`
**Fichier** : `backend_worker/celery_tasks.py` (supprimer)

**Actions** :
1. Vérifier que toutes les tâches ont été migrées
2. Supprimer le fichier

**Commandes** :
```bash
# Vérifier les imports
grep -r "from backend_worker.celery_tasks" backend/ tests/
grep -r "import backend_worker.celery_tasks" backend/ tests/

# Supprimer le fichier
rm backend_worker/celery_tasks.py
```

**Validation** :
- [ ] Aucun import trouvé
- [ ] Le fichier est supprimé

---

### T5.4 : Supprimer `backend_worker/celery_beat_config.py`
**Fichier** : `backend_worker/celery_beat_config.py` (supprimer)

**Actions** :
1. Vérifier que le scheduler TaskIQ est opérationnel
2. Supprimer le fichier

**Commandes** :
```bash
# Vérifier les imports
grep -r "from backend_worker.celery_beat_config" backend/ tests/
grep -r "import backend_worker.celery_beat_config" backend/ tests/

# Supprimer le fichier
rm backend_worker/celery_beat_config.py
```

**Validation** :
- [ ] Aucun import trouvé
- [ ] Le fichier est supprimé
- [ ] Le scheduler TaskIQ fonctionne

---

### T5.5 : Nettoyer `docker-compose.yml`
**Fichier** : `docker-compose.yml`

**Actions** :
1. Supprimer le service `celery-worker`
2. Supprimer le service `celery_beat`
3. Garder uniquement `taskiq-worker`

**Validation** :
- [ ] Le service `celery-worker` est supprimé
- [ ] Le service `celery_beat` est supprimé
- [ ] Le service `taskiq-worker` est présent
- [ ] `docker-compose up` démarre correctement

---

### T5.6 : Mettre à jour la documentation
**Fichiers** :
- `README.md`
- `docs/` (runbooks, architecture)

**Actions** :
1. Mettre à jour `README.md` pour refléter la nouvelle architecture
2. Mettre à jour les runbooks
3. Mettre à jour la documentation architecture

**Validation** :
- [ ] `README.md` est mis à jour
- [ ] Les runbooks sont mis à jour
- [ ] La documentation architecture est mise à jour

---

## 🧪 Tests à Exécuter

### Vérifications de Qualité de Code
```bash
# Exécuter ruff check sur les fichiers modifiés
ruff check backend/api/utils/ docker-compose.yml README.md docs/

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
- [ ] `docker-compose up` démarre sans Celery
- [ ] Toutes les tâches fonctionnent via TaskIQ
- [ ] Aucun import Celery ne reste
- [ ] Documentation à jour

---

## 🚨 Points d'Attention

1. **Ne supprimer** les fichiers Celery qu'après confirmation que plus aucune tâche ne les utilise
2. **Utiliser des imports absolus** (backend.xxx) conformément à AGENTS.md
3. **Logger avec le préfixe `[TASKIQ]`** pour différencier de Celery
4. **Tester localement** avant de committer
5. **Vérifier que le scheduler TaskIQ** fonctionne après suppression de Celery Beat

---

## 📞 Support

En cas de problème :
1. Consulter les logs Docker : `docker logs soniquebay-taskiq-worker`
2. Vérifier la configuration Redis : `docker exec soniquebay-redis redis-cli info`
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 5 (Décommission Celery)*
*Statut : En cours*
