from __future__ import annotations

from typing import TYPE_CHECKING

from strawberry.fastapi import BaseContext


from strawchemy import Strawchemy, StrawchemySyncRepository, StrawchemyConfig
import os

if TYPE_CHECKING:
    from utils.database import SessionLocal

class GraphQLContext(BaseContext):
    db_session: SessionLocal # type: ignore

async def context_getter(db_session: SessionLocal) -> GraphQLContext: # type: ignore
    return GraphQLContext(db_session=db_session)


strawchemy = Strawchemy(StrawchemyConfig(os.getenv('DB_TYPE', 'sqlite').lower(),
                                        repository_type=StrawchemySyncRepository))