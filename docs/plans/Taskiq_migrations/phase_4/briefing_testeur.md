# Briefing Testeur — Phase 4 : Migration Progressive du Cœur

## 🎯 Objectif
Valider que chaque lot de tâches migrées fonctionne correctement et n'introduit aucune régression.

---

## 📋 Tâches à Réaliser

### Pour Chaque Lot Migré

#### Tâches Testeur

**1. Créer les tests unitaires**

Exemple pour le Lot 1 (maintenance) :
```python
# tests/unit/worker/test_taskiq_maintenance.py
import pytest
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

**2. Créer les tests d'intégration**

```python
# tests/integration/workers/test_taskiq_<module>_integration.py
import pytest

@pytest.mark.asyncio
async def test_<module>_taskiq_end_to_end():
    """Test complet de la tâche <module> via TaskIQ."""
    # 1. Démarrer le worker TaskIQ
    # 2. Envoyer la tâche
    # 3. Vérifier le résultat
    # 4. Vérifier les logs
    pass

@pytest.mark.asyncio
async def test_<module>_celery_fallback_end_to_end():
    """Test complet de la tâche <module> via Celery (fallback)."""
    # 1. Désactiver le feature flag
    # 2. Envoyer la tâche via Celery
    # 3. Vérifier le résultat
    # 4. Vérifier les logs
    pass
```

**3. Exécuter les tests de comparaison**

```bash
# Mode Celery
USE_TASKIQ_FOR_<MODULE>=false python -m pytest tests/unit/worker/test_taskiq_<module>.py -v

# Mode TaskIQ
USE_TASKIQ_FOR_<MODULE>=true python -m pytest tests/unit/worker/test_taskiq_<module>.py -v

# Comparer les résultats
```

---

### Liste des Tests à Créer par Lot

#### Lot 1 : Maintenance
- [ ] `tests/unit/worker/test_taskiq_maintenance.py`
- [ ] `tests/integration/workers/test_taskiq_maintenance_integration.py`

#### Lot 2 : Covers
- [ ] `tests/unit/worker/test_taskiq_covers.py`
- [ ] `tests/integration/workers/test_taskiq_covers_integration.py`

#### Lot 3 : Metadata
- [ ] `tests/unit/worker/test_taskiq_metadata.py`
- [ ] `tests/integration/workers/test_taskiq_metadata_integration.py`

#### Lot 4 : Batch + Insert
- [ ] `tests/unit/worker/test_taskiq_batch.py`
- [ ] `tests/unit/worker/test_taskiq_insert.py`
- [ ] `tests/integration/workers/test_taskiq_batch_integration.py`
- [ ] `tests/integration/workers/test_taskiq_insert_integration.py`

#### Lot 5 : Scan
- [ ] `tests/unit/worker/test_taskiq_scan.py`
- [ ] `tests/integration/workers/test_taskiq_scan_integration.py`

#### Lot 6 : Vectorization
- [ ] `tests/unit/worker/test_taskiq_vectorization.py`
- [ ] `tests/integration/workers/test_taskiq_vectorization_integration.py`

---

## 📊 Rapport de Tests

### Format du Rapport
```markdown
# Rapport de Tests — Phase 4 : Migration Progressive du Cœur

## Résumé
- Date : [DATE]
- Testeur : [NOM]
- Phase : 4 (Migration Progressive du Cœur)
- Lot : [NUMÉRO LOT]

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
- Lot validé : [OUI/NON]
- Prêt pour lot suivant : [OUI/NON]
- Recommandations : [LISTE]

## Signatures
- Testeur : [NOM] — [DATE]
- Lead Développeur : [NOM] — [DATE]
```

---

## ✅ Critères d'Acceptation

Pour chaque lot migré :

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

### Si un test existant échoue après migration d'un lot

1. **Identifier le test échoué**
   ```bash
   python -m pytest tests/unit/worker/test_<nom_test>.py -v
   ```

2. **Analyser l'erreur**
   - Vérifier si l'erreur est liée à TaskIQ
   - Vérifier si l'erreur est liée au feature flag
   - Vérifier si l'erreur est liée au wrapper sync/async

3. **Documenter l'anomalie**
   - Fichier : `docs/plans/taskiq_migrations/phase_4/anomalies.md`
   - Format :
     ```markdown
     ## Anomalie [NUMÉRO]
     - **Date** : [DATE]
     - **Lot** : [NUMÉRO LOT]
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
*Phase : 4 (Migration Progressive du Cœur)*
*Statut : En cours*
