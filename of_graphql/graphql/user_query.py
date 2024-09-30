# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .user_type import User, UserFilterInput


class UserQuery(graphene.ObjectType):
    _name = "UserQuery"
    _type = "query"

    users = graphene.List(
        graphene.NonNull(User),
        select=graphene.Argument(UserFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    current_user = graphene.Field(User)

    @staticmethod
    def resolve_users(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]

        odoo_domain = env["res.users"]._prepare_graphql_domain(select=select, domain=domain)

        return env["res.users"].search(odoo_domain, offset=offset, limit=limit)

    @staticmethod
    def resolve_current_user(root, info):
        env = info.context["env"]
        return env["res.users"].search([("id", "=", env.uid)])
