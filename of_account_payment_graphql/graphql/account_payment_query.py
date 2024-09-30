# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .account_payment_type import AccountPayment, AccountPaymentFilterInput


class AccountPaymentQuery(graphene.ObjectType):
    _name = "AccountPaymentQuery"
    _type = "query"

    account_payments = graphene.List(
        graphene.NonNull(AccountPayment),
        select=graphene.Argument(AccountPaymentFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_payments(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]

        odoo_domain = env["account.payment"]._prepare_graphql_domain(select=select, domain=domain)

        return env["account.payment"].search(odoo_domain, offset=offset, limit=limit)
