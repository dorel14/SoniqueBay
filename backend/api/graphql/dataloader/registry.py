from typing import Callable, Dict
from strawberry.dataloader import DataLoader

class LoaderRegistry:
    def __init__(self):
        self._loaders: Dict[str, DataLoader] = {}

    def get(self, name: str, factory: Callable[[], DataLoader]) -> DataLoader:
        if name not in self._loaders:
            self._loaders[name] = factory()
        return self._loaders[name]