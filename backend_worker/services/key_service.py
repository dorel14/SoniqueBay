from typing import Optional

CAMELOT_MAP = {
    'C': '8B', 'C#': '3B', 'Db': '3B', 'D': '10B', 'D#': '5B', 'Eb': '5B',
    'E': '12B', 'F': '7B', 'F#': '2B', 'Gb': '2B', 'G': '9B', 'G#': '4B',
    'Ab': '4B', 'A': '11B', 'A#': '6B', 'Bb': '6B', 'B': '1B',

    'Cm': '5A', 'C#m': '12A', 'Dbm': '12A', 'Dm': '7A', 'D#m': '2A',
    'Ebm': '2A', 'Em': '9A', 'Fm': '4A', 'F#m': '11A', 'Gbm': '11A',
    'Gm': '6A', 'G#m': '1A', 'Abm': '1A', 'Am': '8A', 'A#m': '3A',
    'Bbm': '3A', 'Bm': '10A'
}

def key_to_camelot(key: str, scale: str) -> str:
    """Convertit une clé musicale en notation Camelot."""
    if not key or not scale:
        return "Unknown"
    full_key = key + ('m' if scale.lower() == 'minor' else '')
    return CAMELOT_MAP.get(full_key, "Unknown")
