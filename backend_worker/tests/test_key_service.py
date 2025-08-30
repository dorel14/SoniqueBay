import pytest
from backend_worker.services.key_service import key_to_camelot, CAMELOT_MAP

def test_key_to_camelot_major_keys():
    """Test la conversion des clés majeures en notation Camelot."""
    assert key_to_camelot("C", "major") == "8B"
    assert key_to_camelot("G", "major") == "9B"
    assert key_to_camelot("D", "major") == "10B"
    assert key_to_camelot("A", "major") == "11B"
    assert key_to_camelot("E", "major") == "12B"
    assert key_to_camelot("B", "major") == "1B"
    assert key_to_camelot("F#", "major") == "2B"
    assert key_to_camelot("C#", "major") == "3B"
    assert key_to_camelot("G#", "major") == "4B"
    assert key_to_camelot("D#", "major") == "5B"
    assert key_to_camelot("A#", "major") == "6B"
    assert key_to_camelot("F", "major") == "7B"

def test_key_to_camelot_minor_keys():
    """Test la conversion des clés mineures en notation Camelot."""
    assert key_to_camelot("Am", "minor") == "8A"
    assert key_to_camelot("Em", "minor") == "9A"
    assert key_to_camelot("Bm", "minor") == "10A"
    assert key_to_camelot("F#m", "minor") == "11A"
    assert key_to_camelot("C#m", "minor") == "12A"
    assert key_to_camelot("G#m", "minor") == "1A"
    assert key_to_camelot("D#m", "minor") == "2A"
    assert key_to_camelot("A#m", "minor") == "3A"
    assert key_to_camelot("Fm", "minor") == "4A"
    assert key_to_camelot("Cm", "minor") == "5A"
    assert key_to_camelot("Gm", "minor") == "6A"
    assert key_to_camelot("Dm", "minor") == "7A"

def test_key_to_camelot_alternative_names():
    """Test la conversion des noms alternatifs de clés."""
    assert key_to_camelot("Db", "major") == "3B"
    assert key_to_camelot("Eb", "major") == "5B"
    assert key_to_camelot("Gb", "major") == "2B"
    assert key_to_camelot("Ab", "major") == "4B"
    assert key_to_camelot("Bb", "major") == "6B"
    
    assert key_to_camelot("Dbm", "minor") == "12A"
    assert key_to_camelot("Ebm", "minor") == "2A"
    assert key_to_camelot("Gbm", "minor") == "11A"
    assert key_to_camelot("Abm", "minor") == "1A"
    assert key_to_camelot("Bbm", "minor") == "3A"

def test_key_to_camelot_invalid_input():
    """Test la conversion avec des entrées invalides."""
    assert key_to_camelot(None, "major") == "Unknown"
    assert key_to_camelot("C", None) == "Unknown"
    assert key_to_camelot("", "") == "Unknown"
    assert key_to_camelot("H", "major") == "Unknown"  # Clé non valide