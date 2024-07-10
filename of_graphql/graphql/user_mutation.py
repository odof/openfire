# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput

from .user_type import User


class UserUpdate(graphene.Mutation):
    _name = 'UserUpdate'

    # ici on définit les arguments qui sont à utiliser pour mettre à jour un utilisateur
    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        mobile = graphene.String()
        phone = graphene.String()
        email = graphene.String()
        company = graphene.Argument(CompanyInput, description="Société courante de l'utilisateur")
        companies = graphene.List(
            CompanyInput,
            description="Liste des sociétés auxquelles à accès l'utilisateur",
        )

    # ici on précise qu'on va retourner à la fin de cette fonction un objet User
    Output = User

    # c'est cette fonction qui sera appelée lors l'appel de la classe UpdateUser
    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['res.users']._prepare_mutation_values(**args)
        user = env['res.users'].search([('id', '=', id)])
        user.write(values)
        return user


class UserMutation(graphene.ObjectType):
    _name = 'UserMutation'
    _type = 'mutation'

    user_update = UserUpdate.Field(description="Documentation of UserUpdate")
