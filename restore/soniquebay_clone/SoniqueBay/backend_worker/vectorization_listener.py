#!/usr/bin/env python3
"""
Vectorization Listener - Point d'entrée direct pour le listener de vectorisation

Ce script lance directement la classe VectorizationEventListener
plutôt que d'utiliser un wrapper.

Usage:
    python backend_worker/vectorization_listener.py

Optimisé pour Raspberry Pi :
- Traitement asynchrone
- Gestion d'erreurs robuste
- Reconnexion automatique Redis
- Logs détaillés
"""

import asyncio
import signal
import sys
from backend_worker.utils.redis_utils import vectorization_listener
from backend_worker.utils.logging import logger


class GracefulShutdown:
    """Gestionnaire d'arrêt gracieux."""

    def __init__(self):
        self.shutdown_event = asyncio.Event()

    def signal_handler(self, signum, frame):
        """Gère les signaux d'arrêt."""
        logger.info(f"Signal d'arrêt reçu: {signum}")
        self.shutdown_event.set()

    async def wait_for_shutdown(self):
        """Attend l'événement d'arrêt."""
        await self.shutdown_event.wait()


async def main():
    """
    Point d'entrée principal du listener de vectorisation.
    """
    logger.info("=== DÉMARRAGE VECTORIZATION LISTENER ===")

    # Configuration des signaux pour arrêt gracieux
    shutdown_handler = GracefulShutdown()
    signal.signal(signal.SIGINT, shutdown_handler.signal_handler)
    signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)

    try:
        # Démarrer l'écoute des événements
        await vectorization_listener.start_listening()

    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")

    except Exception as e:
        logger.error(f"Erreur dans le listener principal: {e}")

    finally:
        # Arrêt gracieux
        logger.info("Arrêt du vectorization listener...")
        await vectorization_listener.stop_listening()
        logger.info("=== VECTORIZATION LISTENER ARRÊTÉ ===")


if __name__ == "__main__":
    # Configuration des logs pour le service
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s'
    )

    # Exécuter le listener
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt du service")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)