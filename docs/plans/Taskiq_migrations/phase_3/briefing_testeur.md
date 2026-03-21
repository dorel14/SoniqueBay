# Briefing Testeur — Phase 3 : Accès DB Direct Worker

## 🎯 Objectif
Valider que l'accès DB direct fonctionne correctement et n'introduit aucune régression.

---

## 📋 Tâches à Réaliser

### T3.7 : Créer `tests/unit/worker/db/test_repositories.py`
**Fichier** : `tests/unit/worker/db/test_repositories.py` (nouveau)

**Contenu** :
```python
"""Tests unitaires pour les repositories workers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_track_repository_bulk_insert():
    """Test l'insertion en masse de tracks."""
    from backend_worker.db.repositories.track_repository import TrackRepository
    
    # Mock de la session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1,), (2,)]
    mock_session.execute.return_value = mock_result
    
    repo = TrackRepository(mock_session)
    tracks_data = [
        {"title": "Track 1", "path": "/path/1.mp3"},
        {"title": "Track 2", "path": "/path/2.mp3"}
    ]
    
    ids = await repo.bulk_insert_tracks(tracks_data)
    
    assert len(ids) == 2
    mock_session.execute.assert_called_once()
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les tests passent
- [ ] Les assertions sont correctes

---

### T3.8 : Créer `tests/integration/workers/test_taskiq_insert_integration.py`
**Fichier** : `tests/integration/workers/test_taskiq_insert_integration.py` (nouveau)

**Contenu** :
```python
"""Tests d'intégration pour l'insertion TaskIQ avec DB direct."""
import pytest

@pytest.mark.asyncio
async def test_insert_direct_batch_taskiq():
    """Test complet de l'insertion via TaskIQ."""
    # 1. Préparer les données de test
    # 2. Appeler la tâche TaskIQ
    # 3. Vérifier l'insertion en DB
    # 4. Vérifier les logs
    pass
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les tests passent
- [ ] Les assertions sont correctes

---

### T3.9 : Exécuter les tests de comparaison

**Étape 1 : Exécuter les tests unitaires TaskIQ**
```bash
python -m pytest tests/unit/worker/db/test_repositories.py -v
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
python -m pytest tests/unit/worker -q --tb=no > docs/plans/taskiq_migrations/phase_3/resultats_tests_unitaires.txt
python -m pytest tests/integration/workers -q --tb=no > docs/plans/taskiq_migrations/phase_3/resultats_tests_integration.txt

# Comparer avec la baseline
diff docs/plans/taskiq_migrations/audit/baseline_tests_unitaires.txt docs/plans/taskiq_migrations/phase_3/resultats_tests_unitaires.txt
diff docs/plans/taskiq_migrations/audit/baseline_tests_integration.txt docs/plans/taskiq_migrations/phase_3/resultats_tests_integration.txt
```

**Attendu** :
- Aucune différence (0 régression)

---

## 📊 Rapport de Tests

### Format du Rapport
```markdown
# Rapport de Tests — Phase 3 : Accès DB Direct Worker

## Résumé
- Date : [DATE]
- Testeur : [NOM]
- Phase : 3 (Accès DB Direct Worker)

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

## Accès DB Direct
- Insertion via API (fallback) : [RÉUSSI/ÉCHOUÉ]
- Insertion via DB direct : [RÉUSSI/ÉCHOUÉ]
- Timeouts respectés : [OUI/NON]
- Retries fonctionnels : [OUI/NON]

## Anomalies Détectées
- [DESCRIPTION ANOMALIE 1]
- [DESCRIPTION ANOMALIE 2]

## Conclusion
- Phase 3 validée : [OUI/NON]
- Prêt pour Phase 4 : [OUI/NON]
- Recommandations : [LISTE]
```

---

## ✅ Critères d'Acceptation

- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Les tests unitaires TaskIQ passent
- [ ] Les tests unitaires Celery existants passent (0 régression)
- [ ] Les tests d'intégration workers existants passent (0 régression)
- [ ] L'insertion DB direct fonctionne
- [ ] Les timeouts sont respectés
- [ ] Les retries fonctionnent
- [ ] Le rapport de tests est complet et documenté

---

## 🚨 Procédure en Cas de Régression

### Si un test existant échoue après ajout DB direct

1. **Identifier le test échoué**
   ```bash
   python -m pytest tests/unit/worker/test_<nom_test>.py -v
   ```

2. **Analyser l'erreur**
   - Vérifier si l'erreur est liée à l'accès DB
   - Vérifier si l'erreur est liée aux timeouts
   - Vérifier si l'erreur est liée aux retries

3. **Documenter l'anomalie**
   - Fichier : `docs/plans/taskiq_migrations/phase_3/anomalies.md`
   - Format :
     ```markdown
     ## Anomalie [NUMÉRO]
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
2. Vérifier la connexion DB : `docker exec soniquebay-postgres psql -U soniquebay -d soniquebay -c "SELECT 1;"`
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 3 (Accès DB Direct Worker)*
*Statut : En cours*
