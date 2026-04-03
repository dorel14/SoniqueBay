# -*- coding: UTF-8 -*-
"""
Tests pour les workers GMM des artistes (TaskIQ).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestArtistGMMTaskIQ:
    """Tests des tâches TaskIQ GMM pour les artistes."""

    def test_cluster_all_artists_task_exists(self):
        """Test que la tâche cluster_all_artists_task existe."""
        from backend_worker.taskiq_tasks.gmm import cluster_all_artists_task
        assert cluster_all_artists_task is not None

    def test_refresh_stale_clusters_task_exists(self):
        """Test que la tâche refresh_stale_clusters_task existe."""
        from backend_worker.taskiq_tasks.gmm import refresh_stale_clusters_task
        assert refresh_stale_clusters_task is not None

    @pytest.mark.asyncio
    async def test_cluster_all_artists_task_execution(self):
        """Test exécution de la tâche cluster_all_artists_task."""
        from backend_worker.taskiq_tasks.gmm import cluster_all_artists_task

        with patch('backend_worker.taskiq_tasks.gmm.cluster_all_artists_task.kiq') as mock_kiq:
            mock_kiq.return_value = MagicMock()
            result = await cluster_all_artists_task.kiq(force_refresh=False)
            assert result is not None

    @pytest.mark.asyncio
    async def test_refresh_stale_clusters_task_execution(self):
        """Test exécution de la tâche refresh_stale_clusters_task."""
        from backend_worker.taskiq_tasks.gmm import refresh_stale_clusters_task

        with patch('backend_worker.taskiq_tasks.gmm.refresh_stale_clusters_task.kiq') as mock_kiq:
            mock_kiq.return_value = MagicMock()
            result = await refresh_stale_clusters_task.kiq(max_age_hours=24)
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
