from cryptography.fernet import Fernet
import os

def _get_encryption_key() -> bytes:
    """Obtenir la clé de cryptage depuis l'environnement."""
    import logging
    logger = logging.getLogger(__name__)

    key_str = os.getenv('ENCRYPTION_KEY')
    if not key_str:
        raise RuntimeError("ENCRYPTION_KEY environment variable is required but not set")

    logger.debug("Clé de chiffrement chargée depuis l'environnement")

    # Validation de la clé
    try:
        # Tester que la clé est valide pour Fernet
        Fernet(key_str.encode())
        logger.debug("Clé de chiffrement valide et prête à l'emploi")
        return key_str.encode()
    except Exception as e:
        raise RuntimeError(f"ENCRYPTION_KEY is invalid: {str(e)}. Please provide a valid Fernet key.")

def encrypt_value(value: str) -> str:
    """Crypter une valeur en utilisant la clé d'environnement."""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Décrypter une valeur en utilisant la clé d'environnement."""
    import logging
    logger = logging.getLogger(__name__)

    if not encrypted_value or not isinstance(encrypted_value, str):
        logger.warning(f"Valeur vide ou invalide pour le déchiffrement: {encrypted_value}")
        return ""

    logger.info(f"Tentative de déchiffrement de la valeur: {encrypted_value[:50]}...")  # Log des 50 premiers caractères
    logger.info(f"Longueur de la valeur chiffrée: {len(encrypted_value)}")

    key = _get_encryption_key()
    logger.debug("Clé de chiffrement chargée pour déchiffrement")

    f = Fernet(key)
    try:
        decrypted = f.decrypt(encrypted_value.encode()).decode()
        logger.debug("Déchiffrement réussi")
        return decrypted
    except Exception as e:
        logger.error(f"Échec du déchiffrement: {str(e)}")
        logger.error(f"Type d'exception: {type(e).__name__}")
        logger.error(f"Valeur chiffrée problématique (longueur: {len(encrypted_value)} caractères)")

        # En cas d'échec, propager l'erreur pour ne pas corrompre les données
        raise RuntimeError(f"Failed to decrypt value: {str(e)}")
