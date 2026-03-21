# Phase 1 — Briefing Testeur : Socle TaskIQ Minimal

## 📋 Résumé

**Phase** : 1 — Socle TaskIQ Minimal  
**Durée estimée** : 2-3 jours  
**Objectif** : Valider que TaskIQ s'initialise correctement sans impacter Celery  
**Statut** : 🚀 PRÊT À DÉMARRER

---

## 🎯 Contexte

La Phase 0 (Audit) est terminée. Nous avons :
- 31 tests unitaires worker documentés (baseline)
- 6 tests intégration workers documentés (baseline)
- Configuration Redis documentée

**Prochaine étape** : Valider que le socle TaskIQ fonctionne sans régression sur les tests existants.

---

## 🧪 Tests à Réaliser

### T1.6 : Tests unitaires TaskIQ
**Fichier** : `tests/unit/worker/test_taskiq_app.py`

**Tests créés** :
1. `test_taskiq_broker_initialization()` — Vérifie que le broker s'initialise
2. `test_taskiq_result_backend_initialization()` — Vérifie que le backend résultats s'initialise
3. `test_celery_still_works()` — Vérifie que Celery fonctionne toujours

**Validation** :
- [x] Les 3 tests passent
- [x] Les tests sont rapides (< 1s chacun)
- [x] Pas de dépendance externe (Redis, DB)

---

### T1.7 : Tests de non-régression
**Actions** :
```bash
# Tests TaskIQ
python -m pytest tests/unit/worker/test_taskiq_app.py -v

# Tests Celery existants (vérifier qu'ils passent toujours - échantillon)
python -m pytest tests/unit/worker/test_celery_simple.py -v

# Comparer avec baseline Phase 0
```

**Validation** :
- [x] Tests TaskIQ passent (3/3)
- [x] Tests Celery existants passent (1/1 échantillon)
- [x] Aucune régression détectée

---

## 🔍 Points de Vérification

### 1. Imports
- [ ] `from backend_worker.taskiq_app import broker` fonctionne
- [ ] `from backend_worker.taskiq_app import result_backend` fonctionne
- [ ] Pas d'erreur d'import Celery

### 2. Initialisation
- [ ] `broker.url` est défini (Redis DB 1)
- [ ] `result_backend` est défini
- [ ] Pas d'erreur de connexion Redis (en mode test)

### 3. Coexistence
- [ ] `from backend_worker.celery_app import celery` fonctionne toujours
- [ ] `celery.conf.broker_url` est défini (Redis DB 0)
- [ ] Pas de conflit entre les deux configurations

### 4. Logging
- [ ] Les logs `[TASKIQ]` sont visibles
- [ ] Les logs `[CELERY]` sont visibles
- [ ] Pas de mélange entre les deux

---

## 📊 Matrice de Tests

| Test | Type | Durée | Dépendances | Statut |
|------|------|-------|-------------|--------|
| `test_taskiq_broker_initialization` | Unitaire | < 1s | Aucune | ✅ |
| `test_taskiq_result_backend_initialization` | Unitaire | < 1s | Aucune | ✅ |
| `test_celery_still_works` | Unitaire | < 1s | Aucune | ✅ |
| Tests Celery existants (échantillon) | Unitaire | ~30s | Aucune | ✅ |

---

## 🚨 Procédure en Cas d'Échec

### Si un test TaskIQ échoue
1. **Identifier** : Quel test échoue ?
2. **Analyser** : Quelle est l'erreur ?
3. **Isoler** : Est-ce un problème d'import, d'initialisation ou de configuration ?
4. **Documenter** : Créer un rapport d'incident
5. **Corriger** : Demander une correction au développeur

### Si un test Celery échoue (régression)
1. **Arrêter** : Ne pas continuer la phase
2. **Identifier** : Quel test Celery échoue ?
3. **Analyser** : Est-ce lié aux changements TaskIQ ?
4. **Rollback** : Revenir à l'état avant les changements
5. **Documenter** : Créer un rapport d'incident critique

---

## 📝 Rapport de Tests

### Format du Rapport
```markdown
# Rapport de Tests Phase 1

## Résumé
- Date : [DATE]
- Testeur : [NOM]
- Phase : 1 (Socle TaskIQ Minimal)

## Tests TaskIQ
- [ ] test_taskiq_broker_initialization : [PASS/FAIL]
- [ ] test_taskiq_result_backend_initialization : [PASS/FAIL]
- [ ] test_celery_still_works : [PASS/FAIL]

## Tests Celery (Non-régression)
- Total : 31 tests
- Passés : [X]/31
- Échoués : [Y]/31
- Régression : [OUI/NON]

## Conclusion
- [ ] Phase 1 validée
- [ ] Phase 1 à corriger
- [ ] Phase 1 en échec critique (régression)

## Incidents
- [Liste des incidents rencontrés]
```

---

## ✅ Critères de Validation Phase 1

### Tests
- [ ] Tests unitaires TaskIQ passent (3/3)
- [ ] Tests unitaires Celery existants passent (31/31)
- [ ] Aucune régression détectée

### Performance
- [ ] Tests TaskIQ rapides (< 1s chacun)
- [ ] Tests Celery toujours aussi rapides
- [ ] Pas de dégradation des performances

### Documentation
- [ ] Rapport de tests créé
- [ ] Incidents documentés (si applicable)
- [ ] Baseline mise à jour (si nécessaire)

---

## 🔄 Prochaines Étapes

### Si Phase 1 Validée
- Passer à la Phase 2 (Migration Pilote)
- Créer le briefing testeur Phase 2

### Si Phase 1 à Corriger
- Demander les corrections au développeur
- Re-exécuter les tests après correction
- Valider à nouveau

### Si Phase 1 en Échec Critique
- Arrêter la migration
- Analyser la cause racine
- Revoir l'approche de migration

---

## 📞 Contacts

- **Lead Développeur** : Validation globale, revue de code
- **Développeur** : Corrections des erreurs identifiées

---

*Dernière mise à jour : 2026-03-20*
*Phase : 1 (Socle TaskIQ Minimal) — PRÊTE À DÉMARRER*
