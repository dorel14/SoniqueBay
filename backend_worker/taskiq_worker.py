"""Worker TaskIQ pour SoniqueBay.

Démarre en parallèle du worker Celery.
"""
from backend_worker.taskiq_app import broker
import asyncio

# Import des tâches TaskIQ (à migrer progressivement)
# from backend_worker.taskiq_tasks import *


async def main() -> None:
    """Point d'entrée principal du worker TaskIQ."""
    await broker.startup()
    # Le worker écoute les tâches
    await broker.run()


if __name__ == "__main__":
    asyncio.run(main())
