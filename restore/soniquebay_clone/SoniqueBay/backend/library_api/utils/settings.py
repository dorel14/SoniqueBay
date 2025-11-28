import httpx
from typing import Optional
import os
from backend.api.utils.logging import logger

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')

async def get_setting(key: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/settings/{key}")
            response.raise_for_status()
            setting = response.json()
            return setting.get('value')
    except httpx.HTTPStatusError as e:
        logger.error(f"Erreur HTTP lors de la récupération du paramètre {key}: {e}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Erreur de requête lors de la récupération du paramètre {key}: {e}")
        return None
    except Exception as e:
        logger.error(f"Autre erreur lors de la récupération du paramètre {key}: {e}")
        return None

def get_database_url():
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()

    if db_type == 'sqlite':
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(data_dir, exist_ok=True)
        return f'sqlite:///{os.path.join(data_dir, "music.db")}'

    elif db_type == 'postgres':
        return (f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
                f"{os.getenv('DB_PASS', '')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'musicdb')}")

    elif db_type == 'mariadb':
        return (f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:"
                f"{os.getenv('DB_PASS', '')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '3306')}/"
                f"{os.getenv('DB_NAME', 'musicdb')}")

    raise ValueError(f"Base de données non supportée: {db_type}")

def get_strawchemy_config():
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()
    if db_type == 'sqlite':
        return "sqlite"
    elif db_type in ['postgres', 'mariadb']:
        return db_type
    else:
        raise ValueError(f"Configuration de Strawchemy non supportée pour: {db_type}")

class Settings:
    def __init__(self):
        self.dburl = get_database_url()
