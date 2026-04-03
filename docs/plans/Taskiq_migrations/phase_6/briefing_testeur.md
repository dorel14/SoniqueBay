# Briefing Testeur — Phase 6 : Fusion Backend / Backend Worker

## 🎯 Objectif
Valider que la fusion des répertoires `backend/` et `backend_worker/` n'introduit aucune régression et que toutes les fonctionnalités sont préservées.

---

## 📋 Tâches à Réaliser

### T6.9 : Exécuter la suite complète de tests

**Commande** :
```bash
python -m pytest tests/ -q --tb=no
```

**Attendu** :
- Tous les tests passent
- Aucune régression introduite
- Le nombre de tests est identique ou supérieur à la baseline

---

### T6.10 : Vérifier qu'aucun import `backend_worker` ne reste

**Commande** :
```bash
grep -r "from backend_worker" backend/ tests/ || echo "Aucun import backend_worker trouvé"
grep -r "import backend_worker" backend/ tests/ || echo "Aucun import backend_worker trouvé"
```

**Attendu** :
- Aucun import `backend_worker` trouvé
- Tous les imports pointent vers `backend/`

---

### T6.11 : Vérifier que Docker démarre correctement

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
- Aucune erreur liée à la fusion

---

### T6.12 : Vérifier que toutes les tâches TaskIQ fonctionnent

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

### T6.13 : Vérifier la structure des répertoires

**Actions** :
1. Vérifier que `backend/tasks/` existe et contient les tâches
2. Vérifier que `backend/workers/` existe et contient les workers
3. Vérifier que `backend/models/` existe et contient les modèles
4. Vérifier que `backend/services/` contient les services fusionnés
5. Vérifier que `backend_worker/` n'existe plus

**Commandes** :
```bash
# Vérifier la structure
ls -la backend/tasks/
ls -la backend/workers/
ls -la backend/models/
ls -la backend/services/

# Vérifier que backend_worker/ n'existe plus
ls -la backend_worker/ || echo "backend_worker/ supprimé avec succès"
```

**Attendu** :
- Tous les répertoires cibles existent
- `backend_worker/` n'existe plus

---

### T6.14 : Vérifier les imports dans les tests

**Actions** :
1. Vérifier que tous les tests utilisent les imports `backend.*`
2. Vérifier qu'aucun test n'utilise `backend_worker.*`

**Commande** :
```bash
grep -r "from backend_worker" tests/ || echo "Aucun import backend_worker dans les tests"
grep -r "import backend_worker" tests/ || echo "Aucun import backend_worker dans les tests"
```

**Attendu** :
- Aucun import `backend_worker` dans les tests

---

## 📊 Rapport de Tests

### Format du Rapport
```markdown
# Rapport de Tests — Phase 6 : Fusion Backend / Backend Worker

## Informations Générales
- **Date** : [DATE]
- **Testeur** : [NOM]
- **Phase** : 6 (Fusion Backend / Backend Worker)

## Tests Complets
- Tests exécutés : [NOMBRE]
- Tests réussis : [NOMBRE]
- Tests échoués : [NOMBRE]
- Taux de réussite : [POURCENTAGE]%

## Vérification Imports
- Imports backend_worker restants : [NOMBRE]
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

## Structure des Répertoires
- backend/tasks/ : [EXISTE/ABSENT]
- backend/workers/ : [EXISTE/ABSENT]
- backend/models/ : [EXISTE/ABSENT]
- backend/services/ : [EXISTE/ABSENT]
- backend_worker/ : [SUPPRIMÉ/PRÉSENT]

## Anomalies Détectées
| # | Test | Erreur | Statut |
|---|------|--------|--------|
| 1 | [TEST] | [ERREUR] | [STATUT] |
| 2 | [TEST] | [ERREUR] | [STATUT] |

## Conclusion
- Phase 6 validée : [OUI/NON]
- Prêt pour production : [OUI/NON]
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
- [ ] Aucun import `backend_worker` ne reste
- [ ] `docker-compose up` démarre avec la nouvelle structure
- [ ] Toutes les tâches TaskIQ fonctionnent
- [ ] Les logs sont corrects et différenciés
- [ ] La structure des répertoires est correcte
- [ ] Le rapport de tests est complet et documenté

---

## 🚨 Procédure en Cas de Régression

### Si un test existant échoue après fusion

1. **Identifier le test échoué**
   ```bash
   python -m pytest tests/unit/test_<nom_test>.py -v
   ```

2. **Analyser l'erreur**
   - Vérifier si l'erreur est liée à un import manquant
   - Vérifier si l'erreur est liée à un service dupliqué
   - Vérifier si l'erreur est liée à la structure des répertoires

3. **Documenter l'anomalie**
   - Fichier : `docs/plans/taskiq_migrations/phase_6/anomalies.md`
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
*Phase : 6 (Fusion Backend / Backend Worker)*
*Statut : En cours*
