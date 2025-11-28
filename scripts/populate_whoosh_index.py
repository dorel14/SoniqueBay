#!/usr/bin/env python3
"""
Script de migration/population pour l'index Whoosh.

Ce script permet de :
- Construire l'index Whoosh complet à partir des tracks existantes
- Mettre à jour l'index pour des tracks spécifiques
- Nettoyer l'index existant

Utilisation :
    python scripts/populate_whoosh_index.py --action build
    python scripts/populate_whoosh_index.py --action update --track-ids 1,2,3
    python scripts/populate_whoosh_index.py --action clear

Optimisé pour Raspberry Pi 4 : traitement par batches, gestion mémoire.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(description="Script de gestion de l'index Whoosh")
    parser.add_argument(
        "--action",
        choices=["build", "update", "clear"],
        required=True,
        help="Action à effectuer"
    )
    parser.add_argument(
        "--track-ids",
        type=str,
        help="IDs des tracks à mettre à jour (séparés par des virgules, pour action=update)"
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default="search_index",
        help="Répertoire de l'index Whoosh (défaut: search_index)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Taille des batches pour l'indexation (défaut: 500)"
    )

    args = parser.parse_args()

    try:
        if args.action == "build":
            logger.info(f"[POPULATE] Démarrage construction index complet: index_dir={args.index_dir}, batch_size={args.batch_size}")
            result = build_index(args.index_dir, args.batch_size)

        elif args.action == "update":
            if not args.track_ids:
                logger.error("[POPULATE] --track-ids requis pour l'action update")
                sys.exit(1)

            track_ids = [int(id.strip()) for id in args.track_ids.split(",") if id.strip()]
            logger.info(f"[POPULATE] Mise à jour index pour {len(track_ids)} tracks: {track_ids}")
            result = update_index(track_ids, args.index_dir)

        elif args.action == "clear":
            logger.info(f"[POPULATE] Nettoyage index: {args.index_dir}")
            result = clear_index(args.index_dir)

        # Afficher le résultat
        print(f"Résultat: {result}")

        if result.get("success"):
            logger.info(f"[POPULATE] Action {args.action} terminée avec succès")
            sys.exit(0)
        else:
            logger.error(f"[POPULATE] Échec de l'action {args.action}: {result.get('error', 'Erreur inconnue')}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("[POPULATE] Interruption par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"[POPULATE] Erreur inattendue: {e}")
        sys.exit(1)


def build_index(index_dir: str = "search_index", batch_size: int = 500) -> dict:
    """
    Lance la construction complète de l'index Whoosh.

    Args:
        index_dir: Répertoire de l'index
        batch_size: Taille des batches

    Returns:
        Résultat de l'opération
    """
    try:
        # Lancer la tâche Celery de manière synchrone
        task = celery.send_task(
            "search_indexer.build_index",
            args=[index_dir, batch_size],
            queue="scan"
        )

        # Attendre la fin de la tâche (timeout de 1 heure pour RPi4)
        result = task.get(timeout=3600)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors de la construction de l'index: {str(e)}"
        }


def update_index(track_ids: list[int], index_dir: str = "search_index") -> dict:
    """
    Met à jour l'index pour des tracks spécifiques.

    Args:
        track_ids: Liste des IDs des tracks à mettre à jour
        index_dir: Répertoire de l'index

    Returns:
        Résultat de l'opération
    """
    try:
        # Lancer la tâche Celery de manière synchrone
        task = celery.send_task(
            "search_indexer.update_index",
            args=[track_ids, index_dir],
            queue="scan"
        )

        # Attendre la fin de la tâche (timeout de 30 minutes)
        result = task.get(timeout=1800)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors de la mise à jour de l'index: {str(e)}"
        }


def clear_index(index_dir: str = "search_index") -> dict:
    """
    Nettoie complètement l'index Whoosh.

    Args:
        index_dir: Répertoire de l'index

    Returns:
        Résultat de l'opération
    """
    try:
        # Lancer la tâche Celery de manière synchrone
        task = celery.send_task(
            "search_indexer.clear_index",
            args=[index_dir],
            queue="maintenance"
        )

        # Attendre la fin de la tâche (timeout de 5 minutes)
        result = task.get(timeout=300)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors du nettoyage de l'index: {str(e)}"
        }


if __name__ == "__main__":
    main()