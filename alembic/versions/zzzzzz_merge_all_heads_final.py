# -*- coding: utf-8 -*-
"""
Migration: Fusion finale des 3 heads Alembic en un seul tronc

Rôle:
    Cette migration de fusion consolide les 3 heads non fusionnées en un seul tronc
    pour résoudre l'erreur "Multiple head revisions are present for given argument 'head'".

Heads fusionnées:
    1. 192555aeb78a - ajout de response_mode à ai_agents
    2. b2c3d4e5f6g7 - création des tables MIR (track_mir_raw, normalized, scores, synthetic_tags)
    3. a1b2c3d4e5f7 - suppression des colonnes legacy de la table tracks

Nouvelle tête: zzzzzz_merge_all_heads_final

Prérequis:
    - Ces 3 heads doivent avoir été appliquées dans la base de données avant cette migration
    - Cette migration est un "merge" sans changement de schéma

Auteur: SoniqueBay Team
Date: 2026-02-06
"""

from typing import Sequence, Union
from alembic import op
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# Revision identifiers, used by Alembic.
revision: str = 'zzzzzz_merge_all_heads_final'
down_revision: Union[str, Sequence[str], None] = (
    '192555aeb78a',
    'b2c3d4e5f6g7',
    'a1b2c3d4e5f7'
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Fusion des 3 heads en un seul tronc.
    
    Cette migration est un "merge" - elle ne modifie pas le schéma de la base de données.
    Elle sert uniquement à résoudre la divergence des heads dans le graphe Alembic.
    """
    logger.info("Fusion des heads Alembic en un seul tronc")
    logger.info("Heads fusionnées: 192555aeb78a, b2c3d4e5f6g7, a1b2c3d4e5f7")
    pass


def downgrade() -> None:
    """
    Downgrade schema: Pas de downgrade pour une migration de fusion.
    
    Les migrations de fusion ne peuvent pas être facilement défaites car elles
    consolidient plusieurs branches. Pour revenir en arrière, il faudrait
    recréer les branches de migration.
    """
    logger.warning("Downgrade de merge non supporté - les heads restent fusionnées")
    pass
