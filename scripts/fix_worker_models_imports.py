#!/usr/bin/env python3
"""
Script pour corriger les imports dans backend_worker/models/
Remplace 'from backend.api.utils.database import' par 'from backend_worker.models.base import'
"""

import os
import re

MODELS_DIR = "backend_worker/models"

# Mapping des remplacements
REPLACEMENTS = [
    # Base et TimestampMixin
    (
        r'from backend\.api\.utils\.database import Base, TimestampMixin',
        'from backend_worker.models.base import Base, TimestampMixin'
    ),
    (
        r'from backend\.api\.utils\.database import Base',
        'from backend_worker.models.base import Base'
    ),
    # Covers (dans tracks_model.py et albums_model.py et artist_embeddings_model.py)
    (
        r'from backend\.api\.models\.covers_model import Cover',
        'from backend_worker.models.covers_model import Cover'
    ),
]

def fix_file(filepath):
    """Corrige les imports dans un fichier."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Corrigé: {filepath}")
        return True
    return False

def main():
    """Parcourt tous les fichiers .py dans backend_worker/models/."""
    fixed_count = 0
    
    for filename in os.listdir(MODELS_DIR):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(MODELS_DIR, filename)
            if fix_file(filepath):
                fixed_count += 1
    
    # Corriger aussi __init__.py s'il a des imports problématiques
    init_file = os.path.join(MODELS_DIR, '__init__.py')
    if os.path.exists(init_file):
        # L'__init__.py est déjà correct (il importe depuis local)
        pass
    
    print(f"\n📊 Total: {fixed_count} fichiers corrigés")

if __name__ == "__main__":
    main()
