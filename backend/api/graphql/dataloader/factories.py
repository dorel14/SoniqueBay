from typing import Callable, Awaitable, Sequence, Any
from strawberry.dataloader import DataLoader

def by_id_loader(
    fetch_fn: Callable[[Sequence[int], Any], Awaitable[Sequence[Any]]],
    session,
) -> DataLoader:
    async def load(ids):
        return await fetch_fn(ids, session)

    return DataLoader(load_fn=load)