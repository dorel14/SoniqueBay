"""Tests unitaires pour le worker TaskIQ.

Vérifie que le worker TaskIQ est fonctionnel et importable.
"""
import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))


@pytest.mark.asyncio
async def test_taskiq_worker_importable():
    """Test that taskiq_worker module is importable."""
    try:
        from backend_worker.taskiq_worker import main
        assert callable(main), "main should be callable"
    except Exception as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.asyncio
async def test_broker_importable():
    """Test that broker is importable and configured."""
    try:
        from backend_worker.taskiq_app import broker
        assert hasattr(broker, "listen"), "Broker should have listen method"
        assert hasattr(broker, "startup"), "Broker should have startup method"
        assert hasattr(broker, "shutdown"), "Broker should have shutdown method"
    except Exception as e:
        pytest.fail(f"Broker import failed: {e}")


@pytest.mark.asyncio
async def test_run_receiver_task_importable():
    """Test that run_receiver_task is importable."""
    try:
        from taskiq.api import run_receiver_task
        assert callable(run_receiver_task), "run_receiver_task should be callable"
    except Exception as e:
        pytest.fail(f"run_receiver_task import failed: {e}")
