# Tickets Phase 5 — Nettoyage Tests Obsolètes

## [TICKET-P5-001] Supprimer test_celery_simple.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/unit/worker/test_celery_simple.py` teste l'import et la configuration Celery. Il doit être supprimé :
- Vérifier qu'aucun autre test ne l'importe
- Supprimer le fichier
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.05 jour

---

## [TICKET-P5-002] Supprimer test_celery_unified_config.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/unit/worker/test_celery_unified_config.py` teste la configuration Celery unifiée. Il doit être supprimé :
- Vérifier qu'aucun autre test ne l'importe
- Supprimer le fichier
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.05 jour

---

## [TICKET-P5-003] Supprimer test_celery_autoscale.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/unit/worker/test_celery_autoscale.py` teste l'auto-scaling Celery. Il doit être supprimé :
- Vérifier qu'aucun autre test ne l'importe
- Supprimer le fichier
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.05 jour
**Notes**: Ce fichier a déjà des erreurs LSP (`backend_worker.celery_app` introuvable)

---

## [TICKET-P5-004] Adapter test_artist_gmm_worker.py (mocks TaskIQ)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/unit/worker/test_artist_gmm_worker.py` mock `celery.send_task`. Remplacer par des mocks TaskIQ :
- Remplacer `mock_celery_send_task` par `mock_taskiq_kiq`
- Adapter les assertions pour TaskIQ
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.25 jour

---

## [TICKET-P5-005] Adapter test_taskiq_covers.py (supprimer fallback Celery)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/unit/worker/test_taskiq_covers.py` contient des tests de fallback Celery :
- `test_extract_embedded_covers_celery_fallback`
- `test_process_artist_images_celery_fallback`
- `test_process_album_covers_celery_fallback`

Supprimer ces tests car le fallback Celery n'existe plus.
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P5-006] Supprimer fixture mock_celery_task dans conftest.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/conftest.py` contient une fixture `mock_celery_task` (ligne 255). Supprimer ou renommer :
- Vérifier qu'aucun test n'utilise cette fixture
- Supprimer la fixture
- Ou renommer en `mock_taskiq_task` si elle est encore utile
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.05 jour

---

## [TICKET-P5-007] Adapter test_taskiq_maintenance.py (imports celery_tasks)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `tests/unit/worker/test_taskiq_maintenance.py` importe `backend_worker.celery_tasks` qui n'existe plus (erreurs LSP ligne 22 et 36). Corriger les imports :
- Remplacer `from backend_worker.celery_tasks import ...` par les imports TaskIQ corrects
- Adapter les tests pour TaskIQ
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour
**Notes**: Ce fichier a déjà des erreurs LSP

---

## [TICKET-P5-008] Vérifier couverture de tests post-nettoyage
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Après le nettoyage des tests, vérifier la couverture :
```powershell
python -m pytest tests/unit/worker -q --tb=no --cov=backend_worker --cov-report=term-missing
```
Identifier les zones non couvertes et créer des tickets pour les tests manquants.
**Dépendances**: Tous les tickets de cette phase
**Durée estimée**: 0.25 jour
