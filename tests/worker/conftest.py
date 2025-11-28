# tests/backend_worker/conftest.py
import sys
import os

# Ajouter le répertoire racine au sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, root_dir)
os.environ['PYTHONPATH'] = root_dir