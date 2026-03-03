"""
Tests pour le service d'optimisation du scan.

Ce module teste les fonctions d'optimisation du scan de fichiers audio.
"""
import time

from backend_worker.services.scan_optimizer import ScanMetrics, ScanOptimizer


def test_scan_optimizer_initialization():
    """Test l'initialisation de ScanOptimizer."""
    optimizer = ScanOptimizer()
    
    assert optimizer is not None
    assert optimizer.logger is not None


def test_scan_metrics_initialization():
    """Test l'initialisation de ScanMetrics."""
    metrics = ScanMetrics()
    
    assert metrics.files_processed == 0
    assert metrics.chunks_processed == 0
    assert metrics.processing_time == 0.0
    assert metrics.errors_count == 0
    assert metrics.files_per_second == 0.0
    assert metrics.avg_chunk_time == 0.0


def test_scan_metrics_update():
    """Test la mise à jour des métriques."""
    metrics = ScanMetrics()
    metrics.files_processed = 100
    metrics.chunks_processed = 5
    metrics.processing_time = 25.0
    
    # Simuler du temps écoulé
    metrics.start_time = time.time() - 25.0
    
    metrics.update()
    
    assert metrics.files_per_second == 4.0  # 100 / 25
    assert metrics.avg_chunk_time == 5.0   # 25 / 5


def test_process_audio_for_storage():
    """Test le traitement audio pour le stockage."""
    optimizer = ScanOptimizer()
    
    file_path = "/path/to/track.mp3"
    metadata = {
        'id': 123,
        'tags': {'title': 'Test Track', 'artist': 'Test Artist'},
        'other_field': 'value'
    }
    
    result = optimizer.process_audio_for_storage(file_path, metadata)
    
    assert result['track_id'] == 123
    assert result['file_path'] == file_path
    assert result['tags'] == metadata['tags']
    assert result['metadata'] == metadata


def test_optimize_batch():
    """Test l'optimisation d'un batch."""
    optimizer = ScanOptimizer()
    
    files = ['/path/1.mp3', '/path/2.mp3', '/path/3.mp3']
    
    result = optimizer.optimize_batch(files)
    
    assert result == files  # Par défaut, retourne les fichiers tels quels


def test_scan_metrics_with_zero_chunks():
    """Test les métriques avec zéro chunks."""
    metrics = ScanMetrics()
    metrics.files_processed = 50
    metrics.chunks_processed = 0
    metrics.processing_time = 10.0
    
    metrics.update()
    
    # avg_chunk_time devrait rester 0.0 car pas de chunks
    assert metrics.avg_chunk_time == 0.0
    assert metrics.files_per_second > 0  # Mais files_per_second devrait être calculé
