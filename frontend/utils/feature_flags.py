"""
Feature flags pour la migration progressive vers Supabase.
"""

import os


class FeatureFlags:
    """
    Gestion centralisée des feature flags.
    
    Permet d'activer/désactiver progressivement les fonctionnalités
    lors de la migration vers Supabase.
    """
    
    @staticmethod
    def use_supabase() -> bool:
        """
        Active l'utilisation de Supabase pour les opérations CRUD.
        
        Returns:
            True si Supabase doit être utilisé, False pour API legacy
        """
        return os.getenv("USE_SUPABASE", "false").lower() == "true"
    
    @staticmethod
    def use_supabase_realtime() -> bool:
        """
        Active Supabase Realtime pour les fonctionnalités temps réel.
        
        Returns:
            True si Realtime doit être utilisé, False pour WebSocket legacy
        """
        return os.getenv("USE_SUPABASE_REALTIME", "false").lower() == "true"
    
    @staticmethod
    def use_supabase_auth() -> bool:
        """
        Active Supabase Auth pour l'authentification.
        
        Returns:
            True si Auth Supabase doit être utilisé
        """
        return os.getenv("USE_SUPABASE_AUTH", "false").lower() == "true"
    
    @staticmethod
    def supabase_url() -> str:
        """URL de l'instance Supabase."""
        return os.getenv("SUPABASE_URL", "http://localhost:54322")
    
    @staticmethod
    def supabase_anon_key() -> str:
        """Clé anonyme Supabase."""
        return os.getenv("SUPABASE_ANON_KEY", "")
    
    @staticmethod
    def api_url() -> str:
        """URL de l'API legacy (fallback)."""
        return os.getenv("API_URL", "http://localhost:8001")


# Instance singleton
_feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Retourne l'instance des feature flags."""
    return _feature_flags


__all__ = ['FeatureFlags', 'get_feature_flags']
