# Briefing Testeur — Phase 2 : Migration Pilote

## 🎯 Objectif
Valider que la tâche maintenance migrée fonctionne correctement en mode Celery et TaskIQ.

---

## 📋 Tâches à Réaliser

### T2.6 : Créer les tests unitaires TaskIQ
**Fichier** : `tests/unit/worker/test_taskiq_maintenance.py` (nouveau)

**Contenu** :
```python
"""Tests unitaires pour la tâche maintenance migrée vers TaskIQ.

Vérifie que la tâche fonctionne correctement en mode Celery et TaskIQ.
"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock


def test_cleanup_old_data_taskiq():
    """Test que la tâche fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
    
    # Mock de la logique métier
    with patch('backend_worker.taskiq_tasks.maintenance.asyncio.sleep') as mock_sleep:
        mock_sleep.return_value = None
        
        # Test async
        import asyncio
        result = asyncio.run(cleanup_old_data_task(days_old=30))
        
        assert result["success"] is True
        assert result["days_old"] == 30


def test_cleanup_old_data_celery_fallback():
    """Test que le fallback Celery fonctionne."""
    import os
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'false'
    
    from backend_worker.celery_tasks import cleanup_old_data
    
    # Mock de la logique métier Celery
    with patch('backend_worker.celery_tasks.cleanup_old_data_impl') as mock_impl:
        mock_impl.return_value = {"cleaned": True, "days_old": 30}
        
        # Test que la tâche Celery est appelée
        result = cleanup_old_data(days_old=30)
        
        assert result["cleaned"] is True
        assert result["days_old"] == 30


def test_cleanup_old_data_taskiq_mode():
    """Test que la tâche fonctionne en mode TaskIQ."""
    import os
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    
    from backend_worker.celery_tasks import cleanup_old_data
    
    # Mock de la tâche TaskIQ
    with patch('backend_worker.taskiq_tasks.maintenance.cleanup_old_data_task') as mock_task:
        mock_task.return_value = AsyncMock(return_value={"cleaned": True, "days_old": 30})
        
        # Test que la tâche TaskIQ est appelée
        result = cleanup_old_data(days_old=30)
        
        assert result["cleaned"] is True
        assert result["days_old"] == 30


def test_feature_flag_default():
    """Test que le feature flag est désactivé par défaut."""
    import os
    # S'assurer que le flag est désactivé
    os.environ.pop('USE_TASKIQ_FOR_MAINTENANCE', None)
    
    from backend_worker.celery_tasks import USE_TASKIQ_FOR_MAINTENANCE
    
    assert USE_TASKIQ_FOR_MAINTENANCE is False


def test_feature_flag_enabled():
    """Test que le feature flag peut être activé."""
    import os
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    
    # Recharger le module pour prendre en compte le flag
    import importlib
    import backend_worker.celery_tasks
    importlib.reload(backend_worker.celery_tasks)
    
    from backend_worker.celery_tasks import USE_TASKIQ_FOR_MAINTENANCE
    
    assert USE_TASKIQ_FOR_MAINTENANCE is True
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les tests passent
- [ ] Les assertions sont correctes

---

### T2.7 : Créer les tests d'intégration TaskIQ
**Fichier** : `tests/integration/workers/test_taskiq_maintenance_integration.py` (nouveau)

**Contenu** :
```python
"""Tests d'intégration pour la maintenance TaskIQ.

Vérifie que la tâche fonctionne correctement dans un environnement Docker.
"""
import pytest
import os


@pytest.mark.asyncio
async def test_maintenance_taskiq_end_to_end():
    """Test complet de la tâche maintenance via TaskIQ."""
    # Note: Ce test nécessite un environnement Docker avec TaskIQ démarré
    
    # 1. Vérifier que le worker TaskIQ est démarré
    # 2. Envoyer la tâche via TaskIQ
    # 3. Vérifier le résultat
    # 4. Vérifier les logs
    
    # Pour l'instant, test simulé
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
    
    result = await cleanup_old_data_task(days_old=30)
    
    assert result["success"] is True
    assert result["days_old"] == 30


@pytest.mark.asyncio
async def test_maintenance_celery_fallback_end_to_end():
    """Test complet de la tâche maintenance via Celery (fallback)."""
    # Note: Ce test nécessite un environnement Docker avec Celery démarré
    
    # 1. Vérifier que le worker Celery est démarré
    # 2. Désactiver le feature flag
    # 3. Envoyer la tâche via Celery
    # 4. Vérifier le résultat
    # 5. Vérifier les logs
    
    # Pour l'instant, test simulé
    import os
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'false'
    
    from backend_worker.celery_tasks import cleanup_old_data
    
    result = cleanup_old_data(days_old=30)
    
    assert result["cleaned"] is True
    assert result["days_old"] == 30
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les tests passent
- [ ] Les assertions sont correctes

---

### T2.8 : Exécuter les vérifications de qualité de code

**Étape 1 : Exécuter ruff check sur les fichiers modifiés**
```bash
ruff check backend_worker/taskiq_tasks/ backend_worker/taskiq_utils.py backend_worker/celery_tasks.py
```

**Attendu** :
- Aucune erreur
- Aucun avertissement

**Étape 2 : Vérifier l'absence d'erreurs Pylance dans VS Code**
- Ouvrir les fichiers modifiés dans VS Code
- Vérifier la barre d'état en bas à droite
- S'assurer qu'aucune erreur rouge n'est affichée

**Attendu** :
- Aucune erreur Pylance
- Aucun problème de type ou d'import

---

### T2.9 : Exécuter les tests de comparaison

**Étape 1 : Exécuter les tests unitaires TaskIQ**
```bash
python -m pytest tests/unit/worker/test_taskiq_maintenance.py -v
```

**Attendu** :
- Tous les tests passent
- Aucune erreur d'import
- Aucune erreur d'exécution

**Étape 2 : Exécuter les tests unitaires Celery existants**
```bash
python -m pytest tests/unit/worker -q --tb=no
```

**Attendu** :
- Tous les tests passent (0 régression)
- Aucune erreur liée à TaskIQ

**Étape 3 : Exécuter les tests d'intégration workers**
```bash
python -m pytest tests/integration/workers -q --tb=no
```

**Attendu** :
- Tous les tests passent
- Aucune erreur liée à TaskIQ

**Étape 4 : Comparer avec la baseline**
```bash
# Sauvegarder les résultats
python -m pytest tests/unit/worker -q --tb=no > docs/plans/taskiq_migrations/phase_2/resultats_tests_unitaires.txt
python -m pytest tests/integration/workers -q --tb=no > docs/plans/taskiq_migrations/phase_2/resultats_tests_integration.txt

# Comparer avec la baseline
diff docs/plans/taskiq_migrations/audit/baseline_tests_unitaires.txt docs/plans/taskiq_migrations/phase_2/resultats_tests_unitaires.txt
diff docs/plans/taskiq_migrations/audit/baseline_tests_integration.txt docs/plans/taskiq_migrations/phase_2/resultats_tests_integration.txt
```

**Attendu** :
- Aucune différence (0 régression)

---

## 📊 Rapport de Tests

### Format du Rapport
```markdown
# Rapport de Tests — Phase 2 : Migration Pilote

## Informations Générales
- **Date** : [DATE]
- **Testeur** : [NOM]
- **Phase** : 2 (Migration Pilote)

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

## Tests de Feature Flag
- Mode Celery (flag=false) : [RÉUSSI/ÉCHOUÉ]
- Mode TaskIQ (flag=true) : [RÉUSSI/ÉCHOUÉ]
- Fallback Celery : [RÉUSSI/ÉCHOUÉ]

## Anomalies Détectées
| # | Test | Erreur | Statut |
|---|------|--------|--------|
| 1 | [TEST] | [ERREUR] | [STATUT] |
| 2 | [TEST] | [ERREUR] | [STATUT] |

## Conclusion
- Phase 2 validée : [OUI/NON]
- Prêt pour Phase 3 : [OUI/NON]
- Recommandations : [LISTE]

## Signatures
- Testeur : [NOM] — [DATE]
- Lead Développeur : [NOM] — [DATE]
```

---

## ✅ Critères d'Acceptation

- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Les tests unitaires TaskIQ passent
- [ ] Les tests unitaires Celery existants passent (0 régression)
- [ ] Les tests d'intégration workers existants passent (0 régression)
- [ ] La tâche fonctionne en mode Celery (flag=false)
- [ ] La tâche fonctionne en mode TaskIQ (flag=true)
- [ ] Le fallback vers Celery fonctionne
- [ ] Les logs sont différenciés
- [ ] Le rapport de tests est complet et documenté

---

## 🚨 Procédure en Cas de Régression

### Si un test existant échoue après migration

1. **Identifier le test échoué**
   ```bash
   python -m pytest tests/unit/worker/test_<nom_test>.py -v
   ```

2. **Analyser l'erreur**
   - Vérifier si l'erreur est liée à TaskIQ
   - Vérifier si l'erreur est liée au feature flag
   - Vérifier si l'erreur est liée au wrapper sync/async

3. **Documenter l'anomalie**
   - Fichier : `docs/plans/taskiq_migrations/phase_2/anomalies.md`
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
*Phase : 2 (Migration Pilote)*
*Statut : En cours*
