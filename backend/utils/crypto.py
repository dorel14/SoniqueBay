from cryptography.fernet import Fernet
from base64 import b64encode, b64decode
import os

# Générer ou charger la clé de cryptage
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())

def encrypt_value(value: str) -> str:
    f = Fernet(ENCRYPTION_KEY)
    return b64encode(f.encrypt(value.encode())).decode()

def decrypt_value(encrypted_value: str) -> str:
    f = Fernet(ENCRYPTION_KEY)
    return f.decrypt(b64decode(encrypted_value)).decode()
