"""Worker TaskIQ pour SoniqueBay.

Démarre en parallèle du worker Celery.
"""
from backend_worker.taskiq_app import broker
from taskiq.api import run_receiver_task
import asyncio

# Import des tâches TaskIQ (à migrer progressivement)
# from backend_worker.taskiq_tasks import *


async def main() -> None:
    """Point d'entrée principal du worker TaskIQ."""
    await broker.startup()
    # Le worker écoute les tâches
    await run_receiver_task(broker, run_startup=True)


if __name__ == "__main__":
    asyncio.run(main())
