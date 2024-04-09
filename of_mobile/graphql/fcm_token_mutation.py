# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_graphql.graphql.user_type import UserInput

from .fcm_token_type import FCMToken, FCMTokenInput


class FCMTokenCreate(graphene.Mutation):
    _name = 'FCMTokenCreate'

    class Arguments:
        token = FCMTokenInput(required=True)
        user = UserInput(required=True)

    Output = FCMToken

    def mutate(self, info, **args):
        env = info.context['env']

        token_obj = env['of.fcm.device.token']
        values = token_obj._prepare_mutation_values(**args)
        return token_obj.create(values)


class FCMTokenUpdate(graphene.Mutation):
    _name = 'FCMTokenUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        token = FCMTokenInput(required=True)
        user = UserInput(required=True)

    Output = FCMToken

    def mutate(self, info, id, **args):
        env = info.context['env']

        token_obj = env['of.fcm.device.token']
        values = token_obj._prepare_mutation_values(**args)
        token = token_obj.search([('id', '=', id)])
        token.write(values)
        return token


class FCMTokenDelete(graphene.Mutation):
    _name = 'FCMTokenDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = FCMToken

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.fcm.device.token', id)


class FCMTokenMutation(graphene.ObjectType):
    _name = 'FCMTokenMutation'
    _type = 'mutation'

    fcm_token_create = FCMTokenCreate.Field()
    fcm_token_update = FCMTokenUpdate.Field()
    fcm_token_delete = FCMTokenDelete.Field()
