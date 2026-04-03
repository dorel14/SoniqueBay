"""Repository de base avec garde-fous."""
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    """Classe de base pour les repositories workers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def execute_with_timeout(self, query, timeout=30):
        """Exécute une requête avec timeout."""
        try:
            return await asyncio.wait_for(
                self.session.execute(query),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"[TASKIQ] Requête timeout après {timeout}s")
            raise TimeoutError(f"Requête timeout après {timeout}s")
    
    async def commit_with_retry(self, max_retries=3):
        """Commit avec retry et backoff."""
        for attempt in range(max_retries):
            try:
                await self.session.commit()
                return
            except Exception as e:
                logger.warning(f"[TASKIQ] Tentative de commit {attempt+1} échouée: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"[TASKIQ] Échec du commit après {max_retries} tentatives")
                    raise
                await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
