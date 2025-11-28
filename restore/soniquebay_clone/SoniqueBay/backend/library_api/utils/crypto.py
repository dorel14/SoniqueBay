from cryptography.fernet import Fernet
import os

def _get_encryption_key() -> bytes:
    """Obtenir la clé de cryptage depuis l'environnement ou générer une nouvelle."""
    key_str = os.getenv('ENCRYPTION_KEY')
    if key_str:
        return key_str.encode()
    else:
        return Fernet.generate_key()

def encrypt_value(value: str) -> str:
    """Crypter une valeur en utilisant la clé d'environnement."""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Décrypter une valeur en utilisant la clé d'environnement."""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_value.encode()).decode()
