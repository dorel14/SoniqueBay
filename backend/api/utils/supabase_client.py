"""
Client Supabase pour le backend SoniqueBay.
Utilise la bibliothèque officielle supabase-py.
"""

import os
from typing import Optional

from backend.api.utils.logging import logger
from supabase import Client, create_client

# Configuration singleton
_supabase_client: Optional[Client] = None
_supabase_service_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Retourne le client Supabase pour les opérations anonymes (RLS).
    
    Returns:
        Client Supabase initialisé avec la clé anonyme
    """
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL", "http://supabase-db:5432")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not key:
            raise ValueError("SUPABASE_ANON_KEY non définie dans les variables d'environnement")
        
        _supabase_client = create_client(url, key)
        logger.info("Client Supabase (anon) initialisé")
    
    return _supabase_client


def get_supabase_service_client() -> Client:
    """
    Retourne le client Supabase pour les opérations service (bypass RLS).
    
    Returns:
        Client Supabase initialisé avec la clé de service
    """
    global _supabase_service_client
    
    if _supabase_service_client is None:
        url = os.getenv("SUPABASE_URL", "http://supabase-db:5432")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not key:
            raise ValueError("SUPABASE_SERVICE_KEY non définie dans les variables d'environnement")
        
        _supabase_service_client = create_client(url, key)
        logger.info("Client Supabase (service) initialisé")
    
    return _supabase_service_client


def reset_supabase_clients():
    """Réinitialise les clients Supabase (utile pour les tests)."""
    global _supabase_client, _supabase_service_client
    _supabase_client = None
    _supabase_service_client = None
    logger.debug("Clients Supabase réinitialisés")


class SupabaseClientMixin:
    """
    Mixin pour les services qui ont besoin d'accéder à Supabase.
    Fournit une propriété `supabase` qui retourne le client approprié.
    """
    
    def __init__(self, use_service_role: bool = False):
        self._use_service_role = use_service_role
        self._client: Optional[Client] = None
    
    @property
    def supabase(self) -> Client:
        """Retourne le client Supabase (lazy loading)."""
        if self._client is None:
            if self._use_service_role:
                self._client = get_supabase_service_client()
            else:
                self._client = get_supabase_client()
        return self._client
    
    def reset_client(self):
        """Force la réinitialisation du client."""
        self._client = None


# Export des fonctions principales
__all__ = [
    'get_supabase_client',
    'get_supabase_service_client',
    'reset_supabase_clients',
    'SupabaseClientMixin',
]
