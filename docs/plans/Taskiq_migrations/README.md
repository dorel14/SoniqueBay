# Migration Celery → TaskIQ — SoniqueBay

## 📋 Résumé

Ce projet documente la migration progressive de Celery vers TaskIQ pour SoniqueBay, avec une stratégie anti-régression basée sur l'audit du code existant.

---

## 🎯 Objectifs

1. **Migrer** de Celery vers TaskIQ sans interruption de service
2. **Garantir** zéro régression sur les tests existants
3. **Optimiser** les performances pour le Raspberry Pi 4
4. **Simplifier** l'architecture en fusionnant backend et backend_worker

---

## 📊 État d'Avancement

| Phase | Statut | Durée | Description |
|-------|--------|-------|-------------|
| Phase 0 — Audit | ✅ TERMINÉE | 1-2 jours | Cartographie de l'existant |
| Phase 1 — Socle | 🚀 PRÊTE | 2-3 jours | Ajout de TaskIQ sans impact |
| Phase 2 — Pilote | ⬜ À FAIRE | 2-4 jours | Migration 1-2 tâches non critiques |
| Phase 3 — DB Direct | ⬜ À FAIRE | 3-5 jours | Accès DB direct pour workers |
| Phase 4 — Migration | ⬜ À FAIRE | 5-10 jours | Migration progressive du cœur |
| Phase 5 — Décommission | ⬜ À FAIRE | 2-3 jours | Suppression de Celery |
| Phase 6 — Fusion | ⬜ À FAIRE | 5-8 jours | Fusion backend/backend_worker |

---

## 📁 Structure des Fichiers

```
docs/plans/taskiq_migrations/
├── README.md                          # Ce fichier
├── PLAN_AMELIORE_MIGRATION_TASKIQ.md  # Plan détaillé
├── WORKFLOW_VALIDATION.md             # Workflow de validation
├── audit/                             # Phase 0 — Audit
│   ├── taches_celery.md               # 26 tâches identifiées
│   ├── dependances_taches.md          # Flux inter-tâches
│   ├── baseline_tests_unitaires.txt   # 31 tests unitaires
│   ├── baseline_tests_integration.txt # 6 tests intégration
│   └── configuration_redis.md         # Config Redis documentée
├── phase_0/                           # Phase 0 — Résultats
│   └── resultats_audit.md             # Résumé des résultats
├── phase_1/                           # Phase 1 — Socle TaskIQ
│   ├── briefing_developpeur.md        # Instructions développeur
│   └── briefing_testeur.md            # Instructions testeur
├── phase_2/                           # Phase 2 — Migration Pilote
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
├── phase_3/                           # Phase 3 — Accès DB Direct
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
├── phase_4/                           # Phase 4 — Migration Progressive
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
├── phase_5/                           # Phase 5 — Décommission Celery
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
└── phase_6/                           # Phase 6 — Fusion Backend
    ├── briefing_developpeur.md
    └── briefing_testeur.md
```

---

## 🔍 Phase 0 — Audit et Préparation (TERMINÉE)

### Livrables
- ✅ Matrice des 26 tâches Celery avec signatures complètes
- ✅ Documentation des dépendances entre tâches
- ✅ Baseline des tests (31 unitaires + 6 intégration)
- ✅ Configuration Redis documentée

### Découvertes Clés
- **26 tâches** identifiées (4 haute, 7 moyenne, 15 basse criticité)
- **Pipeline principale** : `scan.discovery` → `metadata.extract_batch` → `batch.process_entities` → `insert.direct_batch`
- **13 queues** configurées avec priorités strictes
- **Accès DB** : Seule `insert.direct_batch` accède à la DB via API HTTP

### Résultats Détaillés
- Voir : [`phase_0/resultats_audit.md`](phase_0/resultats_audit.md)

---

## 🚀 Phase 1 — Socle TaskIQ Minimal (PRÊTE)

### Objectif
Ajouter TaskIQ sans impacter Celery existant.

### Tâches
- [ ] T1.1 : Ajouter les dépendances TaskIQ
- [ ] T1.2 : Créer `backend_worker/taskiq_app.py`
- [ ] T1.3 : Créer `backend_worker/taskiq_worker.py`
- [ ] T1.4 : Ajouter le service TaskIQ dans `docker-compose.yml`
- [ ] T1.5 : Ajouter les variables d'environnement
- [ ] T1.6 : Créer les tests unitaires TaskIQ
- [ ] T1.7 : Exécuter les tests de non-régression

### Briefings
- Développeur : [`phase_1/briefing_developpeur.md`](phase_1/briefing_developpeur.md)
- Testeur : [`phase_1/briefing_testeur.md`](phase_1/briefing_testeur.md)

---

## 🛡️ Stratégie Anti-Régression

### 1. Mode Coexistence
```
Celery Worker (existant) ←→ Redis ←→ TaskIQ Worker (nouveau)
         ↓                           ↓
    Tâches legacy              Tâches migrées
```

### 2. Feature Flags par Tâche
```python
# .env
USE_TASKIQ_FOR_SCAN=false
USE_TASKIQ_FOR_METADATA=false
USE_TASKIQ_FOR_BATCH=false
USE_TASKIQ_FOR_INSERT=false
USE_TASKIQ_FOR_VECTORIZATION=false
ENABLE_CELERY_FALLBACK=true
```

### 3. Shadow Mode (Phase 2)
- Exécution simultanée Celery + TaskIQ
- Comparaison des résultats
- Logs différenciés `[CELERY]` vs `[TASKIQ]`

### 4. Tests de Non-Régression
- Avant chaque phase : baseline des tests existants
- Après chaque phase : comparaison des résultats
- Critère : 0 régression sur les tests existants

---

## 📊 Matrice de Suivi des Tests

| Phase | Tests Unitaires | Tests Intégration | Tests E2E | Régression |
|-------|----------------|-------------------|-----------|------------|
| 0 (Baseline) | ✅ 31 | ✅ 6 | ✅ 3 | N/A |
| 1 (Socle) | ✅ +3 | ✅ 0 | ✅ 0 | ✅ 0 |
| 2 (Pilote) | ✅ +2 | ✅ +1 | ✅ 0 | ✅ 0 |
| 3 (DB Direct) | ✅ +3 | ✅ +2 | ✅ 0 | ✅ 0 |
| 4 (Migration) | ✅ +10 | ✅ +6 | ✅ +3 | ✅ 0 |
| 5 (Décommission) | ✅ 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| 6 (Fusion) | ✅ 0 | ✅ 0 | ✅ 0 | ✅ 0 |

**Légende** : ✅ = Tests passent, +N = Nouveaux tests ajoutés

---

## 🔄 Workflow de Validation

### Pour Chaque Phase

1. **Développeur** :
   - Implémente les tâches de la phase
   - Exécute `ruff check` sur les fichiers modifiés
   - Vérifie l'absence d'erreurs Pylance dans VS Code
   - Exécute les tests unitaires localement
   - Commit atomique à la fin de chaque sous-tâche validée

2. **Testeur** :
   - Exécute `ruff check` sur tous les fichiers modifiés
   - Vérifie l'absence d'erreurs Pylance dans VS Code
   - Exécute les tests unitaires
   - Exécute les tests d'intégration
   - Compare avec la baseline
   - Documente les anomalies

3. **Lead Développeur** :
   - Exécute `ruff check` sur tous les fichiers modifiés
   - Vérifie l'absence d'erreurs Pylance dans VS Code
   - Revue les résultats
   - Valide ou demande des corrections
   - Crée un tag Git à la fin de chaque phase validée

---

## 📝 Règles de Commits

### Format
`<type>(scope): message court`

### Types Autorisés
- **feat** : ajout de fonctionnalité
- **fix** : correction de bug
- **refactor** : modification interne sans changement de comportement
- **style** : formatage, lint, renommages non fonctionnels
- **docs** : documentation uniquement
- **test** : ajout/modification de tests
- **chore** : tâches diverses (dépendances, scripts, CI, etc.)

### Exemples
```text
feat(taskiq): création configuration TaskIQ avec broker Redis
fix(taskiq): correction import manquant dans taskiq_app.py
test(taskiq): ajout tests unitaires configuration TaskIQ
docs(taskiq): mise à jour documentation phase 1
```

---

## 🚨 Procédure de Rollback

### Si Régression Détectée

1. **Immédiatement** :
   ```bash
   # Désactiver le feature flag
   export USE_TASKIQ_FOR_<TACHE>=false
   
   # Redémarrer les services
   docker-compose restart celery-worker taskiq-worker
   ```

2. **Investigation** :
   - Analyser les logs `[TASKIQ]` vs `[CELERY]`
   - Identifier la cause de la régression
   - Documenter dans `docs/plans/taskiq_migrations/incidents/`

3. **Correction** :
   - Corriger le code
   - Ajouter un test pour éviter la régression
   - Re-valider avant de réactiver le feature flag

---

## 📞 Contacts et Responsabilités

- **Lead Développeur** : Validation globale, revue de code
- **Développeur** : Implémentation des tâches
- **Testeur** : Validation des tests, détection des régressions
- **DevOps** : Configuration Docker, monitoring

---

## 🎯 Objectifs de Qualité

- **Zéro régression** sur les tests existants
- **Performance** : latence ≤ 110% de Celery
- **Mémoire** : consommation ≤ 100% de Celery
- **Fiabilité** : taux de succès ≥ 99%
- **Observabilité** : logs structurés et différenciés

---

*Dernière mise à jour : 2026-03-20*
*Version : 1.0*
*Statut : Phase 0 terminée, Phase 1 prête à démarrer*
