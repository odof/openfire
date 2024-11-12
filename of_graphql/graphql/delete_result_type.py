import graphene


class DeleteResult(graphene.ObjectType):
    _name = "DeleteResult"
    _type = "types"

    deleted_ids = graphene.List(graphene.NonNull(graphene.Int))
    non_existent_ids = graphene.List(graphene.NonNull(graphene.Int))
