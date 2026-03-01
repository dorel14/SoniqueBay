"""
Configuration centralisée pour la migration Supabase.
Un seul feature flag global : USE_SUPABASE
"""

import os
from typing import Optional

# Feature flag global - contrôle toute l'application
# True = utiliser Supabase pour les entités migrées
# False = utiliser SQLAlchemy (fallback)
USE_SUPABASE: bool = os.getenv("USE_SUPABASE", "false").lower() in ("true", "1", "yes", "on")

# Configuration Supabase
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://supabase-db:54321")
SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")

# Tables migrées vers Supabase (liste progressive)
# Au début : [], puis on ajoute "tracks", "albums", etc.
MIGRATED_TABLES: set = set(
    os.getenv("MIGRATED_TABLES", "").split(",")
    if os.getenv("MIGRATED_TABLES")
    else []
)


def is_migrated(table_name: str) -> bool:
    """
    Vérifie si une table est migrée vers Supabase.
    
    Args:
        table_name: Nom de la table
        
    Returns:
        True si la table utilise Supabase, False sinon
    """
    if not USE_SUPABASE:
        return False
    return table_name in MIGRATED_TABLES


def get_db_backend(table_name: str) -> str:
    """
    Retourne le backend à utiliser pour une table.
    
    Args:
        table_name: Nom de la table
        
    Returns:
        "supabase" ou "sqlalchemy"
    """
    return "supabase" if is_migrated(table_name) else "sqlalchemy"


__all__ = [
    "USE_SUPABASE",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "MIGRATED_TABLES",
    "is_migrated",
    "get_db_backend",
]
