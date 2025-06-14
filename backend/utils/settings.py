import requests
from typing import Optional
import os

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')

def get_setting(key: str) -> Optional[str]:
    try:
        response = requests.get(f"{API_BASE_URL}/settings/{key}")
        response.raise_for_status()
        setting = response.json()
        return setting.get('value')
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération du paramètre {key}: {e}")
        return None
