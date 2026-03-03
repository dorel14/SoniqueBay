from strawchemy import Strawchemy, StrawchemyConfig, StrawchemySyncRepository

from backend.api.utils.settings import get_strawchemy_config

strawchemy = Strawchemy(StrawchemyConfig(get_strawchemy_config(),
                                        repository_type=StrawchemySyncRepository))