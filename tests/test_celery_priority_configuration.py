#!/usr/bin/env python3
"""
Test pour vérifier la configuration de priorisation des queues Celery.
Ce test vérifie que les priorités des queues sont correctement configurées
pour donner la priorité aux scans complets sur les tâches deferred.
"""

from backend_worker.celery_app import celery, task_queues, task_routes

def test_celery_priority_configuration():
    """Test que la configuration des priorités Celery est correcte."""

    # Vérifier que les queues ont des priorités définies
    assert 'scan' in task_queues
    assert 'deferred' in task_queues
    assert 'deferred_vectors' in task_queues
    assert 'deferred_covers' in task_queues
    assert 'deferred_enrichment' in task_queues

    # Vérifier que les priorités sont correctement configurées
    # scan devrait avoir la priorité la plus élevée (0)
    assert task_queues['scan']['priority'] == 0

    # Les queues deferred devraient avoir des priorités plus basses
    assert task_queues['deferred']['priority'] == 9
    assert task_queues['deferred_vectors']['priority'] == 6
    assert task_queues['deferred_covers']['priority'] == 7
    assert task_queues['deferred_enrichment']['priority'] == 8

    # Vérifier que les priorités sont dans le bon ordre
    # Plus le nombre est bas, plus la priorité est élevée
    assert task_queues['scan']['priority'] < task_queues['extract']['priority']
    assert task_queues['extract']['priority'] < task_queues['deferred_vectors']['priority']
    assert task_queues['deferred_vectors']['priority'] < task_queues['deferred']['priority']

    print("✅ Configuration des priorités Celery validée avec succès !")

def test_celery_app_priority_settings():
    """Test que l'application Celery a les paramètres de priorité corrects."""

    # Vérifier que les paramètres de priorité sont configurés dans l'app Celery
    assert hasattr(celery.conf, 'task_queue_priority_enabled')
    assert celery.conf.task_queue_priority_enabled is True

    assert hasattr(celery.conf, 'task_queue_priority')
    assert isinstance(celery.conf.task_queue_priority, dict)

    # Vérifier que les priorités dans la configuration Celery correspondent
    # aux priorités définies dans task_queues
    assert celery.conf.task_queue_priority['scan'] == task_queues['scan']['priority']
    assert celery.conf.task_queue_priority['deferred'] == task_queues['deferred']['priority']

    print("✅ Paramètres de priorité Celery validés avec succès !")

def test_task_routing_priority():
    """Test que le routage des tâches respecte les priorités."""

    # Vérifier que les tâches de scan sont routées vers la queue scan (haute priorité)
    assert 'scan.discovery' in task_routes
    assert task_routes['scan.discovery']['queue'] == 'scan'

    # Vérifier que les tâches deferred sont routées vers les queues deferred (basse priorité)
    assert 'worker_deferred_enrichment.*' in task_routes
    assert task_routes['worker_deferred_enrichment.*']['queue'] == 'deferred'

    print("✅ Routage des tâches avec priorités validé avec succès !")

if __name__ == "__main__":
    test_celery_priority_configuration()
    test_celery_app_priority_settings()
    test_task_routing_priority()
    print("🎉 Tous les tests de priorisation Celery ont passé avec succès !")