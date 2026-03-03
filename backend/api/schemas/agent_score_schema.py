"""
Schemas Pydantic pour les scores des agents.

Ces schémas sont utilisés pour la validation et la sérialisation des données
liées aux scores des agents dans l'API.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentScoreBase(BaseModel):
    """
    Schéma de base pour un score d'agent.
    
    Contient les champs communs à la création et à la mise à jour.
    """
    agent_name: str = Field(..., description="Nom de l'agent")
    intent: str = Field(..., description="Intention ou tâche de l'agent")
    score: float = Field(1.0, ge=0.0, le=10.0, description="Score de performance (0.0 à 10.0)")
    usage_count: int = Field(0, ge=0, description="Nombre d'utilisations")
    success_count: int = Field(0, ge=0, description="Nombre de succès")


class AgentScoreCreate(AgentScoreBase):
    """
    Schéma pour créer un nouveau score d'agent.
    
    Utilisé lors de la création d'un nouvel enregistrement dans la base de données.
    """
    pass


class AgentScoreUpdate(BaseModel):
    """
    Schéma pour mettre à jour un score d'agent existant.
    
    Tous les champs sont optionnels pour permettre des mises à jour partielles.
    """
    agent_name: Optional[str] = Field(None, description="Nouveau nom de l'agent")
    intent: Optional[str] = Field(None, description="Nouvelle intention ou tâche")
    score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Nouveau score")
    usage_count: Optional[int] = Field(None, ge=0, description="Nouveau compteur d'utilisations")
    success_count: Optional[int] = Field(None, ge=0, description="Nouveau compteur de succès")


class AgentScore(AgentScoreBase):
    """
    Schéma complet pour un score d'agent.
    
    Inclut l'ID et est utilisé pour les réponses de l'API.
    """
    id: int = Field(..., description="Identifiant unique du score")

    model_config = ConfigDict(from_attributes=True)


class AgentScoreWithMetrics(AgentScore):
    """
    Schéma étendu avec des métriques calculées.
    
    Inclut des champs dérivés pour faciliter l'analyse.
    """
    success_rate: Optional[float] = Field(None, description="Taux de succès (success_count/usage_count)")
    last_used: Optional[str] = Field(None, description="Dernière date d'utilisation")


class AgentScoreListResponse(BaseModel):
    """
    Schéma de réponse pour la liste des scores d'agents.
    
    Utilisé pour paginer et structurer les résultats.
    """
    count: int = Field(..., description="Nombre total de scores")
    results: list[AgentScore] = Field(..., description="Liste des scores")
