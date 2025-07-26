from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session
from strawberry.fastapi import BaseContext
from strawchemy import Strawchemy, StrawchemyConfig, StrawchemySyncRepository
from utils.database import get_session, get_db


class GraphQLContext(BaseContext):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

SessionDep = Annotated[Session, Depends(get_session)]


async def context_getter(db_session: SessionDep) -> GraphQLContext:
    return GraphQLContext(session=db_session)


strawchemy = Strawchemy(StrawchemyConfig("sqlite", repository_type=StrawchemySyncRepository))