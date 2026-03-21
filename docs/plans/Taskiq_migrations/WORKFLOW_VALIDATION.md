# Workflow de Validation — Migration Celery → TaskIQ

## 🎯 Objectif
Définir le processus de validation pour chaque phase de la migration, garantissant zéro régression.

---

## 🔄 Cycle de Validation par Phase

### 1. Préparation (Avant le Développement)

#### Actions du Lead Développeur
- [ ] Créer le briefing développeur pour la phase
- [ ] Créer le briefing testeur pour la phase
- [ ] Exécuter la baseline des tests existants
- [ ] Documenter la baseline dans `docs/plans/taskiq_migrations/phase_X/baseline.txt`

#### Actions du Développeur
- [ ] Lire le briefing développeur
- [ ] Comprendre les tâches à réaliser
- [ ] Préparer l'environnement de développement

#### Actions du Testeur
- [ ] Lire le briefing testeur
- [ ] Comprendre les critères d'acceptation
- [ ] Préparer l'environnement de test

---

### 2. Développement

#### Actions du Développeur
- [ ] Implémenter les tâches une par une
- [ ] **Exécuter ruff check** sur les fichiers modifiés
- [ ] **Vérifier l'absence d'erreurs Pylance** dans VS Code
- [ ] Exécuter les tests unitaires localement après chaque tâche
- [ ] **Commit atomique** après chaque sous-tâche validée
- [ ] Documenter les décisions techniques

#### Points de Contrôle
- [ ] Code respecte les conventions du projet (PEP8, type hints, docstrings)
- [ ] **Imports absolus** utilisés (backend_worker.xxx) - Conformément à AGENTS.md
- [ ] Logs utilisent le préfixe `[TASKIQ]` pour différencier de Celery
- [ ] Aucune modification des fichiers Celery existants (sauf feature flags)
- [ ] **Ruff check passe** sans erreur
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Tests unitaires passent localement
- [ ] **Commit atomique** avec message clair (format: `feat(taskiq): description`)

---

### 3. Validation par le Testeur

#### Actions du Testeur
- [ ] **Exécuter ruff check** sur tous les fichiers modifiés
- [ ] **Vérifier l'absence d'erreurs Pylance** dans VS Code
- [ ] Exécuter les tests unitaires TaskIQ
- [ ] Exécuter les tests unitaires Celery existants (non-régression)
- [ ] Exécuter les tests d'intégration workers existants (non-régression)
- [ ] Vérifier le démarrage Docker
- [ ] Documenter les résultats dans le rapport de tests
- [ ] **Vérifier que les imports sont absolus** (pas d'imports relatifs)

#### Critères de Validation
- [ ] Tous les tests unitaires TaskIQ passent
- [ ] Tous les tests unitaires Celery existants passent (0 régression)
- [ ] Tous les tests d'intégration workers existants passent (0 régression)
- [ ] Le worker TaskIQ démarre sans erreur
- [ ] Le worker Celery fonctionne toujours
- [ ] Les logs sont corrects et différenciés

#### Livrables du Testeur
- Rapport de tests complet
- Liste des anomalies détectées (si applicable)
- Recommandations

---

### 4. Validation par le Lead Développeur

#### Actions du Lead Développeur
- [ ] **Exécuter ruff check** sur tous les fichiers modifiés
- [ ] **Vérifier l'absence d'erreurs Pylance** dans VS Code
- [ ] Revue du code développé
- [ ] Revue du rapport de tests
- [ ] Validation des critères d'acceptation
- [ ] **Créer un tag Git** pour la phase validée (ex: `phase-1-complete`)
- [ ] Décision de passage à la phase suivante

#### Critères de Décision
- [ ] Code revu et approuvé
- [ ] Tests passent (0 régression)
- [ ] Documentation à jour
- [ ] Aucune anomalie bloquante

#### Livrables du Lead Développeur
- Validation de la phase
- Mise à jour du plan si nécessaire
- Communication de la décision

---

## 📊 Tableau de Bord de Suivi

### Phase 1 : Socle TaskIQ Minimal
| Tâche | Développeur | Testeur | Lead | Statut |
|-------|-------------|---------|------|--------|
| T1.1 : Dépendances | - | - | - | ⏳ |
| T1.2 : taskiq_app.py | - | - | - | ⏳ |
| T1.3 : taskiq_worker.py | - | - | - | ⏳ |
| T1.4 : docker-compose.yml | - | - | - | ⏳ |
| T1.5 : .env.example | - | - | - | ⏳ |
| T1.6 : Tests unitaires | - | - | - | ⏳ |
| T1.7 : Non-régression | - | - | - | ⏳ |
| T1.8 : Démarrage Docker | - | - | - | ⏳ |

**Légende** :
- ⏳ En attente
- 🔄 En cours
- ✅ Terminé
- ❌ Échoué
- ⚠️ Bloqué

---

## 🚨 Gestion des Anomalies

### Classification des Anomalies

#### Bloquante (Critique)
- Tests existants échouent après modification
- Worker TaskIQ ne démarre pas
- Worker Celery ne démarre pas
- Erreur fatale au démarrage Docker

**Action** : Arrêter le développement, corriger immédiatement

#### Majeure (Haute)
- Tests TaskIQ échouent
- Logs incorrects ou manquants
- Performance dégradée

**Action** : Corriger avant de continuer

#### Mineure (Moyenne)
- Documentation incomplète
- Logs non différenciés
- Code non optimisé

**Action** : Corriger dans la phase suivante

### Procédure de Correction

1. **Identifier l'anomalie**
   - Nom du test échoué
   - Message d'erreur
   - Fichier et ligne concernés

2. **Analyser la cause**
   - Lire le message d'erreur
   - Vérifier les logs
   - Identifier le code problématique

3. **Corriger l'anomalie**
   - Modifier le code
   - Exécuter les tests pour vérifier
   - Vérifier qu'aucune nouvelle régression n'est introduite

4. **Documenter l'anomalie**
   - Fichier : `docs/plans/taskiq_migrations/phase_X/anomalies.md`
   - Format :
     ```markdown
     ## Anomalie [NUMÉRO]
     - **Date** : [DATE]
     - **Phase** : [NUMÉRO PHASE]
     - **Test** : [NOM DU TEST]
     - **Erreur** : [MESSAGE D'ERREUR]
     - **Cause** : [ANALYSE]
     - **Solution** : [CORRECTION]
     - **Statut** : [OUVERT/CORRIGÉ]
     - **Validé par** : [NOM]
     ```

5. **Notifier l'équipe**
   - Informer le lead développeur
   - Mettre à jour le tableau de bord
   - Demander une revue si nécessaire

---

## 📝 Templates de Documents

### Template : Rapport de Tests
```markdown
# Rapport de Tests — Phase [NUMÉRO] : [NOM PHASE]

## Informations Générales
- **Date** : [DATE]
- **Testeur** : [NOM]
- **Phase** : [NUMÉRO] ([NOM PHASE])
- **Environnement** : [LOCAL/DOCKER]

## Résumé
- Tests exécutés : [NOMBRE]
- Tests réussis : [NOMBRE]
- Tests échoués : [NOMBRE]
- Taux de réussite : [POURCENTAGE]%

## Tests Unitaires TaskIQ
- Tests exécutés : [NOMBRE]
- Tests réussis : [NOMBRE]
- Tests échoués : [NOMBRE]
- Détails : [LIEN VERS FICHIER]

## Tests Unitaires Celery (Non-Régression)
- Tests exécutés : [NOMBRE]
- Tests réussis : [NOMBRE]
- Tests échoués : [NOMBRE]
- Régression : [OUI/NON]
- Détails : [LIEN VERS FICHIER]

## Tests d'Intégration Workers (Non-Régression)
- Tests exécutés : [NOMBRE]
- Tests réussis : [NOMBRE]
- Tests échoués : [NOMBRE]
- Régression : [OUI/NON]
- Détails : [LIEN VERS FICHIER]

## Démarrage Docker
- Construction images : [RÉUSSI/ÉCHOUÉ]
- Démarrage services : [RÉUSSI/ÉCHOUÉ]
- Logs TaskIQ : [OK/ERREUR]
- Logs Celery : [OK/ERREUR]
- Santé services : [OK/ERREUR]

## Anomalies Détectées
| # | Test | Erreur | Statut |
|---|------|--------|--------|
| 1 | [TEST] | [ERREUR] | [STATUT] |
| 2 | [TEST] | [ERREUR] | [STATUT] |

## Conclusion
- Phase validée : [OUI/NON]
- Prêt pour phase suivante : [OUI/NON]
- Recommandations : [LISTE]

## Signatures
- Testeur : [NOM] — [DATE]
- Lead Développeur : [NOM] — [DATE]
```

### Template : Rapport d'Anomalie
```markdown
# Rapport d'Anomalie — [NUMÉRO]

## Informations Générales
- **Date** : [DATE]
- **Phase** : [NUMÉRO] ([NOM PHASE])
- **Testeur** : [NOM]
- **Développeur** : [NOM]

## Description de l'Anomalie
- **Test échoué** : [NOM DU TEST]
- **Message d'erreur** : [MESSAGE COMPLET]
- **Fichier** : [CHEMIN FICHIER]
- **Ligne** : [NUMÉRO LIGNE]

## Analyse
- **Cause probable** : [ANALYSE]
- **Impact** : [BLOQUANT/MAJEUR/MINEUR]
- **Fréquence** : [SYSTÉMATIQUE/INTERMITTENT]

## Solution
- **Correction appliquée** : [DESCRIPTION]
- **Fichiers modifiés** : [LISTE]
- **Tests ajoutés** : [LISTE]

## Validation
- **Tests re-exécutés** : [OUI/NON]
- **Résultat** : [RÉUSSI/ÉCHOUÉ]
- **Régression introduite** : [OUI/NON]

## Statut
- **Statut** : [OUVERT/CORRIGÉ/FERMÉ]
- **Validé par** : [NOM]
- **Date de validation** : [DATE]
```

---

## 📅 Planning de Validation

### Phase 0 : Audit et Préparation
- **Durée** : 1-2 jours
- **Validation** : Lead Développeur
- **Livrables** : Matrice des tâches, baseline tests

### Phase 1 : Socle TaskIQ Minimal
- **Durée** : 2-3 jours
- **Validation** : Testeur + Lead Développeur
- **Livrables** : Worker TaskIQ opérationnel, tests passent

### Phase 2 : Migration Pilote
- **Durée** : 2-4 jours
- **Validation** : Testeur + Lead Développeur
- **Livrables** : Tâche pilote migrée, feature flag opérationnel

### Phase 3 : Accès DB Direct
- **Durée** : 3-5 jours
- **Validation** : Testeur + Lead Développeur
- **Livrables** : Couche DB worker, tests de performance

### Phase 4 : Migration Progressive
- **Durée** : 5-10 jours
- **Validation** : Testeur + Lead Développeur
- **Livrables** : >80% tâches migrées, tests passent

### Phase 5 : Décommission Celery
- **Durée** : 2-3 jours
- **Validation** : Testeur + Lead Développeur
- **Livrables** : Runtime unique TaskIQ, documentation à jour

---

## 🎯 Objectifs de Qualité

### Métriques de Suivi
- **Taux de réussite des tests** : ≥ 100%
- **Régressions introduites** : 0
- **Anomalies bloquantes** : 0
- **Performance** : ≤ 110% de Celery
- **Mémoire** : ≤ 100% de Celery

### Indicateurs de Succès
- [ ] Tous les tests passent à chaque phase
- [ ] Aucune régression introduite
- [ ] Documentation complète et à jour
- [ ] Code revu et approuvé
- [ ] Performance stable ou meilleure

---

## 📞 Contacts et Responsabilités

### Lead Développeur
- **Responsabilités** :
  - Validation globale
  - Revue de code
  - Décision de passage à la phase suivante
  - Communication avec l'équipe

- **Contact** : [EMAIL/SLACK]

### Développeur
- **Responsabilités** :
  - Implémentation des tâches
  - Tests unitaires locaux
  - Documentation technique
  - Correction des anomalies

- **Contact** : [EMAIL/SLACK]

### Testeur
- **Responsabilités** :
  - Validation des tests
  - Détection des régressions
  - Documentation des anomalies
  - Rapports de tests

- **Contact** : [EMAIL/SLACK]

---

*Dernière mise à jour : 2026-03-20*
*Version : 1.0*
*Statut : En cours de validation*
