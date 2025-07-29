# from strawchemy_init import strawchemy
# from ...models.covers_model import Cover
# import strawberry

# @strawberry.enum
# class CoverType:
#     ARTIST = "artist"
#     ALBUM = "album"
#     TRACK = "track"


# @strawchemy.order(Cover, include="all")
# class CoverOrder:
#     pass
# @strawchemy.filter(Cover, include="all")
# class CoverFilter:
#     pass
# @strawchemy.type(Cover, include="all", filter_input=CoverFilter, order_by=CoverOrder, override=True)
# class CoverGQL:
#     pass
# @strawchemy.create_input(Cover, exclude=["id", "created_at", "updated_at"])
# class CoverCreateInput:
#     pass