from ..graph_init import strawchemy
from ...models.user_model import User

@strawchemy.type(model=User, include=["id","username"])
class UserType():
    pass

@strawchemy.filter(model=User, include=["username"])
class UserFilter():
    pass

@strawchemy.order(model=User, include=["username"])
class UserOrderBy():
    pass