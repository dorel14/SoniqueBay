"""Utilitaires de chiffrement pour SoniqueBay.

Ce module fournit des fonctions de chiffrement/déchiffrement basées sur Fernet.
La clé de chiffrement DOIT être fournie via la variable d'environnement ENCRYPTION_KEY.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import os

from cryptography.fernet import Fernet

from backend.api.utils.logging import logger


def _get_encryption_key() -> bytes:
    """Obtenir la clé de chiffrement depuis la variable d'environnement ENCRYPTION_KEY.

    Raises:
        RuntimeError: Si ENCRYPTION_KEY n'est pas définie ou est invalide.

    Returns:
        bytes: La clé Fernet encodée en bytes.
    """
    key_str = os.getenv('ENCRYPTION_KEY')
    if not key_str:
        raise RuntimeError(
            "ENCRYPTION_KEY environment variable is required but not set. "
            "Generate a valid Fernet key with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # Validation de la clé Fernet
    try:
        Fernet(key_str.encode())
        return key_str.encode()
    except Exception as e:
        raise RuntimeError(
            f"ENCRYPTION_KEY is set but invalid (not a valid Fernet key): {e}. "
            "Please provide a valid Fernet key."
        ) from e


def encrypt_value(value: str) -> str:
    """Chiffrer une valeur en utilisant la clé d'environnement.

    Args:
        value: Valeur en clair à chiffrer.

    Returns:
        Valeur chiffrée encodée en base64.

    Raises:
        RuntimeError: Si ENCRYPTION_KEY n'est pas définie ou invalide.
    """
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Déchiffrer une valeur en utilisant la clé d'environnement.

    Args:
        encrypted_value: Valeur chiffrée encodée en base64.

    Returns:
        Valeur déchiffrée, ou chaîne vide si la valeur est invalide.

    Raises:
        RuntimeError: Si ENCRYPTION_KEY n'est pas définie ou invalide.
    """
    if not encrypted_value or not isinstance(encrypted_value, str):
        logger.warning(f"Valeur vide ou invalide pour le déchiffrement: {encrypted_value}")
        return ""

    key = _get_encryption_key()
    f = Fernet(key)
    try:
        decrypted = f.decrypt(encrypted_value.encode()).decode()
        logger.debug("Déchiffrement réussi")
        return decrypted
    except Exception as e:
        logger.error(f"Échec du déchiffrement: {type(e).__name__}: {e}")
        # NOTE: Ne jamais logger le ciphertext - risque de fuite de données
        # et d'attaques par brute-force offline. On logue seulement la longueur.
        logger.error(
            f"Valeur chiffrée problématique (longueur: {len(encrypted_value)} caractères)"
        )
        return ""
