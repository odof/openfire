# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.user_type import User


class UserSubscribeNotification(graphene.Mutation):
    _name = 'UserSubscribeNotification'

    class Arguments:
        token = graphene.String(required=True)

    Output = User

    def mutate(self, info, token, **args):
        env = info.context['env']

        if not env.user.of_fcm_token_ids.filtered(lambda u: u.token == token):
            env['of.fcm.device.token'].create({'token': token, 'user_id': env.user.id})

        return env.user


class UserSubscribeNotificationMutation(graphene.ObjectType):
    _name = 'UserSubscribeNotificationMutation'
    _type = 'mutation'

    user_subscribe_notification = UserSubscribeNotification.Field()
