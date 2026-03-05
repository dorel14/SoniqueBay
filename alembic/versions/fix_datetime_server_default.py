# -*- coding: utf-8 -*-
"""
Migration: Fix datetime server_default for genres and settings tables

Rôle:
    Corrige le problème de timezone-aware vs naive datetime en ajoutant
    server_default=CURRENT_TIMESTAMP aux colonnes date_added et date_modified
    des tables genres et settings.

    Ce fix résout l'erreur "can't subtract offset-naive and offset-aware datetimes"
    qui se produisait lors de l'insertion de genres via l'API.

Contexte:
    Les modèles SQLAlchemy ont été mis à jour pour utiliser TimestampMixin
    qui définit DateTime(timezone=True) avec server_default=text("CURRENT_TIMESTAMP").
    Cette migration aligne le schéma de la base de données avec les modèles.

Auteur: SoniqueBay Team
Date: 2026-02-07
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# Revision identifiers, used by Alembic.
revision: str = 'fix_datetime_server_default'
down_revision: Union[str, Sequence[str], None] = 'zzzzzz_merge_all_heads_final'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Ajoute server_default aux colonnes datetime.

    Modifications:
        - genres.date_added: Ajoute timezone=True et server_default
        - genres.date_modified: Ajoute timezone=True et server_default
        - settings.date_added: Ajoute timezone=True et server_default
        - settings.date_modified: Ajoute timezone=True et server_default
    """
    logger.info("Ajout de server_default aux colonnes datetime de genres et settings")

    # Table genres: date_added
    with op.batch_alter_table('genres', schema=None) as batch_op:
        batch_op.alter_column(
            'date_added',
            type_=sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            existing_nullable=True,
            existing_type=sa.DateTime()
        )

    # Table genres: date_modified
    with op.batch_alter_table('genres', schema=None) as batch_op:
        batch_op.alter_column(
            'date_modified',
            type_=sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            existing_nullable=True,
            existing_type=sa.DateTime()
        )

    # Table settings: date_added
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column(
            'date_added',
            type_=sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            existing_nullable=True,
            existing_type=sa.DateTime()
        )

    # Table settings: date_modified
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column(
            'date_modified',
            type_=sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            existing_nullable=True,
            existing_type=sa.DateTime()
        )

    logger.info("Migration fix_datetime_server_default terminée avec succès")


def downgrade() -> None:
    """
    Downgrade schema: Supprime server_default des colonnes datetime.

    Revient au comportement précédent (pas de server_default explicite).
    """
    logger.info("Suppression de server_default des colonnes datetime de genres et settings")

    # Table genres: date_added
    with op.batch_alter_table('genres', schema=None) as batch_op:
        batch_op.alter_column(
            'date_added',
            type_=sa.DateTime(),
            server_default=None,
            existing_nullable=True,
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.text('CURRENT_TIMESTAMP')
        )

    # Table genres: date_modified
    with op.batch_alter_table('genres', schema=None) as batch_op:
        batch_op.alter_column(
            'date_modified',
            type_=sa.DateTime(),
            server_default=None,
            existing_nullable=True,
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.text('CURRENT_TIMESTAMP')
        )

    # Table settings: date_added
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column(
            'date_added',
            type_=sa.DateTime(),
            server_default=None,
            existing_nullable=True,
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.text('CURRENT_TIMESTAMP')
        )

    # Table settings: date_modified
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column(
            'date_modified',
            type_=sa.DateTime(),
            server_default=None,
            existing_nullable=True,
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.text('CURRENT_TIMESTAMP')
        )

    logger.info("Downgrade de fix_datetime_server_default terminé")
