#!/usr/bin/env python3
"""
Script pour corriger les imports backend_worker.models vers backend.api.models
dans tout le projet backend_worker/
"""

import os
import re

BACKEND_WORKER_DIR = "backend_worker"

# Mapping des remplacements
REPLACEMENTS = [
    # Base et TimestampMixin
    (
        r'from backend_worker\.models\.base import Base, TimestampMixin',
        'from backend.api.utils.database import Base, TimestampMixin'
    ),
    (
        r'from backend_worker\.models\.base import Base',
        'from backend.api.utils.database import Base'
    ),
    # Tous les modèles
    (
        r'from backend_worker\.models\.(\w+) import',
        r'from backend.api.models.\1 import'
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
    """Parcourt tous les fichiers .py dans backend_worker/."""
    fixed_count = 0
    
    for root, dirs, files in os.walk(BACKEND_WORKER_DIR):
        for filename in files:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                if fix_file(filepath):
                    fixed_count += 1
    
    print(f"\n📊 Total: {fixed_count} fichiers corrigés")

if __name__ == "__main__":
    main()