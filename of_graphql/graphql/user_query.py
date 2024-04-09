import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .user_type import User, UserFilterInput


class UserQuery(graphene.ObjectType):
    _name = 'UserQuery'
    _type = 'query'

    users = graphene.List(
        graphene.NonNull(User),
        filter=graphene.Argument(UserFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    current_user = graphene.Field(User)

    @staticmethod
    def resolve_users(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {'id': 'int', 'company_id': 'int'}
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.email:
                odoo_domain += [('email', 'ilike', filter.email)]
            if filter.mobile:
                odoo_domain += [('mobile', 'ilike', filter.mobile)]
            if filter.phone:
                odoo_domain += [('phone', 'ilike', filter.phone)]

        return env['res.users'].search(odoo_domain, offset=offset, limit=limit)

    @staticmethod
    def resolve_current_user(root, info):
        env = info.context["env"]
        return env["res.users"].search([("id", "=", env.uid)])
