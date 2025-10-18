from contextlib import asynccontextmanager, contextmanager
from backend.library_api.utils.database import get_session, get_db
from sqlalchemy.orm import DeclarativeBase
from typing import Callable, Any, Coroutine


# -------- ASYNC SESSION --------

@asynccontextmanager
async def with_session():
    async with get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e

async def run_in_session(func: Callable, *args, **kwargs) -> Any:
    async with get_session() as session:
        try:
            result = await func(session, *args, **kwargs)
            await session.commit()

            if isinstance(result, DeclarativeBase):
                await session.refresh(result)
            return result
        except Exception:
            await session.rollback()
            raise

def transactional(func: Callable[..., Coroutine[Any, Any, Any]]):
    async def wrapper(*args, **kwargs):
        async with get_session() as session:
            try:
                result = await func(session=session, *args, **kwargs)
                await session.commit()

                if isinstance(result, DeclarativeBase):
                    await session.refresh(result)
                return result
            except Exception:
                await session.rollback()
                raise
    return wrapper


# -------- SYNC SESSION --------

@contextmanager
def with_sync_session():
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def run_in_sync_session(func: Callable, *args, **kwargs) -> Any:
    db = next(get_db())
    try:
        result = func(db, *args, **kwargs)
        db.commit()

        if isinstance(result, DeclarativeBase):
            db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def transactional_sync(func: Callable):
    def wrapper(*args, **kwargs):
        db = next(get_db())
        try:
            result = func(session=db, *args, **kwargs)
            db.commit()
            if isinstance(result, DeclarativeBase):
                db.refresh(result)
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    return wrapper
