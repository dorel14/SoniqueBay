# tests/benchmark/conftest.py
"""
Configuration et fixtures communes pour les benchmarks.
"""
import pytest
import numpy as np
import tempfile
import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
os.environ['PYTHONPATH'] = str(root_dir)


@pytest.fixture(scope="session")
def benchmark_config():
    """Configuration commune pour tous les benchmarks."""
    return {
        "rounds": 5,
        "iterations": 10,
        "warmup_rounds": 2,
        "timer": "time.perf_counter",
        "disable_gc": True,
        "min_rounds": 3,
        "max_time": 10.0
    }


@pytest.fixture(scope="session")
def audio_sample_10s():
    """Génère un échantillon audio synthétique de 10 secondes."""

    # Paramètres audio
    sr = 22050  # Sample rate standard
    duration = 10  # 10 secondes
    frequency = 440  # 440 Hz (La)

    # Générer un signal sinusoïdal simple
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)

    # Ajouter un peu de bruit pour réalisme
    noise = 0.01 * np.random.normal(0, 1, len(audio))
    audio = audio + noise

    return audio.astype(np.float32), sr


@pytest.fixture(scope="session")
def audio_sample_30s():
    """Génère un échantillon audio synthétique de 30 secondes."""

    sr = 22050
    duration = 30
    frequency = 440

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)

    # Ajouter plus de complexité
    audio2 = 0.3 * np.sin(2 * np.pi * 880 * t)  # Harmonique
    noise = 0.02 * np.random.normal(0, 1, len(audio))

    audio = audio + audio2 + noise

    return audio.astype(np.float32), sr


@pytest.fixture(scope="session")
def audio_sample_60s():
    """Génère un échantillon audio synthétique de 60 secondes."""

    sr = 22050
    duration = 60
    frequency = 440

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Signal plus complexe avec plusieurs fréquences
    audio1 = 0.4 * np.sin(2 * np.pi * frequency * t)
    audio2 = 0.2 * np.sin(2 * np.pi * 880 * t)
    audio3 = 0.1 * np.sin(2 * np.pi * 1320 * t)  # Troisième harmonique

    # Ajouter du bruit et une enveloppe
    noise = 0.03 * np.random.normal(0, 1, len(audio1))
    envelope = np.exp(-t / duration)  # Décroissance exponentielle

    audio = (audio1 + audio2 + audio3) * envelope + noise

    return audio.astype(np.float32), sr


@pytest.fixture
def temp_audio_file(audio_sample_30s):
    """Crée un fichier audio temporaire WAV."""
    import soundfile as sf

    audio, sr = audio_sample_30s

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, audio, sr)
        yield tmp_file.name

    # Nettoyage
    try:
        os.unlink(tmp_file.name)
    except (OSError, PermissionError):
        pass


@pytest.fixture
def temp_audio_files_10(audio_sample_10s):
    """Crée 10 fichiers audio temporaires."""
    import soundfile as sf

    audio, sr = audio_sample_10s
    files = []

    for i in range(10):
        with tempfile.NamedTemporaryFile(suffix=f'_{i}.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, audio, sr)
            files.append(tmp_file.name)

    yield files

    # Nettoyage
    for file_path in files:
        try:
            os.unlink(file_path)
        except (OSError, PermissionError):
            pass


@pytest.fixture
def temp_audio_files_20(audio_sample_10s):
    """Crée 20 fichiers audio temporaires."""
    import soundfile as sf

    audio, sr = audio_sample_10s
    files = []

    for i in range(20):
        with tempfile.NamedTemporaryFile(suffix=f'_{i}.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, audio, sr)
            files.append(tmp_file.name)

    yield files

    # Nettoyage
    for file_path in files:
        try:
            os.unlink(file_path)
        except (OSError, PermissionError):
            pass


@pytest.fixture
def sample_acoustid_tags():
    """Tags AcoustID d'exemple pour les benchmarks."""
    return {
        'ab:lo:rhythm:bpm': ['120.5'],
        'ab:lo:tonal:key_key': ['C'],
        'ab:lo:tonal:key_scale': ['major'],
        'ab:hi:danceability:danceable': ['0.85'],
        'ab:hi:mood_happy:happy': ['0.72'],
        'ab:hi:mood_aggressive:aggressive': ['0.15'],
        'ab:hi:mood_party:party': ['0.68'],
        'ab:hi:mood_relaxed:relaxed': ['0.45'],
        'ab:hi:voice_instrumental:instrumental': ['0.12'],
        'ab:hi:mood_acoustic:acoustic': ['0.25'],
        'ab:hi:tonal_atonal:tonal': ['0.88'],
        'ab:genre:electronic': ['electronic', 'house', 'techno'],
        'ab:mood:energetic': ['energetic', 'upbeat']
    }


@pytest.fixture
def benchmark_db_session(test_db_engine):
    """Session de base de données pour les benchmarks."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def benchmark_client(benchmark_db_session):
    """Client FastAPI pour les benchmarks."""
    from backend.api_app import create_api
    from backend.utils.database import get_db, get_session
    from fastapi.testclient import TestClient

    app = create_api()

    def override_get_db():
        try:
            yield benchmark_db_session
        finally:
            pass

    def override_get_session():
        try:
            yield benchmark_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client