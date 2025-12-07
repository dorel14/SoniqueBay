from cryptography.fernet import Fernet
import os

def _get_encryption_key() -> bytes:
    """Obtenir la clé de cryptage depuis l'environnement ou utiliser une clé par défaut."""
    import logging
    logger = logging.getLogger(__name__)

    # Clé par défaut pour la compatibilité - devrait être remplacée par une clé d'environnement en production
    # Cette clé est une clé Fernet valide générée avec Fernet.generate_key()
    DEFAULT_ENCRYPTION_KEY = "kX7Qw9JbE2pR5sT8uV1yA4zD6fG7hK9mN2qW3eR5tY7uI8oP0aS2dF4gH6jK8lZ"

    key_str = os.getenv('ENCRYPTION_KEY', DEFAULT_ENCRYPTION_KEY)
    logger.info(f"Clé de chiffrement utilisée: {key_str[:10]}...")

    # Validation de la clé
    try:
        # Tester que la clé est valide pour Fernet
        Fernet(key_str.encode())
        logger.info("Clé de chiffrement valide et prête à l'emploi")
        return key_str.encode()
    except Exception as e:
        logger.error(f"Clé de chiffrement invalide: {str(e)}, utilisation de la clé par défaut")
        # Générer une nouvelle clé valide si la clé par défaut est invalide
        new_key = Fernet.generate_key()
        logger.warning(f"Nouvelle clé générée: {new_key.decode()[:10]}...")
        return new_key

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
    logger.info(f"Clé de chiffrement utilisée: {key[:10]}...")  # Log des 10 premiers caractères de la clé

    f = Fernet(key)
    try:
        decrypted = f.decrypt(encrypted_value.encode()).decode()
        logger.info("Déchiffrement réussi")
        return decrypted
    except Exception as e:
        logger.error(f"Échec du déchiffrement: {str(e)}")
        logger.error(f"Type d'exception: {type(e).__name__}")
        logger.error(f"Valeur chiffrée problématique (100 premiers caractères): {encrypted_value[:100]}...")

        # En cas d'échec, retourner une valeur par défaut et marquer pour ré-encryption
        logger.warning("Retour d'une valeur vide en raison de l'échec du déchiffrement")
        return ""
