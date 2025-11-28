#!/usr/bin/env python3
"""
Script pour mettre à jour les imports après la restructuration du dossier backend/api.
Remplace 'from backend.api.' par 'from backend.api.' dans tous les fichiers Python.
"""
import os
import re

def update_imports_in_file(filepath):
    """Met à jour les imports dans un fichier."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remplacer les imports
        original_content = content
        content = re.sub(r'from backend\.library_api\.', 'from backend.api.', content)
        content = re.sub(r'from backend\.recommender_api\.', 'from backend.api.', content)
        content = re.sub(r'from backend\.api\.api\.', 'from backend.api.', content)

        # Écrire seulement si il y a eu des changements
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def main():
    """Parcourt tous les fichiers Python et met à jour les imports."""
    updated_count = 0
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if update_imports_in_file(filepath):
                    updated_count += 1

    print(f"Total files updated: {updated_count}")

if __name__ == '__main__':
    main()