import pytest
import os
from unittest.mock import patch
from sqlalchemy.orm import Session
from backend.api.models.scan_sessions_model import ScanSession
from backend.services.scan_service import ScanService

def test_scan_session_creation(db_session: Session):
    """Test creation of scan session."""
    scan_session = ScanSession(directory="/test", status="running")
    db_session.add(scan_session)
    db_session.commit()
    db_session.refresh(scan_session)

    assert scan_session.id is not None
    assert scan_session.directory == "/test"
    assert scan_session.status == "running"

def test_scan_service_launch_scan(db_session: Session, mocker):
    """Test launching a scan creates a session."""
    # Mock file system checks
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.listdir', return_value=[])
    mocker.patch('os.stat', return_value=mocker.MagicMock(st_mode=0o755))

    # Mock celery task
    mock_task = mocker.MagicMock()
    mock_task.id = "test-task-id"
    mocker.patch('backend.services.scan_service.celery.send_task', return_value=mock_task)

    result = ScanService.launch_scan("/test", db_session)
    assert "task_id" in result
    assert result["task_id"] == "test-task-id"

    # Check session was created
    session = db_session.query(ScanSession).filter(ScanSession.directory == "/music/test").first()
    assert session is not None
    assert session.status == "running"
    assert session.task_id == "test-task-id"

def test_scan_service_prevent_duplicate(db_session: Session, mocker):
    """Test preventing duplicate active scans."""
    # Mock file system checks
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.listdir', return_value=[])
    mocker.patch('os.stat', return_value=mocker.MagicMock(st_mode=0o755))

    # Create existing session
    existing = ScanSession(directory="/music/test", status="running")
    db_session.add(existing)
    db_session.commit()

    # Try to launch again
    result = ScanService.launch_scan("/test", db_session)
    assert result["status"] == "Scan déjà en cours"