"""
TinyDB handler for simple file-based storage.
Used for playqueue persistence.
"""

from tinydb import TinyDB
import os

class TinyDBHandler:
    @staticmethod
    def get_db(name: str) -> TinyDB:
        db_path = f"data/{name}.json"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return TinyDB(db_path)