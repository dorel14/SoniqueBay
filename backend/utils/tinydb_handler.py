from tinydb import TinyDB
import os

class TinyDBHandler:
    _instances = {}

    @classmethod
    def get_db(cls, db_name: str) -> TinyDB:
        if db_name not in cls._instances:
            db_path = os.path.join('./backend/data', f'{db_name}.json')
            os.makedirs('data', exist_ok=True)
            cls._instances[db_name] = TinyDB(db_path)
        return cls._instances[db_name]
