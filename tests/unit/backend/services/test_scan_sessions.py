from sqlalchemy.orm import Session
from backend.api.models.scan_sessions_model import ScanSession
from backend.api.services.scan_service import ScanService

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
    mocker.patch('os.getenv', return_value='/music')

    # Mock celery task
    mock_task = mocker.MagicMock()
    mock_task.id = "test-task-id"
    mocker.patch('backend.api.utils.celery_app.celery.send_task', return_value=mock_task)

    # Mock database operations to avoid threading issues
    mock_session = mocker.MagicMock()
    mock_query = mocker.MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_query

    # Mock the ScanSession creation
    mock_scan_session = mocker.MagicMock()
    mock_scan_session.id = 1
    mock_scan_session.task_id = "test-task-id"
    mock_session.add = mocker.MagicMock()
    mock_session.commit = mocker.MagicMock()
    mock_session.refresh = mocker.MagicMock()

    result = ScanService.launch_scan("/test", mock_session)
    assert result is not None
    assert "task_id" in result
    assert result["task_id"] == "test-task-id"

def test_scan_service_prevent_duplicate(db_session: Session, mocker):
    """Test preventing duplicate active scans."""
    # Mock file system checks
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.listdir', return_value=[])
    mocker.patch('os.stat', return_value=mocker.MagicMock(st_mode=0o755))
    mocker.patch('os.getenv', return_value='/music')

    # Mock database operations
    mock_session = mocker.MagicMock()
    mock_query = mocker.MagicMock()

    # Mock existing session
    mock_existing_session = mocker.MagicMock()
    mock_existing_session.task_id = "existing-task-id"
    mock_query.filter.return_value.first.return_value = mock_existing_session
    mock_session.query.return_value = mock_query

    # Try to launch again
    result = ScanService.launch_scan("/test", mock_session)
    assert result is not None
    assert result["status"] == "Scan déjà en cours"