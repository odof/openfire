# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_graphql.graphql.user_type import User


class FCMToken(OdooObjectType):
    _name = "FCMToken"
    _type = "types"

    id = graphene.Int(required=True)
    token = graphene.String()
    user = graphene.Field(User)


class FCMTokenInput(graphene.InputObjectType):
    _name = "FCMTokenInput"
    _type = "types"

    id = graphene.Int()
    token = graphene.String(required=True)
