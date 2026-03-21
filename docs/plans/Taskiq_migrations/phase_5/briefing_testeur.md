# Briefing Testeur — Phase 5 : Décommission Celery

## 🎯 Objectif
Valider que la suppression de Celery n'introduit aucune régression et que toutes les fonctionnalités sont préservées.

---

## 📋 Tâches à Réaliser

### T5.7 : Exécuter la suite complète de tests

**Commande** :
```bash
python -m pytest tests/ -q --tb=no
```

**Attendu** :
- Tous les tests passent
- Aucune régression introduite
- Le nombre de tests est identique ou supérieur à la baseline

---

### T5.8 : Vérifier qu'aucun import Celery ne reste

**Commande** :
```bash
grep -r "from celery" backend/ backend_worker/ || echo "Aucun import Celery trouvé"
```

**Attendu** :
- Aucun import Celery trouvé
- Tous les imports pointent vers TaskIQ

---

### T5.9 : Vérifier que Docker démarre correctement

**Étape 1 : Construire les images**
```bash
docker-compose build
```

**Attendu** :
- Construction réussie
- Aucune erreur de dépendance

**Étape 2 : Démarrer les services**
```bash
docker-compose up -d
```

**Attendu** :
- Tous les services démarrent
- Aucune erreur de démarrage

**Étape 3 : Vérifier la santé des services**
```bash
docker-compose ps
```

**Attendu** :
- Tous les services sont "Up"
- Aucun service en "Exit" ou "Restarting"

**Étape 4 : Vérifier les logs TaskIQ**
```bash
docker logs soniquebay-taskiq-worker
```

**Attendu** :
- Logs visibles avec préfixe `[TASKIQ]`
- Aucune erreur fatale
- Message "Broker démarré, écoute des tâches..."

**Étape 5 : Vérifier les logs API**
```bash
docker logs soniquebay-api
```

**Attendu** :
- Logs normaux
- Aucune erreur liée à la suppression de Celery

---

### T5.10 : Vérifier que toutes les tâches TaskIQ fonctionnent

**Actions** :
1. Tester chaque tâche migrée
2. Vérifier les logs
3. Valider les résultats

**Tâches à tester** :
- [ ] `scan.discovery`
- [ ] `metadata.extract_batch`
- [ ] `batch.process_entities`
- [ ] `insert.direct_batch`
- [ ] `vectorization.calculate`
- [ ] `covers.extract_embedded`
- [ ] `maintenance.cleanup_old_data`

**Pour chaque tâche** :
1. Envoyer la tâche via l'API ou directement
2. Vérifier que la tâche est reçue par le worker
3. Vérifier que la tâche s'exécute correctement
4. Vérifier les logs avec préfixe `[TASKIQ]`
5. Valider le résultat

---

### T5.11 : Vérifier que le scheduler TaskIQ fonctionne

**Actions** :
1. Vérifier que les tâches planifiées sont exécutées
2. Vérifier les logs du scheduler
3. Valider les résultats

**Commandes** :
```bash
# Vérifier les logs du scheduler
docker logs soniquebay-taskiq-worker | grep -i "scheduler"

# Vérifier que les tâches planifiées sont exécutées
docker logs soniquebay-taskiq-worker | grep -i "scheduled"
```

**Attendu** :
- Le scheduler fonctionne
- Les tâches planifiées sont exécutées
- Les logs sont corrects

---

## 📊 Rapport de Tests

### Format du Rapport
```markdown
# Rapport de Tests — Phase 5 : Décommission Celery

## Informations Générales
- **Date** : [DATE]
- **Testeur** : [NOM]
- **Phase** : 5 (Décommission Celery)

## Tests Complets
- Tests exécutés : [NOMBRE]
- Tests réussis : [NOMBRE]
- Tests échoués : [NOMBRE]
- Taux de réussite : [POURCENTAGE]%

## Vérification Imports
- Imports Celery restants : [NOMBRE]
- Détails : [LISTE]

## Démarrage Docker
- Construction images : [RÉUSSI/ÉCHOUÉ]
- Démarrage services : [RÉUSSI/ÉCHOUÉ]
- Logs TaskIQ : [OK/ERREUR]
- Logs API : [OK/ERREUR]
- Santé services : [OK/ERREUR]

## Tâches TaskIQ
| Tâche | Fonctionnelle | Logs | Résultat |
|-------|---------------|------|----------|
| scan.discovery | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |
| metadata.extract_batch | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |
| batch.process_entities | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |
| insert.direct_batch | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |
| vectorization.calculate | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |
| covers.extract_embedded | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |
| maintenance.cleanup_old_data | [OUI/NON] | [OK/ERREUR] | [VALIDE/INVALIDE] |

## Scheduler TaskIQ
- Scheduler fonctionnel : [OUI/NON]
- Tâches planifiées exécutées : [OUI/NON]
- Logs scheduler : [OK/ERREUR]

## Anomalies Détectées
| # | Test | Erreur | Statut |
|---|------|--------|--------|
| 1 | [TEST] | [ERREUR] | [STATUT] |
| 2 | [TEST] | [ERREUR] | [STATUT] |

## Conclusion
- Phase 5 validée : [OUI/NON]
- Prêt pour Phase 6 : [OUI/NON]
- Recommandations : [LISTE]

## Signatures
- Testeur : [NOM] — [DATE]
- Lead Développeur : [NOM] — [DATE]
```

---

## ✅ Critères d'Acceptation

- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Tous les tests passent
- [ ] Aucun import Celery ne reste
- [ ] `docker-compose up` démarre sans Celery
- [ ] Toutes les tâches TaskIQ fonctionnent
- [ ] Le scheduler TaskIQ fonctionne
- [ ] Les logs sont corrects et différenciés
- [ ] Le rapport de tests est complet et documenté

---

## 🚨 Procédure en Cas de Régression

### Si un test existant échoue après suppression de Celery

1. **Identifier le test échoué**
   ```bash
   python -m pytest tests/unit/test_<nom_test>.py -v
   ```

2. **Analyser l'erreur**
   - Vérifier si l'erreur est liée à un import manquant
   - Vérifier si l'erreur est liée à la suppression de Celery
   - Vérifier si l'erreur est liée au scheduler

3. **Documenter l'anomalie**
   - Fichier : `docs/plans/taskiq_migrations/phase_5/anomalies.md`
   - Format :
     ```markdown
     ## Anomalie [NUMÉRO]
     - **Date** : [DATE]
     - **Test** : [NOM DU TEST]
     - **Erreur** : [MESSAGE D'ERREUR]
     - **Cause probable** : [ANALYSE]
     - **Solution** : [CORRECTION APPLIQUÉE]
     - **Statut** : [OUVERT/CORRIGÉ]
     ```

4. **Corriger l'anomalie**
   - Modifier le code si nécessaire
   - Re-exécuter les tests
   - Vérifier que la correction ne crée pas de nouvelle régression

5. **Notifier le lead développeur**
   - Fournir le rapport d'anomalie
   - Demander une revue de code si nécessaire

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
