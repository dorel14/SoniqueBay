from strawchemy import Strawchemy, StrawchemySyncRepository, StrawchemyConfig
from library_api.utils.settings import get_strawchemy_config


strawchemy = Strawchemy(StrawchemyConfig(get_strawchemy_config(),
                                        repository_type=StrawchemySyncRepository))