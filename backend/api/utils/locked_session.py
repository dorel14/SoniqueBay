# -*- coding: utf-8 -*-
"""
Wrapper pour session SQLAlchemy async avec verrou de concurrence.

Ce module fournit un wrapper autour des sessions SQLAlchemy async pour empêcher
les accès concurrents qui causent des erreurs avec SQLAlchemy.

Usage:
    db = LockedSession(session, lock)
    result = await db.execute(query)
"""
import asyncio
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable


class LockedSession:
    """
    Wrapper pour AsyncSession qui utilise un verrou pour empêcher
    les opérations concurrentes.
    """

    def __init__(self, session: AsyncSession, lock: asyncio.Lock):
        self._session = session
        self._lock = lock

    async def execute(self, statement: Executable, params: Optional[Any] = None):
        """Exécute une requête avec verrou."""
        async with self._lock:
            return await self._session.execute(statement, params)

    async def scalar(self, statement: Executable, params: Optional[Any] = None):
        """Récupère un scalaire avec verrou."""
        async with self._lock:
            result = await self._session.execute(statement, params)
            return result.scalar()

    async def scalars(self, statement: Executable, params: Optional[Any] = None):
        """Récupère plusieurs scalaires avec verrou."""
        async with self._lock:
            result = await self._session.execute(statement, params)
            return result.scalars()

    async def commit(self):
        """Commit avec verrou."""
        async with self._lock:
            await self._session.commit()

    async def rollback(self):
        """Rollback avec verrou."""
        async with self._lock:
            await self._session.rollback()

    async def refresh(self, instance: Any):
        """Refresh avec verrou."""
        async with self._lock:
            await self._session.refresh(instance)

    async def flush(self):
        """Flush avec verrou."""
        async with self._lock:
            await self._session.flush()

    def add(self, instance: Any):
        """Add sans verrou (opération synchrone)."""
        self._session.add(instance)

    def delete(self, instance: Any):
        """Delete sans verrou (opération synchrone)."""
        self._session.delete(instance)

    @property
    def session(self) -> AsyncSession:
        """Accès direct à la session sous-jacente (à utiliser avec précaution)."""
        return self._session

    def __getattr__(self, name: str) -> Any:
        """Délègue les autres attributs à la session."""
        return getattr(self._session, name)
