import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_update

from .user_type import User, UserUpdateInput


class UserUpdate(graphene.Mutation):
    _name = 'UserUpdate'

    # ici on définit les arguments qui sont à utiliser pour mettre à jour un utilisateur
    class Arguments:
        id = graphene.Int(required=True)
        input = UserUpdateInput(required=True)

    # ici on précise qu'on va retourner à la fin de cette fonction un objet User
    Output = User

    # c'est cette fonction qui sera appelée lors l'appel de la classe UpdateUser
    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, "res.users", id, input)


class UserMutation(graphene.ObjectType):
    _name = "UserMutation"
    _type = "mutation"

    user_update = UserUpdate.Field(description="Documentation of UserUpdate")
