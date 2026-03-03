"""
Client Supabase pour le frontend SoniqueBay (NiceGUI).
Utilise la bibliothèque officielle supabase-py.
"""

import os
from typing import Optional

from frontend.utils.logging import logger
from supabase import Client, create_client

# Configuration singleton
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Retourne le client Supabase pour le frontend.
    
    Returns:
        Client Supabase initialisé
    """
    global _supabase_client
    
    if _supabase_client is None:
        # En mode développement local, on utilise les URLs exposées par docker-compose
        url = os.getenv("SUPABASE_URL", "http://localhost:54321")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not key:
            raise ValueError(
                "SUPABASE_ANON_KEY non définie dans les variables d'environnement. "
                "Configurez cette variable avant de démarrer le frontend."
            )
        
        _supabase_client = create_client(url, key)
        logger.info("Client Supabase frontend initialisé")
    
    return _supabase_client


def reset_supabase_client():
    """Réinitialise le client Supabase (utile pour les tests ou reconnexion)."""
    global _supabase_client
    _supabase_client = None
    logger.debug("Client Supabase frontend réinitialisé")


class SupabaseAuth:
    """
    Gestion de l'authentification Supabase pour le frontend.
    """
    
    def __init__(self):
        self.client = get_supabase_client()
        self._user = None
        self._session = None
    
    async def sign_in(self, email: str, password: str) -> dict:
        """
        Connexion avec email/mot de passe.
        
        Args:
            email: Email de l'utilisateur
            password: Mot de passe
            
        Returns:
            Données de session
        """
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            self._session = response.session
            self._user = response.user
            logger.info(f"Utilisateur connecté: {email}")
            return {
                "user": self._user,
                "session": self._session,
                "access_token": self._session.access_token if self._session else None
            }
        except Exception as e:
            logger.error(f"Erreur de connexion: {e}")
            raise
    
    async def sign_up(self, email: str, password: str) -> dict:
        """
        Inscription d'un nouvel utilisateur.
        
        Args:
            email: Email de l'utilisateur
            password: Mot de passe
            
        Returns:
            Données utilisateur créé
        """
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            logger.info(f"Utilisateur inscrit: {email}")
            return {
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            logger.error(f"Erreur d'inscription: {e}")
            raise
    
    async def sign_out(self):
        """Déconnexion de l'utilisateur."""
        try:
            self.client.auth.sign_out()
            self._user = None
            self._session = None
            logger.info("Utilisateur déconnecté")
        except Exception as e:
            logger.error(f"Erreur de déconnexion: {e}")
            raise
    
    def get_current_user(self) -> Optional[dict]:
        """Retourne l'utilisateur actuellement connecté."""
        return self._user
    
    def get_access_token(self) -> Optional[str]:
        """Retourne le token d'accès JWT."""
        if self._session:
            return self._session.access_token
        return None


class SupabaseRealtime:
    """
    Gestion des abonnements temps réel Supabase.
    """
    
    def __init__(self):
        self.client = get_supabase_client()
        self._channels = {}
    
    def subscribe(self, table: str, callback, event: str = "*"):
        """
        S'abonne aux changements sur une table.
        
        Args:
            table: Nom de la table
            callback: Fonction à appeler sur changement
            event: Type d'événement (INSERT, UPDATE, DELETE, *)
        """
        channel = self.client.channel(f"{table}_changes")
        
        channel.on(
            "postgres_changes",
            event=event,
            schema="public",
            table=table,
            callback=callback
        ).subscribe()
        
        self._channels[table] = channel
        logger.info(f"Abonnement temps réel activé pour {table}")
        return channel
    
    def unsubscribe(self, table: str):
        """Désabonne d'une table."""
        if table in self._channels:
            self._channels[table].unsubscribe()
            del self._channels[table]
            logger.info(f"Abonnement temps réel désactivé pour {table}")


# Export des fonctions principales
__all__ = [
    'get_supabase_client',
    'reset_supabase_client',
    'SupabaseAuth',
    'SupabaseRealtime',
]
